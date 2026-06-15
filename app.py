import os
from flask import Flask, request, Response, jsonify, send_from_directory, stream_with_context
import requests

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

@app.route("/")
@app.route("/index.html")
def index():
    return send_from_directory(BASE_DIR, "index.html")

@app.route("/api/<path:endpoint>", methods=["GET", "POST"])
def api_proxy(endpoint):
    # 上流サーバーへのURLを構築
    url = f"{UPSTREAM}/api/{endpoint}"
    
    # フロントエンドからのヘッダーをコピー（Hostヘッダーなどは上流とコンフリクトするので除外）
    headers = {k: v for k, v in request.headers if k.lower() not in ["host", "content-length"]}
    
    # YouTubeストリーミング用のUser-Agent/Referer固定（元のロジックを踏襲）
    if endpoint == "stream":
        headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        headers["Referer"] = "https://www.youtube.com/"

    try:
        if endpoint == "stream":
            # ストリーミングエンドポイントの場合（チャンク転送）
            upstream_resp = requests.request(
                method=request.method,
                url=url,
                params=request.args,
                headers=headers,
                stream=True,
                timeout=60
            )
            
            def generate():
                for chunk in upstream_resp.iter_content(chunk_size=65536):
                    if chunk:
                        yield chunk

            response_headers = dict(upstream_resp.headers)
            response_headers["Cache-Control"] = "no-cache"
            
            return Response(
                stream_with_context(generate()),
                status=upstream_resp.status_code,
                content_type=upstream_resp.headers.get("Content-Type", "video/mp4"),
                headers={k: v for k, v in response_headers.items() if k.lower() not in ["transfer-encoding", "connection"]}
            )
        else:
            # 通常のAPIリクエスト（auth, app, search, infoなど）
            upstream_resp = requests.request(
                method=request.method,
                url=url,
                params=request.args,
                headers=headers,
                data=request.get_data(),
                timeout=30
            )
            
            return Response(
                upstream_resp.content,
                status=upstream_resp.status_code,
                content_type=upstream_resp.headers.get("Content-Type", "application/json")
            )

    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Upstream proxy error: {str(e)}"}), 502

@app.route("/health")
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == "__main__":
    print(f"StreamBox proxy 起動中 → http://0.0.0.0:{PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
