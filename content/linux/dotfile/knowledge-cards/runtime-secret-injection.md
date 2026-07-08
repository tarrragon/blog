---
title: "機密 runtime 注入"
date: 2026-07-08
description: "要決定 token / 金鑰放哪、能不能烤進 image 或提交進（即使私有的）repo 時回來讀"
weight: 51
tags: ["linux", "container", "security", "knowledge-cards"]
---

機密（token、金鑰、密碼）的正確放法是 runtime 注入：不烤進 image layer、也不提交進 git（連私有 repo 都不），而是存成 host 側的 gitignored 檔或 secrets manager、在 container 啟動時用環境變數 / `--env-file` 注入。理由是 image layer 與 git repo 都不是機密容器——它們會被複製、快取、分享、永久留存，機密一旦進去就跟著到處跑、且很難真正抹除。把機密跟可分享的 artifact（image、Dockerfile、設定）分離，是這條原則的核心。

## image layer 不是機密

Dockerfile 裡 `ENV TOKEN=...` 或 `COPY` 一個機密檔進去，那顆機密就烤進某一層 image。`docker history --no-trunc` 讀得到 `ENV` 值與 build 參數、解開 layer 就拿得到 COPY 進去的檔。image 一旦 push 到 registry、被 CI 快取、被別人 pull，機密就跟著散出去。即使你在後面的 layer 刪掉它，前一層仍留著——layer 是疊加的、刪除不會回溯抹除。

## 私有 repo 也不是保險箱

「放私有 repo 應該安全」是常見的誤判。私有降低曝露、但不消除：有讀取權的協作者、CI / 整合服務、不小心設成公開、fork、以及 git 歷史永久留存（後來刪掉也還在歷史裡、要 rewrite 且視同已洩）都是曝露面。長效機密（例如有效一年的 token）blast radius 大，不值得為省事賭在「這個 repo 一直是私有」上。這也是 secret-scanning 工具存在的理由——它們專門掃 repo 裡不該出現的機密。

## 正解：runtime 注入、機密與 artifact 分離

把三件事分開放：

- **image / Dockerfile / 設定** → 進 repo（公開或私有都行、因為不含機密）。
- **機密** → host 側的 gitignored 檔（如 `.env`、權限 `600`）或 secrets manager。
- **注入** → `docker run --env-file .env`（或 `-e`、Docker secrets）在 runtime 把機密餵進去。

這讓 image 是可重現、可分享的乾淨 artifact、機密則跟著環境走。認證因此也跟 image 生命週期解耦：rebuild image 不影響機密、換機密只改注入的檔。私鑰不外流的同源原則見 [SSH 金鑰儲放與 authorized_keys](/linux/dotfile/knowledge-cards/ssh-key-storage/)。

## 判讀訊號 / 邊界

- 想「把 token 寫進 Dockerfile 省事」時就是這條原則該擋下的時刻——改成 `.env` + 注入。
- **build-time 真的需要機密**（例如 build 時要拉私有套件）時，別用 `ARG` / `ENV`（會進 layer），用 BuildKit 的 `--mount=type=secret`——它在 build 期掛載、不寫進 image layer。多數應用機密只在 runtime 用、連這個都不需要。
- **輪替**：機密到期前換、裝置遺失或疑似外洩就撤銷重發。gitignored `.env` 對單機個人用途夠；多機 / 團隊改用 secrets manager。
