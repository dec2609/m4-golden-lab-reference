"""D2 frontend-owned production test topology; never removes resources."""
import argparse
import base64
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import secrets
import shlex
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[3]
FRONT = ROOT / "ma-nguon/orderflow"
COMPOSE = FRONT / "e2e/compose.production.yaml"
RUN = None
PROJECT = None
ENV = os.environ.copy()
PASSWORDS = []


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def save(name, value):
    (RUN / name).write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def scrub(text):
    for value in PASSWORDS:
        text = text.replace(value, "[REDACTED]") if value else text
    return text


def run(args, timeout=120, checked=True):
    started = utc()
    effective_args = docker_shell(args)
    try:
        result = subprocess.run(effective_args, cwd=ROOT, env=ENV, capture_output=True,
                                text=True, encoding="utf-8", errors="replace", timeout=timeout)
        record = {"command": args, "shell_command": effective_args, "started": started, "ended": utc(), "exit_code": result.returncode,
                  "stdout": scrub(result.stdout), "stderr": scrub(result.stderr)}
    except subprocess.TimeoutExpired as exc:
        record = {"command": args, "started": started, "ended": utc(), "exit_code": None, "status": "ERROR", "reason": "command timeout"}
        with (RUN / "commands.jsonl").open("a", encoding="utf-8") as log:
            log.write(json.dumps(record) + "\n")
        raise RuntimeError("Command timeout: " + args[0]) from exc
    with (RUN / "commands.jsonl").open("a", encoding="utf-8") as log:
        log.write(json.dumps(record) + "\n")
    if checked and result.returncode:
        raise RuntimeError(args[0] + " exited " + str(result.returncode) + "; see commands.jsonl")
    return result


def compose(*args):
    return ["docker", "compose", "-p", PROJECT, "-f", str(COMPOSE), *args]


def docker_shell(args):
    """On Windows run Docker through Git Bash, disabling MSYS container-path rewriting."""
    if os.name != "nt" or args[0] != "docker":
        return args
    git = pathlib.Path(shutil.which("git") or "")
    bash = pathlib.Path(os.environ.get("ORDERFLOW_GIT_BASH", str(git.parent.parent / "bin/bash.exe")))
    if not bash.is_file():
        raise RuntimeError("Git Bash required for Windows Docker commands; set ORDERFLOW_GIT_BASH")
    ENV["MSYS_NO_PATHCONV"] = "1"
    return [str(bash), "-c", shlex.join(args)]


def configuration():
    # Read existing development settings in memory; never dump passwords into logs.
    raw = subprocess.run(docker_shell(["docker", "compose", "-f", str(ROOT / "docker-compose.yml"), "config", "--format", "json"]),
                         cwd=ROOT, env=ENV, capture_output=True, text=True, encoding="utf-8")
    if raw.returncode:
        raise RuntimeError("Unable to read main Compose settings (raw output withheld)")
    db = json.loads(raw.stdout)["services"]["order-db"]["environment"]
    for key in ("NAME", "USER", "PASSWORD"):
        value = str(db["POSTGRES_DB" if key == "NAME" else "POSTGRES_" + key])
        ENV["D2_DB_" + key] = value
        if key == "PASSWORD":
            PASSWORDS.append(value)


def inventory():
    containers = []
    for line in run(["docker", "ps", "-a", "--format", "{{json .}}"]).stdout.splitlines():
        c = json.loads(line)
        containers.append({k: c.get(k) for k in ("ID", "Names", "State", "Status", "Labels")})
    return {"containers": containers,
            "volumes": run(["docker", "volume", "ls", "-q"]).stdout.splitlines(),
            "networks": run(["docker", "network", "ls", "--format", "{{.Name}}"]).stdout.splitlines()}


def collision(current):
    found = [c["Names"] for c in current["containers"] if c["Names"].startswith(PROJECT)]
    found += [n for n in current["volumes"] + current["networks"] if n.startswith(PROJECT)]
    if found:
        raise RuntimeError("Existing test resource detected; refusing reuse: " + ", ".join(found))


