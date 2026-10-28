
#!/usr/bin/env python3
"""Validate installed Trivy version and vulnerability database freshness."""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_timestamp(value: Any) -> datetime:
    """Parse an ISO-8601 timestamp and require a timezone."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("DATABASE_TIMESTAMP_MISSING")

    try:
        timestamp = datetime.fromisoformat(
            value.strip().replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ValueError("DATABASE_TIMESTAMP_INVALID") from exc

    if timestamp.tzinfo is None:
        raise ValueError("DATABASE_TIMEZONE_MISSING")

    return timestamp.astimezone(timezone.utc)


def evaluate_reproducibility(
    trivy_version: str,
    metadata: dict,
    max_age_hours: int = 24,
    now: datetime | None = None,
) -> dict:
    """Return PASS only when version and database metadata are valid and fresh."""
    if not isinstance(trivy_version, str) or not trivy_version.strip():
        return {"status": "ERROR", "reason": "TRIVY_VERSION_MISSING"}

    if not isinstance(metadata, dict):
        return {"status": "ERROR", "reason": "DATABASE_METADATA_INVALID"}

    if isinstance(max_age_hours, bool) or not isinstance(max_age_hours, int):
        return {"status": "ERROR", "reason": "MAX_AGE_INVALID"}

    if max_age_hours <= 0:
        return {"status": "ERROR", "reason": "MAX_AGE_INVALID"}

    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        return {"status": "ERROR", "reason": "CURRENT_TIMEZONE_MISSING"}
    else:
        now = now.astimezone(timezone.utc)

    try:
        updated_at = parse_timestamp(metadata.get("UpdatedAt"))
    except ValueError as exc:
        return {"status": "ERROR", "reason": str(exc)}

    age_seconds = (now - updated_at).total_seconds()

    if age_seconds < 0:
        return {"status": "ERROR", "reason": "DATABASE_TIMESTAMP_IN_FUTURE"}

    age_hours = age_seconds / 3600

    if age_hours > max_age_hours:
        return {
            "status": "ERROR",
            "reason": "DATABASE_STALE",
            "database_age_hours": round(age_hours, 2),
            "max_age_hours": max_age_hours,
            "trivy_version": trivy_version.strip(),
        }

    return {
        "status": "PASS",
        "reason": "VERSION_AND_DATABASE_FRESHNESS_VALID",
        "trivy_version": trivy_version.strip(),
        "database_updated_at": updated_at.isoformat(),
        "database_age_hours": round(age_hours, 2),
        "max_age_hours": max_age_hours,
    }


def get_installed_trivy_version() -> str:
    """Read the version from the installed Trivy executable."""
    try:
        completed = subprocess.run(
            ["trivy", "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=15,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise RuntimeError("TRIVY_EXECUTION_FAILED") from exc

    output = completed.stdout + "\n" + completed.stderr
    match = re.search(r"(?m)^\s*Version:\s*(\S+)\s*$", output)

    if not match:
        raise RuntimeError("TRIVY_VERSION_UNREADABLE")

    return match.group(1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check installed Trivy version and database freshness."
    )
    parser.add_argument(
        "--version",
        help="Optional expected version; compared with the installed binary",
    )
    parser.add_argument(
        "--metadata",
        required=True,
        help="Trivy database metadata JSON",
    )
    parser.add_argument(
        "--max-age-hours",
        type=int,
        default=24,
        help="Maximum permitted database age in hours (default: 24)",
    )
    parser.add_argument("--output", help="Optional output JSON path")
    args = parser.parse_args()

    try:
        installed_version = get_installed_trivy_version()

        if args.version and args.version.strip() != installed_version:
            result = {
                "status": "ERROR",
                "reason": "TRIVY_VERSION_MISMATCH",
                "expected_version": args.version.strip(),
                "installed_version": installed_version,
            }
        else:
            metadata = json.loads(
                Path(args.metadata).read_text(encoding="utf-8")
            )
            result = evaluate_reproducibility(
                installed_version,
                metadata,
                max_age_hours=args.max_age_hours,
            )
    except RuntimeError as exc:
        result = {
            "status": "ERROR",
            "reason": str(exc),
        }
    except OSError as exc:
        result = {
            "status": "ERROR",
            "reason": "DATABASE_METADATA_UNREADABLE",
            "detail": str(exc),
        }
    except json.JSONDecodeError as exc:
        result = {
            "status": "ERROR",
            "reason": "DATABASE_METADATA_INVALID_JSON",
            "detail": str(exc),
        }

    if args.output:
        output_path = Path(args.output)
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(result, indent=2) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            print(f"OUTPUT_ERROR={exc}", file=sys.stderr)
            return 2

    print(f"REPRODUCIBILITY_STATUS={result['status']}")
    print(f"REASON={result['reason']}")
    print(f"RESULT={json.dumps(result, sort_keys=True)}")

    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
