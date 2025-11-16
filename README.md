# サンプル: ログインと「特定ユーザーがパスワードを管理できる」API

このサンプルは、Flask を使った最小構成のログインシステムです。特徴:

- ユーザー登録 / ログイン / ログアウト
- 自分のパスワード変更（現在のパスワードを確認）
- "password_manager" ロールを持つユーザーは他人のパスワードを変更できる
- パスワード変更は監査ログに記録される

注意: これは学習用のサンプルです。運用時は下記の「セキュリティ上の注意点」を必ず確認してください。

## ファイル
- app.py - メインアプリケーション
- models.py - DBモデル（User、PasswordChangeLog）
- requirements.txt - 必要パッケージ

## 起動方法（ローカル）
1. 仮想環境を作る (推奨)
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate

2. 依存をインストール
   pip install -r requirements.txt

3. DB 初期化（初回）
   export FLASK_APP=app.py
   python -c "from app import create_app; app=create_app(); from models import db; \
   with app.app_context(): db.create_all()"

4. (任意) 初期管理者ユーザーを作る: Python REPL で直接作成
   from app import create_app
   from models import db, User
   app = create_app()
   with app.app_context():
       u = User(username="admin")
       u.set_password("strong-password")
       u.role = "password_manager"
       db.session.add(u)
       db.session.commit()

5. アプリ起動（開発）
   python app.py
   -> http://localhost:5000

## API（主なエンドポイント）
- POST /register
  - JSON: { "username": "user", "password": "pw" }
  - 説明: 新規ユーザー作成（多くのシステムでは管理者のみ作成にする）

- POST /login
  - JSON: { "username": "user", "password": "pw" }
  - 説明: セッションクッキーを発行

- POST /logout
  - 説明: ログアウト（ログインが必要）

- POST /change_password
  - 認証要
  - JSON: { "current_password": "old", "new_password": "new" }
  - 説明: 自分のパスワードを変更

- POST /admin/change_password/<user_id>
  - 認証要、role="password_manager" 必須
  - JSON: { "new_password": "new", "reason": "support-reset" }
  - 説明: マネージャが別のユーザーのパスワードを上書きできる

- POST /admin/set_manager/<user_id>
  - 認証要、role="password_manager" 必須
  - 説明: 指定ユーザーを password_manager に昇格

- GET /admin/logs
  - 認証要、role="password_manager" 必須
  - 説明: パスワード変更の監査ログを取得

## セキュリティ上の注意点（必ず検討してください）
- HTTPS を必須にする（TLS）。平文HTTPは絶対に避ける。
- パスワードハッシュは PBKDF2 を使っていますが、Argon2 や bcrypt を検討してください（passlib など）。
- パスワード変更操作は監査ログに記録していますが、ログの保存先、アクセス制御を厳密にしてください。
- 認証情報の露出を防ぐために、ログやエラーメッセージに平文パスワードを残さないでください。
- 2要素認証（2FA）の導入を検討してください。
- ブルートフォース対策（レートリミット、アカウントロック、CAPTCHA）を実装してください。
- 管理者（password_manager）ロールの付与は慎重に。少数の信頼できるアカウントに限定してください。
- パスワードリセットのワークフロー（メールによる確認トークン等）を導入するのが一般的です（このサンプルでは省略しています）。

## 拡張アイデア
- JWT を使ったトークンベース認証
- メール経由のパスワードリセット（トークン、期限付き）
- 2FA（TOTP）
- 詳細な監査（who/when/from-IP/old-hash-not-stored）とアラート
- 管理UI（Web 管理画面）と RBAC（細かい権限管理）