def preflight():
    if (RUN / "preflight.json").exists():
        raise RuntimeError("Preflight already recorded; use a new run")
    current = inventory()
    collision(current)
    # Resolve privately, then store a summary with environment keys only.
    resolved = subprocess.run(docker_shell(compose("config", "--format", "json")), cwd=ROOT, env=ENV,
                              capture_output=True, text=True, encoding="utf-8")
    if resolved.returncode:
        raise RuntimeError("Test Compose config invalid (raw output withheld)")
    cfg = json.loads(resolved.stdout)
    if set(cfg["services"]) != {"order-db", "order-app", "order-frontend"}:
        raise RuntimeError("Unexpected services")
    if cfg["volumes"]["order-db-data"].get("external") or cfg["volumes"]["order-db-data"]["name"] != PROJECT + "_order-db-data":
        raise RuntimeError("Volume is not exclusively owned by this new run")
    if cfg["networks"]["default"].get("external") or cfg["networks"]["default"]["name"] != PROJECT + "_default":
        raise RuntimeError("Network is not exclusively owned by this new run")
    for name in ("order-app", "order-db"):
        if cfg["services"][name].get("ports"):
            raise RuntimeError("Backend and DB must not publish host ports")
    free = shutil.disk_usage(ROOT.drive + "\\").free
    if free < 3 * 1024**3:
        raise RuntimeError("Insufficient free disk (<3 GiB)")
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 5180))
    safe = {"project": PROJECT, "services": {}}
    for name, svc in cfg["services"].items():
        safe["services"][name] = {k: svc.get(k) for k in
                                ("image", "build", "ports", "volumes", "read_only", "tmpfs", "cap_drop", "security_opt")}
        safe["services"][name]["environment_keys"] = sorted(svc.get("environment", {}))
    save("compose.sanitized.json", safe)
    save("preflight.json", {"status": "PASS", "observed_at": utc(), "before": current, "free_host_bytes": free,
                            "available_port": 5180, "docker": run(["docker", "version", "--format", "{{.Server.Version}}"]).stdout.strip(),
                            "resources": run(["docker", "info", "--format", "{{.NCPU}} CPUs; {{.MemTotal}} bytes RAM"]).stdout.strip()})
    print("D2 preflight PASS; unique project/volume/network and port 5180 available.")


def build():
    if not (RUN / "preflight.json").exists():
        raise RuntimeError("Require new successful preflight")
    if (RUN / "build.json").exists():
        previous = json.loads((RUN / "build.json").read_text())
        if previous["status"] == "PASS":
            raise RuntimeError("Build already passed; use a new run for a different image")
        if not list(RUN.glob("build-attempt-*.json")):
            save("build-attempt-1.json", previous)
    attempt = len(list(RUN.glob("build-attempt-*.json"))) + 1
    collision(inventory())
    result = run(compose("--progress", "plain", "build", "order-frontend", "order-app"), timeout=600, checked=False)
    logfile = "docker-build-attempt-" + str(attempt) + ".log"
    (RUN / logfile).write_text(scrub(result.stdout + "\n" + result.stderr), encoding="utf-8")
    record = {"status": "PASS" if result.returncode == 0 else "FAIL", "exit_code": result.returncode, "observed_at": utc(), "attempt": attempt, "log": logfile}
    save("build-attempt-" + str(attempt) + ".json", record)
    save("build.json", record)
    if result.returncode:
        raise RuntimeError("Build failed")
    bases = {}
    for ref in ("node:24-alpine@sha256:44fce696f38ba8c987c4db89954051000bbd05ffd8d8659ba15ed4a8602e937f",
                "nginx:1.30.6-alpine@sha256:970364228b1e4f932abc22d321932816782cca8a20b85a77552a7cfe9acfb3b5"):
        bases[ref] = json.loads(run(["docker", "buildx", "imagetools", "inspect", ref, "--format", "{{json .Manifest}}"]).stdout)
    save("base-image-descriptors.json", bases)
    print("D2 production build PASS; npm ci and production assets built inside multi-stage image.")


def up():
    if json.loads((RUN / "build.json").read_text())["status"] != "PASS":
        raise RuntimeError("Build did not pass")
    collision(inventory())
    run(compose("up", "-d", "--no-build", "--wait", "--wait-timeout", "120"), timeout=180)
    verify_runtime()


