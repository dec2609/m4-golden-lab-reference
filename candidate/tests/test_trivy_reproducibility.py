
from datetime import datetime, timedelta, timezone

import pytest

from scripts.trivy_reproducibility import evaluate_reproducibility


NOW = datetime(2026, 10, 19, 12, 0, tzinfo=timezone.utc)


def metadata(updated_at):
    return {
        "Version": 2,
        "UpdatedAt": updated_at,
        "NextUpdate": "2026-10-20T00:00:00Z",
        "DownloadedAt": "2026-10-19T11:00:00Z",
    }


def test_fresh_database_passes():
    updated = (NOW - timedelta(hours=2)).isoformat()
    result = evaluate_reproducibility(
        "0.XX.X", metadata(updated), max_age_hours=24, now=NOW
    )
    assert result["status"] == "PASS"
    assert result["reason"] == "VERSION_AND_DATABASE_FRESHNESS_VALID"


def test_stale_database_is_rejected():
    updated = (NOW - timedelta(hours=25)).isoformat()
    result = evaluate_reproducibility(
        "0.XX.X", metadata(updated), max_age_hours=24, now=NOW
    )
    assert result["status"] == "ERROR"
    assert result["reason"] == "DATABASE_STALE"


def test_missing_version_is_rejected():
    updated = (NOW - timedelta(hours=1)).isoformat()
    result = evaluate_reproducibility(
        "", metadata(updated), now=NOW
    )
    assert result["reason"] == "TRIVY_VERSION_MISSING"


def test_missing_database_timestamp_is_rejected():
    result = evaluate_reproducibility(
        "0.XX.X", {"Version": 2}, now=NOW
    )
    assert result["reason"] == "DATABASE_TIMESTAMP_MISSING"


def test_invalid_database_timestamp_is_rejected():
    result = evaluate_reproducibility(
        "0.XX.X", metadata("not-a-timestamp"), now=NOW
    )
    assert result["reason"] == "DATABASE_TIMESTAMP_INVALID"


def test_timestamp_without_timezone_is_rejected():
    result = evaluate_reproducibility(
        "0.XX.X",
        metadata("2026-10-19T11:00:00"),
        now=NOW,
    )
    assert result["reason"] == "DATABASE_TIMEZONE_MISSING"


def test_future_database_timestamp_is_rejected():
    future = (NOW + timedelta(hours=1)).isoformat()
    result = evaluate_reproducibility(
        "0.XX.X", metadata(future), now=NOW
    )
    assert result["reason"] == "DATABASE_TIMESTAMP_IN_FUTURE"


@pytest.mark.parametrize("max_age", [0, -1])
def test_invalid_max_age_is_rejected(max_age):
    updated = (NOW - timedelta(hours=1)).isoformat()
    result = evaluate_reproducibility(
        "0.XX.X", metadata(updated), max_age_hours=max_age, now=NOW
    )
    assert result["reason"] == "MAX_AGE_INVALID"


def test_non_object_metadata_is_rejected():
    result = evaluate_reproducibility(
        "0.XX.X", [], now=NOW
    )
    assert result["reason"] == "DATABASE_METADATA_INVALID"
