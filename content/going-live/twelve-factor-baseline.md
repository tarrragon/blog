---
title: "十二要素基線"
date: 2026-07-06
description: "服務能上線了、但一換機器 / 換環境就出狀況、設定散在各處、log 不知道去哪找時回來讀 — 讓服務好部署好搬家的幾條基本紀律"
weight: 4
tags: ["going-live", "deployment", "twelve-factor", "foundations"]
---

十二要素（Twelve-Factor App）是一套「讓服務好部署、好搬家、好擴展」的基本紀律。它原本是 12 條，但對第一次上線的人，真正天天影響你的是其中幾條——它們的共通精神是**把「會變的東西」跟「code」分開**，這樣同一份 code 才能在你的筆電、staging（上線前的測試環境）、prod 三個環境不改一行就跑起來。

## 設定進環境變數，不寫死在 code 裡

這是最重要的一條。資料庫位址、API 金鑰、外部服務 URL——這些**每個環境都不一樣**的東西，不能寫死在 code 裡，要從**環境變數**讀：

```text
# 不要這樣（寫死，換環境要改 code）
db = connect("mysql://root:secret@localhost/app")

# 要這樣（從環境變數讀，換環境只換變數）
db = connect(env("DATABASE_URL"))
```

好處：同一份 code 在本機讀到本機的 DB、在 prod 讀到 prod 的 DB，不用改 code、也不會把 prod 密鑰簽進 git。密鑰怎麼安全注入見 [Backend secret 治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/)。

## process 無狀態，資料放外面

你的 app process 本身**不存資料**——使用者 session、上傳的檔案、快取，都放到外部的後端服務（DB、Redis、物件儲存），不放在 app 的記憶體或本機磁碟。

為什麼：這樣你才能隨時砍掉一個 app、重開一個、或同時開三個副本擋流量——因為資料不在 app 裡，砍了不會掉東西。這條是水平擴展的前提，深入見 [運行期維運 無狀態設計](/operations/02-horizontal-scaling/stateless-design/)。

## log 輸出到 stdout，當成串流

不要讓 app 自己寫 log 檔、自己輪替。把 log 直接印到標準輸出（stdout），交給外面的平台去收集、儲存、查詢。這樣不管 app 跑在哪、幾個副本，log 都被統一收走，你不用去每台機器翻檔案。

## 明確宣告依賴、開機即用

app 依賴哪些套件，要寫在 lockfile 裡（`package-lock.json`、`go.sum`、`requirements.txt`），部署時照 lockfile 裝——不靠「機器上剛好有」。而且 app 要能**快速啟動、優雅關閉**（收到停止信號先處理完手上的請求再退），這樣部署新版、自動重啟才順。

## dev / prod 儘量一致

本機開發環境跟線上環境的差距越小，「在我電腦上能跑、上線卻壞」的機率越低。這條在你用舊版 runtime 的 client 環境時特別關鍵——本機要對齊線上的版本與行為，見 [Dotfile 模組十：Prod Parity](/linux/dotfile/10-prod-parity/)。

## 判讀：這些不是潔癖，是省未來的痛

每一條都對應一個「沒做就會在某個時刻痛」的場景：設定寫死 → 換環境或輪替密鑰時要改 code、還可能把密鑰簽進 git；process 有狀態 → 想加一台擋流量卻發現 session 掉了；log 寫檔 → 出事要 SSH 進每台機器撈。還有一條上 PaaS 當天就會撞的：**listen 在平台指派的 `$PORT`**——Heroku / Cloud Run 這類平台會給你一個環境變數指定 port，app 沒讀它、寫死自己的 port，就部署失敗。第一次上線可以先抓住「設定進環境變數」跟「process 無狀態」這兩條（上 PaaS 再加 `$PORT`），其餘隨服務長大再補。

## 下一步

服務好部署了，接著常要決定「有狀態的那部分（資料庫）自己顧還是託管」——見 [自架還是託管：以資料庫為例](/going-live/self-host-vs-managed-db/)。config 注入與 runtime 設定的進階做法見 [Backend 部署平台](/backend/05-deployment-platform/)。
