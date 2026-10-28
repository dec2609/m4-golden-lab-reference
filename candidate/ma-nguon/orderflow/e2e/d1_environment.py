"""Controlled D1 environment/API runner. Does not reset DB or remove resources."""
import argparse
import base64
import datetime
import hashlib
import json
import os
import pathlib
import secrets
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "ma-nguon/orderflow"
SECRETS = []
RUN = None
PROJECT = None


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def scrub(text):
    for value in SECRETS:
        if value:
            text = text.replace(value, "[REDACTED]")
    return text


def save(name, data):
    (RUN / name).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def command(args, *, timeout=120, log=True):
    started = utc()
    try:
        result = subprocess.run(args, cwd=ROOT, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        with (RUN / "commands.jsonl").open("a", encoding="utf-8") as out:
            out.write(json.dumps({"started": started, "command": args, "exit_code": None,
                                  "status": "ERROR", "reason": "command timeout"}) + "\n")
        raise
    if log:
        with (RUN / "commands.jsonl").open("a", encoding="utf-8") as out:
            out.write(json.dumps({"started": started, "ended": utc(), "command": args,
                                  "exit_code": result.returncode,
                                  "stdout": scrub(result.stdout), "stderr": scrub(result.stderr)}) + "\n")
    return result


def checked(args, **kwargs):
    result = command(args, **kwargs)
    if result.returncode:
        raise RuntimeError("Command failed: " + args[0] + " (exit " + str(result.returncode) + ")")
    return result.stdout


def compose(*args):
    return ["docker", "compose", "-p", PROJECT, "-f", str(ROOT / "docker-compose.yml"), *args]


def config():
    # Never print or persist raw resolved environment.
    result = command(compose("config", "--format", "json"), log=False)
    if result.returncode:
        raise RuntimeError("Compose config failed (raw environment output withheld)")
    data = json.loads(result.stdout)
    for svc in data["services"].values():
        for key, value in svc.get("environment", {}).items():
            if any(term in key.upper() for term in ("PASSWORD", "SECRET", "TOKEN")):
                SECRETS.append(str(value))
    with (RUN / "commands.jsonl").open("a", encoding="utf-8") as out:
        out.write(json.dumps({"ended": utc(), "command": compose("config", "--format", "json"),
                              "exit_code": result.returncode,
                              "stdout": "Resolved configuration captured only as sanitized summary"}) + "\n")
    return data


def inventory():
    containers = []
    for line in checked(["docker", "container", "ls", "-a", "--format", "{{json .}}"]).splitlines():
        item = json.loads(line)
        containers.append({k: item.get(k) for k in ("ID", "Names", "State", "Status", "Labels")})
    volumes = checked(["docker", "volume", "ls", "-q"]).splitlines()
    networks = checked(["docker", "network", "ls", "--format", "{{.Name}}"]).splitlines()
    return {"containers": containers, "volumes": volumes, "networks": networks}


def no_collision(current):
    matches = [c["Names"] for c in current["containers"]
               if ("com.docker.compose.project=" + PROJECT + ",") in (c["Labels"] + ",")
               or c["Names"].startswith(PROJECT)]
    matches += [n for n in current["volumes"] + current["networks"] if n.startswith(PROJECT)]
    if matches:
        raise RuntimeError("Existing project resource detected; refusing reuse: " + ", ".join(matches))


def preflight():
    if (RUN / "preflight.json").exists():
        raise RuntimeError("Preflight already recorded; use a new run instead of overwriting evidence")
    cfg = config()
    if set(cfg["services"]) != {"order-app", "order-db"}:
        raise RuntimeError("Unexpected service set")
    vol = cfg["volumes"]["order-db-data"]
    net = cfg["networks"]["order-network"]
    if vol.get("external") or net.get("external"):
        raise RuntimeError("External shared volume/network is forbidden")
    if vol["name"] != PROJECT + "_order-db-data" or net["name"] != PROJECT + "_order-network":
        raise RuntimeError("Resolved resource names do not belong to new project")
    current = inventory()
    no_collision(current)
    free = shutil.disk_usage(ROOT.drive + "\\").free
    if free < 3 * 1024**3:
        raise RuntimeError("Less than 3 GiB free on host")
    for port in (8081, 5173):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", port))
    safe_services = {}
    for name, svc in cfg["services"].items():
        safe_services[name] = {k: svc.get(k) for k in
                              ("image", "build", "ports", "expose", "volumes", "networks")}
        safe_services[name]["environment_keys"] = sorted(svc.get("environment", {}))
    save("compose.sanitized.json", {"project": PROJECT, "services": safe_services,
                                    "volumes": cfg["volumes"], "networks": cfg["networks"]})
    version = checked(["docker", "version", "--format", "{{.Server.Version}}"]).strip()
    save("preflight.json", {"status": "PASS", "observed_at": utc(), "free_host_bytes": free,
                            "ports_available": [8081, 5173], "docker_server": version,
                            "compose_version": checked(["docker", "compose", "version"]).strip(),
                            "before": current})
    print("Preflight PASS; project and named volume/network do not exist.")


def up():
    config()
    if not (RUN / "preflight.json").exists():
        raise RuntimeError("Preflight evidence required")
    no_collision(inventory())
    checked(compose("up", "-d", "--build", "--wait", "--wait-timeout", "120",
                    "order-db", "order-app"), timeout=300)
    checked(compose("ps", "--format", "json"))
    logs = checked(compose("logs", "--no-color", "--tail", "100"))
    (RUN / "containers.startup.log").write_text(scrub(logs), encoding="utf-8")
    save("started.json", {"status": "PASS", "observed_at": utc(), "project": PROJECT,
                          "volume": PROJECT + "_order-db-data"})
    print("Two-service test project started.")


def http(method, url, payload=None, raw=None):
    data = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Accept": "application/json", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            status, body = res.status, res.read().decode()
    except urllib.error.HTTPError as err:
        status, body = err.code, err.read().decode()
    parsed = json.loads(body)
    return {"method": method, "url": url, "http_status": status, "body": parsed}


def db_snapshot(cfg):
    env = cfg["services"]["order-db"]["environment"]
    sql = "SELECT COALESCE(json_agg(t),'[]'::json)::text FROM (SELECT id,customer_name,product_name,quantity,status,created_at FROM orders ORDER BY id) t"
    rows = checked(compose("exec", "-T", "order-db", "psql", "-X", "-U",
                           env["POSTGRES_USER"], "-d", env["POSTGRES_DB"],
                           "-A", "-t", "-c", sql))
    return json.loads(rows.strip())


def vite():
    env = os.environ.copy()
    for key in list(env):
        if key.startswith("VITE_"):
            del env[key]
    args = ["node", str(FRONTEND / "node_modules/vite/bin/vite.js"),
            "--host", "127.0.0.1", "--port", "5173", "--strictPort"]
    if list(FRONTEND.glob(".env*")):
        raise RuntimeError("Review Vite env files before running controlled proxy E2E")
    with (RUN / "vite.log").open("w", encoding="utf-8") as log:
        process = subprocess.Popen(args, cwd=FRONTEND, env=env, stdout=log,
                                   stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        record = {"started": utc(), "command": args, "pid": process.pid,
                  "status": "RUNNING", "VITE_overrides_removed": True,
                  "base_url": "http://127.0.0.1:5173", "proxy_target": "http://127.0.0.1:8081"}
        save("vite.json", record)
        print("Vite launched for this run; PID", process.pid, flush=True)
        try:
            process.wait()
        except KeyboardInterrupt:
            pass
        finally:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=15)
            record.update(status="STOPPED", ended=utc(), exit_code=process.returncode)
            save("vite.json", record)
            print("Owned Vite process stopped.", flush=True)


def api():
    if (RUN / "api-results.json").exists():
        raise RuntimeError("API results already recorded; use a new isolated run")
    cfg = config()
    tests = []
    report = {"stage": "D1-A", "started": utc(), "project": PROJECT, "tests": tests}
    def case(name, observed, valid):
        tests.append({"name": name, "status": "PASS" if valid else "FAIL", "observed": observed})
        save("api-results.json", report)
        if not valid:
            raise AssertionError(name)
    try:
        initial = db_snapshot(cfg)
        case("new isolated database is empty", {"row_count": len(initial)}, initial == [])
        for url in ("http://127.0.0.1:8081/health", "http://127.0.0.1:5173/api/health"):
            res = http("GET", url)
            case("health " + url, res, res["http_status"] == 200 and res["body"] == {"status": "ok"})
        for url in ("http://127.0.0.1:8081/orders", "http://127.0.0.1:5173/api/orders"):
            res = http("GET", url)
            case("list " + url, res, res["http_status"] == 200 and res["body"] == {"orders": []})
        marker = RUN.name + "-api"
        payload = {"customer_name": marker, "product_name": "D1 synthetic API item", "quantity": 3}
        res = http("POST", "http://127.0.0.1:5173/api/orders", payload)
        order = res["body"]
        case("POST via Vite to Flask", res, res["http_status"] == 201
             and all(order.get(k) == v for k, v in payload.items())
             and isinstance(order.get("id"), int) and order.get("status") == "pending")
        for url in ("http://127.0.0.1:8081/orders", "http://127.0.0.1:5173/api/orders"):
            res = http("GET", url)
            case("GET created ID " + url, res, res["http_status"] == 200 and order in res["body"]["orders"])
        rows = db_snapshot(cfg)
        expected = {k: order[k] for k in ("id", "customer_name", "product_name", "quantity", "status")}
        case("PostgreSQL exact persisted row", rows,
             len(rows) == 1 and all(rows[0][k] == v for k, v in expected.items()))
        invalid = [
            ("quantity boolean", {**payload, "quantity": True}, None),
            ("quantity zero", {**payload, "quantity": 0}, None),
            ("quantity negative", {**payload, "quantity": -1}, None),
            ("quantity float", {**payload, "quantity": 1.5}, None),
            ("quantity string", {**payload, "quantity": "2"}, None),
            ("empty customer", {**payload, "customer_name": "   "}, None),
            ("empty product", {**payload, "product_name": ""}, None),
            ("required fields missing", {}, None),
            ("JSON array", [], None),
            ("malformed JSON", None, b'{"broken":'),
        ]
        for name, payload, raw in invalid:
            before = db_snapshot(cfg)
            res = http("POST", "http://127.0.0.1:5173/api/orders", payload, raw)
            after = db_snapshot(cfg)
            case("reject " + name, {"response": res, "rows_before": len(before),
                                   "rows_after": len(after)},
                 res["http_status"] == 400 and before == after and "error" in res["body"])
        report["status"] = "PASS"
    except Exception as exc:
        report["status"] = "FAIL" if isinstance(exc, AssertionError) else "ERROR"
        report["error"] = scrub(str(exc))
        raise
    finally:
        report["ended"] = utc()
        save("api-results.json", report)
    print("D1-A PASS:", len(tests), "assertions; real Flask/PostgreSQL via direct and Vite proxy.")


def db_verify():
    cfg = config()
    rows = db_snapshot(cfg)
    own = [r for r in rows if RUN.name in r["customer_name"]]
    report = json.loads((RUN / "browser-results.json").read_text(encoding="utf-8"))
    expected = []
    def walk(suite):
        for spec in suite.get("specs", []):
            for test in spec["tests"]:
                for result in test["results"]:
                    for attachment in result.get("attachments", []):
                        if attachment["name"] in ("real-persisted-order", "uncertain-post-actual-write"):
                            body = json.loads(base64.b64decode(attachment["body"]))
                            expected.append(body.get("order", body.get("stored_order")))
        for child in suite.get("suites", []):
            walk(child)
    for suite in report["suites"]:
        walk(suite)
    matched = []
    for order in expected:
        record = next((r for r in rows if r["id"] == order["id"]), None)
        keys = ("id", "customer_name", "product_name", "quantity", "status")
        valid = record is not None and all(record[k] == order[k] for k in keys)
        if valid:
            valid = datetime.datetime.fromisoformat(record["created_at"]) == datetime.datetime.fromisoformat(order["created_at"])
        matched.append({"id": order["id"], "matches_browser_response": valid})
    markers = {RUN.name + suffix for suffix in ("-api", "-browser", "-uncertain-post")}
    valid = (len(rows) == 3 and {r["customer_name"] for r in own} == markers
             and len(expected) == 2 and all(r["matches_browser_response"] for r in matched))
    save("database-after-browser.json", {"observed_at": utc(), "project": PROJECT,
                                       "status": "PASS" if valid else "FAIL", "rows": rows,
                                       "browser_response_comparison": matched,
                                       "expected_marker_count": 3, "mock_row_absent": all("-mock-only" not in r["customer_name"] for r in rows)})
    if not valid:
        raise AssertionError("Database rows do not match actual browser writes")
    version = checked(compose("exec", "-T", "order-db", "postgres", "--version")).strip()
    flask = checked(compose("exec", "-T", "order-app", "python", "-c",
                            "import sys,importlib.metadata as m;print(sys.version);print('Flask',m.version('Flask'));print('psycopg',m.version('psycopg'))")).strip()
    ids = checked(compose("ps", "-q")).splitlines()
    runtime = []
    for container in ids:
        item = json.loads(checked(["docker", "inspect", "--format",
                                  '{"id":"{{.Id}}","image_id":"{{.Image}}","name":"{{.Name}}","health":"{{.State.Health.Status}}"}', container]))
        runtime.append(item)
    save("runtime-versions.json", {"observed_at": utc(), "postgres": version,
                                  "backend": flask, "containers": runtime,
                                  "note": "Local Docker image IDs, not independently verified registry digests"})
    logs = checked(compose("logs", "--no-color", "--tail", "300"))
    (RUN / "containers.final.log").write_text(scrub(logs), encoding="utf-8")
    print("Database verification PASS: 3 real rows; browser responses match PostgreSQL, including timestamps; mock row absent.")


def stop_vite():
    record_path = RUN / "vite.json"
    if not record_path.is_file():
        save("vite-cleanup.json", {"status": "NOT_RUN", "reason": "No Vite process was started"})
        return
    record = json.loads(record_path.read_text(encoding="utf-8"))
    pid = int(record["pid"])
    query = "Get-CimInstance Win32_Process -Filter 'ProcessId = " + str(pid) + "' | Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
    output = checked(["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", query]).strip()
    if output:
        process = json.loads(output)
        line = process["CommandLine"].lower()
        expected = str(FRONTEND / "node_modules/vite/bin/vite.js").lower()
        if expected not in line or "--port 5173" not in line or "--host 127.0.0.1" not in line:
            raise RuntimeError("Vite PID no longer matches owned command; refusing to terminate")
        checked(["taskkill", "/PID", str(pid), "/T", "/F"])
    deadline = time.monotonic() + 10
    available = False
    while time.monotonic() < deadline:
        try:
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 5173))
            available = True
            break
        except OSError:
            time.sleep(0.2)
    save("vite-cleanup.json", {"observed_at": utc(), "owned_pid": pid,
                               "status": "PASS" if available else "FAIL",
                               "port_5173_released": available,
                               "termination": "Only command-validated Vite process tree of this run"})
    if not available:
        raise RuntimeError("Vite port is still occupied")
    print("Owned Vite process stopped; port 5173 released.")


