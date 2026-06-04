# StreamBox - Render Frontend

表向き：StartUp Search（マルチエンジン検索サービス）
実態：YouTubeプロキシビューア

## デプロイ手順（GitHub → Render）

### 1. GitHubにリポジトリを作る
1. https://github.com/new でリポジトリ作成（Private推奨）
2. このフォルダの中身を全部アップロード

### 2. Renderにデプロイ
1. https://render.com → ログイン
2. [New +] → [Web Service]
3. GitHubのリポジトリを選択して Connect
4. 以下を設定：
   - Name: 好きな名前（例: startup-search）
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn app:app`
5. [Environment] タブ → [Add Environment Variable]
   - Key: `AGAMES_URL`
   - Value: `http://11.jpn.gg:10225`
6. [Create Web Service] → デプロイ完了を待つ

### 3. 動作確認
- サイトURL（例: https://startup-search.onrender.com）にアクセス
- StartUp検索画面が表示されればOK
- 検索ボックスに `YouTube` と入力してEnter → StreamBoxが起動するか確認

## ファイル構成

```
streambox-render/
├── app.py              ← Renderサーバー（フロント配信 + APIプロキシ）
├── requirements.txt    ← Pythonパッケージ一覧
├── render.yaml         ← Render設定ファイル（オプション）
├── .gitignore
├── README.md
└── static/
    └── index.html      ← StartUp偽装UI + StreamBox本体
```

## 操作ガイド（StreamBox）

| 操作 | 動作 |
|------|------|
| 検索窓に `YouTube` + Enter | StreamBox起動 |
| それ以外の文字 + Enter | 選択した検索エンジンで検索 |
| Tabキー | 検索エンジンを切替 |
| Kキー（入力欄以外で） | google.com へ緊急退出 |
| 動画クリック | 音量警告 → 再生 |

## UptimeRobot（コールドスタート防止・推奨）

1. https://uptimerobot.com で無料アカウント作成
2. [Add New Monitor] → HTTP(s)
3. URL: `https://あなたのサイト.onrender.com/health`
4. Interval: 5分
5. これで15分のコールドスタートを防げる
