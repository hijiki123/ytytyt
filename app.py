import urllib.request
import urllib.parse
from flask import Flask, request, Response, send_from_directory
import os

app = Flask(__name__)
UPSTREAM_URL = "http://11.jpn.gg:10225"

def proxy_buffered(path, method="GET", extra_headers=None, body=None):
    url = f"{UPSTREAM_URL}{path}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    }
    if extra_headers:
        for k, v in extra_headers.items():
            headers[k] = v

    req = urllib.request.Request(url, data=body, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as res:
            resp_headers = dict(res.headers)
            return Response(res.read(), status=res.status, headers=resp_headers)
    except urllib.error.HTTPError as e:
        return Response(e.read(), status=e.code, headers=dict(e.headers))
    except Exception as e:
        return Response(str(e), status=502)


@app.route("/api/<path:endpoint>", methods=["GET", "POST", "OPTIONS"])
def api_proxy(endpoint):
    if request.method == "OPTIONS":
        return Response(""), 200

    path = f"/api/{endpoint}"
    if request.query_string:
        path += "?" + request.query_string.decode("utf-8")

    headers = {}
    for k, v in request.headers.items():
        if k.lower() in ["content-type", "x-streambox-auth", "range"]:
            headers[k] = v

    body = None
    if request.method == "POST":
        body = request.get_data()
        if body:
            headers["Content-Length"] = str(len(body))

    return proxy_buffered(path, method=request.method, extra_headers=headers, body=body)


# ★ ここが抜けていた：トップページを返すルート
@app.route("/")
def index():
    return send_from_directory(".", "index.html")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