def cleanup():
    config()
    # Only stop labelled containers of this run; never down/reset/remove.
    ids = checked(["docker", "ps", "-a", "--filter", "label=com.docker.compose.project=" + PROJECT,
                   "--format", "{{.ID}}"]).splitlines()
    if ids:
        checked(compose("stop", "--timeout", "20", "order-app", "order-db"), timeout=80)
    after = inventory()
    before = json.loads((RUN / "preflight.json").read_text())["before"]
    old = {c["ID"]: c for c in after["containers"] if not c["Names"].startswith(PROJECT)}
    unchanged = all(c["ID"] in old and c["State"] == old[c["ID"]]["State"] for c in before["containers"])
    volume = PROJECT + "_order-db-data"
    checked(compose("ps", "-a", "--format", "json"))
    save("cleanup.json", {"observed_at": utc(), "project": PROJECT,
                          "test_containers_stopped": all(c["State"] == "exited" for c in after["containers"]
                                                        if c["Names"].startswith(PROJECT)),
                          "test_volume_retained": volume in after["volumes"],
                          "prior_container_states_unchanged": unchanged,
                          "prior_volumes_retained": all(v in after["volumes"] for v in before["volumes"]),
                          "after": after})
    print("Test containers stopped. Named volume and all artifacts retained.")


