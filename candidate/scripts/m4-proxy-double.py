import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

UPSTREAM = os.getenv(
    "M4_UPSTREAM_URL",
    "http://127.0.0.1:8081",
).rstrip("/")
TIMEOUT_SECONDS = 5


class ProxyHandler(BaseHTTPRequestHandler):
    server_version = "M4ProxyDouble/1.0"

    def send_json(self, status, payload):
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def forward(self, method, upstream_path):
        body = None
        headers = {"Accept": "application/json"}

        if method == "POST":
            length = self.headers.get("Content-Length")
            if length is None:
                self.send_json(400, {"error": "Missing Content-Length"})
                return

            try:
                length = int(length)
            except ValueError:
                self.send_json(400, {"error": "Invalid Content-Length"})
                return

            if length < 0 or length > 1024 * 1024:
                self.send_json(413, {"error": "Request body too large"})
                return

            body = self.rfile.read(length)
            headers["Content-Type"] = self.headers.get(
                "Content-Type",
                "application/json",
            )

        request = Request(
            f"{UPSTREAM}{upstream_path}",
            data=body,
            headers=headers,
            method=method,
        )

        try:
            with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                status = response.status
                response_body = response.read()
                content_type = response.headers.get(
                    "Content-Type",
                    "application/json",
                )
        except HTTPError as exc:
            status = exc.code
            response_body = exc.read()
            content_type = exc.headers.get(
                "Content-Type",
                "application/json",
            )
        except (URLError, TimeoutError, OSError):
            self.send_json(502, {"error": "Upstream unavailable"})
            return

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

    def do_GET(self):
        routes = {
            "/api/orders": "/orders",
            "/api/health": "/health",
            "/api/ready": "/ready",
        }

        upstream_path = routes.get(self.path)
        if upstream_path is None:
            self.send_json(404, {"error": "Route not found"})
            return

        self.forward("GET", upstream_path)

    def do_POST(self):
        if self.path != "/api/orders":
            self.send_json(404, {"error": "Route not found"})
            return

        self.forward("POST", "/orders")

    def do_PUT(self):
        self.send_json(405, {"error": "Method not allowed"})

    def do_PATCH(self):
        self.send_json(405, {"error": "Method not allowed"})

    def do_DELETE(self):
        self.send_json(405, {"error": "Method not allowed"})

    def log_message(self, format_string, *args):
        # Log request metadata only; do not log request bodies or credentials.
        super().log_message(format_string, *args)


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", 8082), ProxyHandler)
    print("M4 proxy double listening on 127.0.0.1:8082")
    print(f"Upstream backend: {UPSTREAM}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping M4 proxy double.")
    finally:
        server.server_close()