def verify_runtime():
    ids = run(compose("ps", "-q")).stdout.splitlines()
    details = []
    for cid in ids:
        c = json.loads(run(["docker", "inspect", "--format",
                           '{"id":"{{.Id}}","name":"{{.Name}}","image_id":"{{.Image}}","user":"{{.Config.User}}","read_only":{{.HostConfig.ReadonlyRootfs}},"health":"{{.State.Health.Status}}"}', cid]).stdout)
        details.append(c)
    for args in (("id",), ("nginx", "-t"), ("nginx", "-v")):
        run(compose("exec", "-T", "order-frontend", *args))
    audit = run(compose("exec", "-T", "order-frontend", "sh", "-c",
                       'test "$(id -u)" = 101 && ! command -v node && test ! -e /usr/share/nginx/html/.env && test ! -e /app && cat /proc/1/cmdline && sha256sum /usr/share/nginx/html/index.html')).stdout
    save("runtime.json", {"status": "PASS", "observed_at": utc(), "containers": details,
                          "frontend_runtime_checks": audit, "note": "Docker image IDs are opaque engine identities; determine OCI descriptor kind separately, never infer registry verification"})
    (RUN / "nginx-effective.conf").write_text(run(compose("exec", "-T", "order-frontend", "nginx", "-T")).stdout, encoding="utf-8")
    print("D2 topology healthy; Nginx UID 101, read-only rootfs; runtime has no Node/Vite.")


def repair_frontend():
    if (RUN / "runtime.json").exists():
        raise RuntimeError("Runtime already verified; use a new run for later changes")
    current = inventory()
    own = [c for c in current["containers"] if c["Names"].startswith(PROJECT)]
    if len(own) != 3 or any(("com.docker.compose.project=" + PROJECT + ",") not in (c["Labels"] + ",") for c in own):
        raise RuntimeError("Repair restricted to the three containers created by this run")
    (RUN / "startup-failed.log").write_text(run(compose("logs", "--no-color", "order-frontend")).stdout, encoding="utf-8")
    result = run(compose("--progress", "plain", "build", "order-frontend"), timeout=600, checked=False)
    (RUN / "docker-build-frontend-repair.log").write_text(scrub(result.stdout + "\n" + result.stderr), encoding="utf-8")
    save("frontend-repair.json", {"status": "PASS" if result.returncode == 0 else "FAIL", "exit_code": result.returncode,
                                  "reason": "Move every Nginx temp directory to writable /tmp for read-only non-root runtime", "observed_at": utc()})
    if result.returncode:
        raise RuntimeError("Frontend repair build failed")
    run(compose("up", "-d", "--no-deps", "--no-build", "--wait", "order-frontend"), timeout=120)
    verify_runtime()


def http(method, path, payload=None, timeout=25):
    body = None if payload is None else json.dumps(payload).encode()
    req = urllib.request.Request("http://127.0.0.1:5180" + path, method=method, data=body,
                                 headers={"Accept": "application/json", "Content-Type": "application/json"})
    try:
        response = urllib.request.urlopen(req, timeout=timeout)
    except urllib.error.HTTPError as exc:
        response = exc
    with response:
        raw = response.read()
        content_type = response.headers.get("Content-Type", "")
        return {"method": method, "path": path, "http_status": response.status, "content_type": content_type,
                "body": json.loads(raw) if "application/json" in content_type else raw.decode(errors="replace"),
                "sha256": hashlib.sha256(raw).hexdigest()}


def rows():
    sql = "SELECT COALESCE(json_agg(t),'[]'::json)::text FROM (SELECT id,customer_name,product_name,quantity,status,created_at FROM orders ORDER BY id) t"
    raw = run(compose("exec", "-T", "order-db", "psql", "-X", "-U", ENV["D2_DB_USER"],
                      "-d", ENV["D2_DB_NAME"], "-A", "-t", "-c", sql)).stdout
    return json.loads(raw.strip())


