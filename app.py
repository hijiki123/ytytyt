# app.py
import os
import urllib.error
import urllib.request

from flask import Flask, request, Response, jsonify, send_from_directory, stream_with_context

app = Flask(__name__)

PORT = int(os.environ.get("SERVER_PORT", 10225))
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPSTREAM = os.environ.get("UPSTREAM_BASE", "http://11.jpn.gg:10225").rstrip("/")


def add_cors(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Range, X-StreamBox-Auth"
    return response


@app.after_request
def after_request(response):
    return add_cors(response)


@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        return add_cors(Response(""))


def upstream_url(path: str) -> str:
    return UPSTREAM + path


def proxy_buffered(path: str, method: str = "GET", extra_headers=None, body: bytes | None = None):
    req = urllib.request.Request(upstream_url(path), data=body, method=method)
    for k, v in (extra_headers or {}).items():
        if v is not None and v != "":
            req.add_header(k, v)

    try:
        with urllib.request.urlopen(req, timeout=30) as upstream:
            payload = upstream.read()
            status = getattr(upstream, "status", 200)
            headers = dict(upstream.headers.items())
    except urllib.error.HTTPError as e:
        payload = e.read()
        status = e.code
        headers = dict(e.headers.items())
    except Exception as e:
        return jsonify({"error": f"Upstream error: {str(e)}"}), 502

    content_type = headers.get("Content-Type", "application/octet-stream")
    resp = Response(payload, status=status, content_type=content_type)

    for key in ("Cache-Control", "Content-Disposition", "ETag", "Last-Modified"):
        if key in headers:
            resp.headers[key] = headers[key]

    return resp


def proxy_stream(path: str, extra_headers=None):
    req = urllib.request.Request(upstream_url(path), method="GET")
    for k, v in (extra_headers or {}).items():
        if v is not None and v != "":
            req.add_header(k, v)

    try:
        upstream = urllib.request.urlopen(req, timeout=60)
    except urllib.error.HTTPError as e:
        payload = e.read()
        return Response(
            payload,
            status=e.code,
            content_type=e.headers.get("Content-Type", "application/json"),
        )
    except Exception as e:
        return jsonify({"error": f"Upstream stream error: {str(e)}"}), 502

    status_code = getattr(upstream, "status", 200)
    content_type = upstream.headers.get("Content-Type", "video/mp4")
    content_length = upstream.headers.get("Content-Length")
    content_range = upstream.headers.get("Content-Range")
    accept_ranges = upstream.headers.get("Accept-Ranges", "bytes")

    def generate():
        try:
            while True:
                chunk = upstream.read(1024 * 64)
                if not chunk:
                    break
                yield chunk
        finally:
            upstream.close()

    resp = Response(
        stream_with_context(generate()),
        status=status_code,
        content_type=content_type,
        direct_passthrough=True,
    )
    resp.headers["Accept-Ranges"] = accept_ranges
    resp.headers["Cache-Control"] = "no-cache"
    if content_length:
        resp.headers["Content-Length"] = content_length
    if content_range:
        resp.headers["Content-Range"] = content_range
    return resp


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/index.html")
def index_html():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/api/<path:endpoint>", methods=["GET", "POST", "OPTIONS"])
def api_proxy(endpoint):
    if endpoint == "stream":
        range_header = request.headers.get("Range")
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.youtube.com/",
        }
        if range_header:
            headers["Range"] = range_header
        return proxy_stream("/api/stream?" + request.query_string.decode("utf-8") if request.query_string else "/api/stream", headers)

    path = f"/api/{endpoint}"
    if request.query_string:
        path += "?" + request.query_string.decode("utf-8")

    headers = {}

    ct = request.headers.get("Content-Type")
    if ct:
        headers["Content-Type"] = ct

    auth = request.headers.get("X-StreamBox-Auth")
    if auth:
        headers["X-StreamBox-Auth"] = auth

    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header

    user_agent = request.headers.get("User-Agent")
    if user_agent:
        headers["User-Agent"] = user_agent

    body = request.get_data() if request.method == "POST" else None
    return proxy_buffered(path, method=request.method, extra_headers=headers, body=body)


@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200


if __name__ == "__main__":
    print("StreamBox proxy 起動中 → http://0.0.0.0:" + str(PORT))
    app.run(host="0.0.0.0", port=PORT, threaded=True)
