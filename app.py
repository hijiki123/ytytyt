"""
StreamBox - Render版
フロントエンド配信 + Agamesへのリバースプロキシ
"""
import os
import requests
from flask import Flask, request, Response, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder="static")
CORS(app)

AGAMES_URL = os.environ.get("AGAMES_URL", "http://11.jpn.gg:10225")
PROXY_TIMEOUT = 60


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/search")
@app.route("/api/info")
def api_proxy_light():
    path = request.path
    params = request.args.to_dict()
    try:
        resp = requests.get(
            f"{AGAMES_URL}{path}",
            params=params,
            timeout=35,
        )
        return Response(
            resp.content,
            status=resp.status_code,
            content_type=resp.headers.get("Content-Type", "application/json"),
        )
    except requests.exceptions.Timeout:
        return {"error": "Agamesサーバーがタイムアウトしました"}, 504
    except requests.exceptions.ConnectionError:
        return {"error": "Agamesサーバーに接続できません"}, 502


@app.route("/api/stream")
def api_proxy_stream():
    video_id = request.args.get("v", "")
    if not video_id:
        return {"error": "動画IDが必要です"}, 400

    headers = {}
    if "Range" in request.headers:
        headers["Range"] = request.headers["Range"]

    try:
        upstream = requests.get(
            f"{AGAMES_URL}/api/stream",
            params={"v": video_id},
            headers=headers,
            stream=True,
            timeout=PROXY_TIMEOUT,
        )
    except requests.exceptions.ConnectionError:
        return {"error": "Agamesサーバーに接続できません"}, 502

    def generate():
        for chunk in upstream.iter_content(chunk_size=32 * 1024):
            if chunk:
                yield chunk

    resp_headers = {
        "Content-Type": upstream.headers.get("Content-Type", "video/mp4"),
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-cache",
    }
    if "Content-Length" in upstream.headers:
        resp_headers["Content-Length"] = upstream.headers["Content-Length"]
    if "Content-Range" in upstream.headers:
        resp_headers["Content-Range"] = upstream.headers["Content-Range"]

    return Response(
        generate(),
        status=upstream.status_code,
        headers=resp_headers,
    )


@app.route("/health")
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"🚀 Render proxy 起動中 → http://0.0.0.0:{port}")
    app.run(host="0.0.0.0", port=port)