def proxy():
    if (RUN / "proxy-results.json").exists():
        previous = json.loads((RUN / "proxy-results.json").read_text())
        if previous.get("status") == "PASS":
            raise RuntimeError("Proxy results already passed; use a new run")
        attempt = len(list(RUN.glob("proxy-attempt-*.json"))) + 1
        save("proxy-attempt-" + str(attempt) + ".json", previous)
    tests = []
    report = {"started": utc(), "tests": tests}
    def check(name, observed, valid, layer="REAL"):
        tests.append({"name": name, "status": "PASS" if valid else "FAIL", "layer": layer, "observed": observed})
        save("proxy-results.json", report)
        if not valid:
            raise AssertionError(name)
    try:
        initial = rows()
        check("fresh DB empty", initial, initial == [])
        index = http("GET", "/")
        check("static index served", {"status": index["http_status"], "content_type": index["content_type"], "sha256": index["sha256"]},
              index["http_status"] == 200 and "text/html" in index["content_type"] and "/@vite/client" not in index["body"])
        disk_hash = run(compose("exec", "-T", "order-frontend", "sha256sum", "/usr/share/nginx/html/index.html")).stdout.split()[0]
        check("HTTP index matches image bytes", {"image_sha256": disk_hash, "http_sha256": index["sha256"]}, disk_hash == index["sha256"])
        for route in ("/orders", "/orders/new", "/orders/123", "/release"):
            res = http("GET", route)
            check("SPA direct " + route, {"status": res["http_status"], "sha256": res["sha256"]},
                  res["http_status"] == 200 and res["sha256"] == index["sha256"])
        assets = re.findall(r'(?:src|href)="(/assets/[^"]+)"', index["body"])
        check("hashed assets referenced", assets, any(p.endswith(".js") for p in assets) and any(p.endswith(".css") for p in assets))
        for asset in assets:
            res = http("GET", asset)
            expected_type = {".js": "javascript", ".css": "text/css", ".png": "image/png", ".svg": "image/svg+xml", ".ico": "image/x-icon"}.get(pathlib.Path(asset).suffix)
            valid_type = expected_type is not None and expected_type in res["content_type"]
            check("static asset " + asset, {"status": res["http_status"], "content_type": res["content_type"], "sha256": res["sha256"]}, res["http_status"] == 200 and valid_type)
        missing = http("GET", "/assets/not-a-real-file.js")
        check("missing asset is 404, not SPA", {"status": missing["http_status"]}, missing["http_status"] == 404)
        for path in ("/api/health", "/api/orders"):
            res = http("GET", path)
            check("proxy " + path, res, res["http_status"] == 200 and isinstance(res["body"], dict))
        ready = http("GET", "/api/ready")
        check("M4 database readiness through Nginx", ready,
              ready["http_status"] == 200 and ready["body"] == {"status": "ready", "database": "connected"})
        payload = {"customer_name": RUN.name + "-api", "product_name": "D2 production proxy item", "quantity": 3}
        created = http("POST", "/api/orders", payload)
        check("POST body/method/201 preserved", created, created["http_status"] == 201 and all(created["body"].get(k) == v for k, v in payload.items()))
        order = created["body"]
        fetched = http("GET", "/api/orders")
        check("GET returns persisted ID", fetched, order in fetched["body"]["orders"])
        before = rows()
        invalid = http("POST", "/api/orders", {**payload, "quantity": True})
        check("Flask 400 JSON unchanged; no write", invalid, invalid["http_status"] == 400 and isinstance(invalid["body"], dict) and rows() == before)
        overflow = http("POST", "/api/orders", {**payload, "quantity": 2147483648})
        check("M4 int32 overflow rejected without write", overflow,
              overflow["http_status"] == 400 and isinstance(overflow["body"], dict) and rows() == before)
        missing_api = http("GET", "/api/d2-missing")
        check("Flask 404 not HTML 200 fallback", {"status": missing_api["http_status"], "content_type": missing_api["content_type"]},
              missing_api["http_status"] == 404)
        # Real dependency failure, only the fresh D2 database. Always restore it.
        try:
            run(compose("stop", "--timeout", "15", "order-db"), timeout=45)
            unready = http("GET", "/api/ready")
            check("M4 database outage is readiness503, not healthy", unready,
                  unready["http_status"] == 503 and unready["body"] == {"status": "unready", "error": "database unreachable"})
            failure = http("GET", "/api/orders")
            check("real Flask 500 JSON preserved while D2 DB stopped", failure,
                  failure["http_status"] == 500 and failure["body"] == {"error": "Internal server error"})
        finally:
            run(compose("start", "order-db"))
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                try:
                    if http("GET", "/api/orders")["http_status"] == 200:
                        break
                except Exception:
                    pass
                time.sleep(0.5)
            else:
                raise RuntimeError("D2 database did not recover")
        check("DB recovery retains row", rows(), rows() == before)
        ready = http("GET", "/api/ready")
        check("M4 readiness recovers after database restart", ready,
              ready["http_status"] == 200 and ready["body"] == {"status": "ready", "database": "connected"})
        try:
            run(compose("pause", "order-app"))
            started = time.monotonic()
            timeout = http("GET", "/api/health")
            elapsed = time.monotonic() - started
            check("real Nginx upstream timeout is 504, not SPA 200",
                  {"status": timeout["http_status"], "elapsed_seconds": elapsed},
                  timeout["http_status"] == 504 and elapsed >= 14)
        finally:
            run(compose("unpause", "order-app"))
        check("backend recovers after timeout", http("GET", "/api/health"),
              http("GET", "/api/health")["http_status"] == 200)
        report["status"] = "PASS"
    except Exception as exc:
        report.update(status="FAIL" if isinstance(exc, AssertionError) else "ERROR", error=scrub(str(exc)))
        raise
    finally:
        report["ended"] = utc()
        save("proxy-results.json", report)
    print("Production proxy PASS:", len(tests), "real checks.")


