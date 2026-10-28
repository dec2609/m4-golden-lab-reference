#!/usr/bin/env python3

import argparse
import re
import sys
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POLICY_FILE = ROOT / "cau-hinh/m4/dependency-policy.yml"


def load_policy(path):
    text = path.read_text(encoding="utf-8")

    manifest_match = re.search(
        r"^\s*path:\s*(.+?)\s*$", text, re.MULTILINE
    )
    if not manifest_match:
        raise ValueError("Policy thiếu manifest.path")

    manifest_path = manifest_match.group(1).strip()
    manifest = ROOT / manifest_path

    allowlist = {}
    for match in re.finditer(
        r"- name:\s*([^\s]+)\s*\n\s*version:\s*[\"']?([^\"'\s]+)[\"']?",
        text,
    ):
        name = match.group(1).strip().lower()
        version = match.group(2).strip()
        allowlist[name] = version

    return manifest, allowlist


def parse_requirements(path):
    dependencies = []
    seen_names = set()

    for line_number, raw_line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        match = re.fullmatch(r"([A-Za-z0-9_.-]+)==([^\s#]+)", line)
        if not match:
            raise ValueError(
                f"{path}:{line_number}: dependency phải dùng exact version với '=='"
            )

        name = match.group(1).lower()
        version = match.group(2)

        if name in seen_names:
            raise ValueError(
                f"{path}:{line_number}: dependency bị trùng tên: {name}"
            )

        seen_names.add(name)
        dependencies.append((name, version, line_number))

    if not dependencies:
        raise ValueError(f"{path}: manifest không có dependency hợp lệ")

    return dependencies

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", help="Override manifest path for isolated testing")
    parser.add_argument('--candidate')
    parser.add_argument('--run-dir')
    args = parser.parse_args()
    context = None
    if args.candidate:
        from m4_result_adapter import load_context
        if args.manifest or not args.run_dir:
            parser.error('M4 handoff requires --run-dir and the active manifest')
        context = load_context(args.candidate)

    try:
        manifest, allowlist = load_policy(ROOT / "cau-hinh/m4/dependency-policy.yml" if context is not None else POLICY_FILE)
        if args.manifest:
            manifest = ROOT / args.manifest
        dependencies = parse_requirements(manifest)
    except Exception as exc:
        print(f"DEPENDENCY_STATUS=FAIL")
        print(f"ERROR: {exc}")
        return 1

    failures = []

    for name, version, line_number in dependencies:
        approved_version = allowlist.get(name)

        if approved_version is None:
            failures.append(
                f"unapproved dependency: {name}=={version} "
                f"(line {line_number})"
            )
        elif approved_version != version:
            failures.append(
                f"version not approved: {name}=={version}; "
                f"allowed version is {approved_version} "
                f"(line {line_number})"
            )

    print(f"Manifest: {manifest.relative_to(ROOT)}")
    print(f"Dependencies checked: {len(dependencies)}")

    if context is not None:
        from m4_result_adapter import emit_control
        report = Path(args.run_dir) / 'dependency-report.json'
        if report.exists():
            raise ValueError('dependency report already exists')
        report.parent.mkdir(parents=True, exist_ok=True)
        policy = ROOT / 'cau-hinh/m4/dependency-policy.yml'
        data = {'schema_version':'1.0','status':'FAIL' if failures else 'PASS','reason':'DEPENDENCY_POLICY_VIOLATION' if failures else 'ALL_DIRECT_DEPENDENCIES_APPROVED','manifest':manifest.relative_to(ROOT).as_posix(),'scope':'direct','manifest_sha256':__import__('hashlib').sha256(manifest.read_bytes()).hexdigest(),'policy_sha256':__import__('hashlib').sha256(policy.read_bytes()).hexdigest(),'packages':[{'name':n,'version':v,'approved':allowlist.get(n)==v} for n,v,_ in dependencies],'violations':failures}
        report.write_bytes((json.dumps(data)+'\n').encode())
        emit_control(context, args.run_dir, 'DEPENDENCY', report, 1 if failures else 0, 'FAIL' if failures else 'PASS', {'name': 'dependency-policy', 'version': '1.0'}, [sys.executable, *sys.argv], '; '.join(failures) or 'Active source manifest satisfies allowlist')

    if failures:
        print("DEPENDENCY_STATUS=FAIL")
        for failure in failures:
            print(f"ERROR: {failure}")
        return 1

    print("DEPENDENCY_STATUS=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
