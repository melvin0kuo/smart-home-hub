# 手機與外網私人存取

先完成本機平台，使用自己的 VPN／Tailscale 私人 HTTPS，保留平台登入。Repo 不提供公開網站。

1. 執行 npm run build --prefix frontend。
2. .env 啟用 HUB_SERVE_FRONTEND=true，將自己的完整 HTTPS Origin 加到 HUB_ALLOWED_ORIGINS，保留本地開發 Origin。
3. 後端只監聽 127.0.0.1:8000。
4. 按 [Tailscale Serve 官方指南](https://tailscale.com/kb/1242/tailscale-serve) 完成 HTTPS 與帳號授權，不混用公開 Funnel。

    tailscale serve --bg --https=443 http://127.0.0.1:8000
    tailscale serve status

手機須在被授權 tailnet 並開啟 VPN，以自己的 Serve URL 登入。主機須開機，服務須運行；Serve 背景設定不等於本平台自動開機啟動。更新前端須重新 Build，私人入口使用 frontend/dist。不要取消 TLS 驗證或把密碼、Token 放 URL。