def app(action):
    if action not in ("stop", "start"):
        raise RuntimeError("Only test backend stop/start is permitted")
    run(compose(action, "order-app"))
    if action == "start":
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline:
            try:
                if http("GET", "/api/health")["http_status"] == 200:
                    break
            except Exception:
                pass
            time.sleep(0.5)
        else:
            raise RuntimeError("Backend recovery deadline exceeded")
    save("backend-" + action + ".json", {"status": "PASS", "observed_at": utc(), "action": action, "project": PROJECT})
    print("Owned backend", action, "completed.")


def db_verify():
    observed = rows()
    expected = {RUN.name + "-api", RUN.name + "-browser"}
    valid = len(observed) == 2 and {r["customer_name"] for r in observed} == expected
    browser = json.loads((RUN / "browser-results.json").read_text(encoding="utf-8"))
    comparisons = []
    def walk(suite):
        for spec in suite.get("specs", []):
            for test in spec["tests"]:
                for result in test["results"]:
                    for item in result.get("attachments", []):
                        if item["name"] == "production-persisted-order":
                            order = json.loads(base64.b64decode(item["body"]))
                            actual = next((r for r in observed if r["id"] == order["id"]), None)
                            match = actual is not None and all(actual[k] == order[k] for k in ("id","customer_name","product_name","quantity","status"))
                            match = match and dt.datetime.fromisoformat(actual["created_at"]) == dt.datetime.fromisoformat(order["created_at"])
                            comparisons.append({"id": order["id"], "fields_and_timestamp_match": match})
        for child in suite.get("suites", []):
            walk(child)
    for suite in browser["suites"]:
        walk(suite)
    valid = valid and len(comparisons) == 1 and all(c["fields_and_timestamp_match"] for c in comparisons)
    save("database-verification.json", {"status": "PASS" if valid else "FAIL", "observed_at": utc(),
                                       "rows": observed, "browser_comparison": comparisons})
    (RUN / "containers.final.log").write_text(run(compose("logs", "--no-color", "--tail", "300")).stdout, encoding="utf-8")
    if not valid:
        raise AssertionError("PostgreSQL does not match browser output")
    print("Real PostgreSQL persistence PASS: 2 synthetic rows; browser fields/timestamp match.")