def initialize():
    run_id = "d1-" + datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(2)
    target = ROOT / "bang-chung/m4/orderflow/e2e" / run_id
    target.mkdir(parents=True, exist_ok=False)
    def git(*args):
        return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()
    files = {}
    excluded = {".git", "node_modules", "dist", "__pycache__", ".venv"}
    for directory, dirs, names in os.walk(ROOT):
        dirs[:] = [name for name in dirs if name not in excluded
                   and pathlib.Path(directory, name).resolve() != (ROOT / "bang-chung/m4/orderflow/e2e").resolve()]
        for name in names:
            p = pathlib.Path(directory, name)
            files[p.relative_to(ROOT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    baseline = {"run_id": run_id, "project": "orderflow-" + run_id.lower(),
                "head": git("rev-parse", "HEAD"), "branch": git("branch", "--show-current"),
                "dirty": git("status", "--porcelain=v1", "--untracked-files=all"), "files": files,
                "observed_at": utc(), "note": "Historical E2E run artifacts excluded from input hash inventory"}
    (target / "baseline.json").write_text(json.dumps(baseline, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"run_dir": str(target), "run_id": run_id, "project": baseline["project"]}))


def main():
    global RUN, PROJECT
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=["init", "preflight", "up", "vite", "api", "db-verify", "stop-vite", "cleanup"])
    parser.add_argument("--run-dir")
    args = parser.parse_args()
    if args.stage == "init":
        if args.run_dir:
            raise RuntimeError("init generates its own unique run path; do not supply --run-dir")
        initialize()
        return
    if not args.run_dir:
        parser.error("--run-dir is required for execution stages")
    RUN = pathlib.Path(args.run_dir).resolve()
    expected = (ROOT / "bang-chung/m4/orderflow/e2e").resolve()
    if RUN.parent != expected or not (RUN / "baseline.json").is_file():
        raise RuntimeError("Run path must be an initialized D1 evidence directory")
    PROJECT = json.loads((RUN / "baseline.json").read_text(encoding="utf-8"))["project"]
    if not PROJECT.startswith("orderflow-d1-"):
        raise RuntimeError("Unexpected test project prefix")
    globals()[args.stage.replace("-", "_")]()


if __name__ == "__main__":
    main()