def audit():
    cid = run(compose("ps", "-q", "order-frontend")).stdout.strip()
    host = json.loads(run(["docker", "inspect", "--format",
                          '{"image_id":"{{.Image}}","read_only":{{.HostConfig.ReadonlyRootfs}},"cap_drop":{{json .HostConfig.CapDrop}},"security_opt":{{json .HostConfig.SecurityOpt}}}', cid]).stdout)
    image = json.loads(run(["docker", "image", "inspect", "--format",
                           '{"id":"{{.Id}}","repo_digests":{{json .RepoDigests}},"user":"{{.Config.User}}","entrypoint":{{json .Config.Entrypoint}},"size":{{.Size}}}', host["image_id"]]).stdout)
    status = run(compose("exec", "-T", "order-frontend", "sh", "-c", "id; grep -E '^(CapEff|NoNewPrivs)' /proc/1/status")).stdout
    valid = host["read_only"] and "ALL" in host["cap_drop"] and "no-new-privileges:true" in host["security_opt"] and image["user"] == "101:101" and "0000000000000000" in status and re.search(r"NoNewPrivs:\s+1", status)
    save("frontend-image-audit.json", {"status": "PASS" if valid else "FAIL", "observed_at": utc(), "host_config": host,
                                       "image": image, "process_status": status,
                                       "identity_note": "Image ID and RepoDigests are engine references; inspect BuildKit OCI index/manifest/config records separately. No signature or independent registry verification"})
    if not valid:
        raise AssertionError("Frontend runtime hardening audit failed")
    print("Production frontend runtime audit PASS: UID101, read-only, CapEff0, no-new-privileges.")


def cleanup():
    current = inventory()
    own = [c for c in current["containers"] if c["Names"].startswith(PROJECT)]
    if own:
        run(compose("stop", "--timeout", "20"), timeout=90)
    after = inventory()
    before = json.loads((RUN / "preflight.json").read_text())["before"]
    old = {c["ID"]: c for c in after["containers"]}
    ok = all(c["ID"] in old and old[c["ID"]]["State"] == c["State"] for c in before["containers"])
    stopped = all(c["State"] == "exited" for c in after["containers"] if c["Names"].startswith(PROJECT))
    retained = all(v in after["volumes"] for v in before["volumes"]) and PROJECT + "_order-db-data" in after["volumes"]
    nets = all(n in after["networks"] for n in before["networks"])
    save("cleanup.json", {"status": "PASS" if ok and stopped and retained and nets else "FAIL", "observed_at": utc(),
                          "prior_container_states_unchanged": ok, "test_containers_stopped": stopped,
                          "all_prior_and_test_volumes_retained": retained, "prior_networks_retained": nets, "after": after})
    print("D2 resources stopped; D1/sandbox states and all volumes preserved.")


def main():
    global RUN, PROJECT
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["init","preflight","build","up","repair-frontend","proxy","app-stop","app-start","db-verify","audit","cleanup"])
    parser.add_argument("--run-dir")
    args = parser.parse_args()
    if args.stage == "init":
        if args.run_dir:
            raise RuntimeError("init creates a unique new run; do not supply --run-dir")
        run_id = "d2a-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(2)
        RUN = ROOT / "bang-chung/m4/orderflow/d2" / run_id
        RUN.mkdir(parents=True, exist_ok=False)
        files = {}
        for directory, dirs, names in os.walk(ROOT):
            dirs[:] = [d for d in dirs if d not in {".git","node_modules","dist","__pycache__",".venv"}
                       and pathlib.Path(directory, d).resolve() != RUN.parent.resolve()]
            for name in names:
                if name == ".git":
                    continue
                p = pathlib.Path(directory, name)
                files[p.relative_to(ROOT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
        def git(*a):
            return subprocess.check_output(["git", *a], cwd=ROOT, text=True).strip()
        save("baseline.json", {"run_id": run_id, "project": "orderflow-" + run_id.lower(),
                               "head": git("rev-parse","HEAD"), "dirty": git("status","--porcelain=v1","--untracked-files=all"),
                               "files": files, "observed_at": utc(), "note": "Older D2 evidence excluded from new input inventory; D1/M3 included"})
        print(json.dumps({"run_dir": str(RUN), "project": "orderflow-" + run_id.lower()}))
        return
    if not args.run_dir:
        parser.error("--run-dir is required for execution stages")
    RUN = pathlib.Path(args.run_dir).resolve()
    if RUN.parent != (ROOT / "bang-chung/m4/orderflow/d2").resolve():
        raise RuntimeError("Run path must stay inside frontend D2 evidence directory")
    baseline = json.loads((RUN / "baseline.json").read_text(encoding="utf-8"))
    PROJECT = baseline["project"]
    if not PROJECT.startswith("orderflow-d2a-"):
        raise RuntimeError("Invalid project prefix")
    configuration()
    if args.stage.startswith("app-"):
        app(args.stage.split("-")[1])
    else:
        globals()[args.stage.replace("-", "_")]()


if __name__ == "__main__":
    main()
