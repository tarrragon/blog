---
title: "部署到底是什麼"
date: 2026-07-06
description: "第一次要把服務放上線、不確定「部署」到底在做什麼、跟在本機跑 npm start 差在哪時回來讀 — 上線這個動作的本質"
weight: 1
tags: ["going-live", "deployment", "foundations"]
---

部署（deploy）就是「讓你的程式跑在一台**永遠開著、且網際網路連得到**的電腦上」，而不是跑在你會關機、會睡眠、只有你自己連得到的筆電上。你在本機 `npm start` / `php -S` 跑起來，跟服務「上線」之間，變的是這台電腦的四個性質，而不只是那行指令。

## 從本機跑到上線，變的是這四件事

同樣一份 code，放到線上要滿足四個本機不需要的條件：

- **機器永遠開著**：你的筆電會關、會睡、會斷網。線上要一台 24 小時開著的電腦（雲主機、VPS、或平台幫你顧的機器），你闔上筆電服務也不能停。
- **網際網路連得到**：本機是 `localhost`（只有你這台連得到）。線上要一個**公開位址**——一個公網 IP，通常再掛一個域名（`example.com`）指過去，別人才連得到。
- **沒人顧也要活著**：本機是你手動 `start`、崩了你再手動重跑。線上要能**開機自動啟動、崩潰自動重啟**——半夜掛了不能等你醒來。
- **面對的是真實流量與環境**：線上同時被很多人打（並發）、被掃描攻擊（安全）、而且設定跟你本機不同（資料庫位址、密鑰、環境變數都不一樣）。

「部署」這個動作，本質就是把 code 搬到一台滿足這四點的機器上、並讓它以正確的設定跑起來。

## 一次部署實際包含哪些步驟

把上面四點拆成動作，一次最基本的部署大致是：

1. **準備一台線上機器**（或一個幫你跑 code 的平台）——這是「[主機形態](/going-live/hosting-spectrum/)」要選的。
2. **把 code 送上去**——git pull、或打包成 [container image](/backend/knowledge-cards/container/) 推到 [registry](/ci/knowledge-cards/container-registry/)（存放 image 的倉庫）再拉下來。
3. **裝好依賴、帶上正確設定**——線上的 DB 位址、密鑰用[環境變數](/going-live/twelve-factor-baseline/)注入，不是寫死在 code 裡。
4. **讓它開機自動起、崩潰自動重啟**——用 systemd、或平台/[container 編排器](/backend/knowledge-cards/container-per-service/)管生命週期。
5. **讓外面連得到**——設[域名與 HTTPS](/going-live/domain-and-https/)、開對的 port。

有資料庫的服務還多一步：第一次上線要跑一次 **schema 初始化 / migration** 把資料表建起來——步驟 3 帶的是「DB 位址」，不等於「DB 裡有表」，漏了這步就是 code 上去了、一連 DB 就爆的典型翻車（migration 屬「一次性 admin process」，每次改資料表結構都要跑）。

常見的誤解是把「部署」等同步驟 2 的「把 code 傳上去」，但真正讓服務「活著且可用」的是其餘幾步。

## 判讀：你其實已經在部署了

如果你用過 Heroku / Vercel / Render 這種平台按一下就上線，你已經部署過了——只是平台把上面 1、4、5 全包了，你只做了 2、3，也就是**平台幫你扛掉大部分部署工作**（這正是[主機形態光譜](/going-live/hosting-spectrum/)的一端）。理解「部署包含哪五步」，是為了在平台包不住、要自己顧機器時，知道每一步在做什麼。

## 邊界與下一步

這篇講的是「單次把服務弄上線」。真實服務會反覆部署新版本，這時要處理「更新時怎麼不中斷服務」——舊版還在服務、新版怎麼接手、出錯怎麼退回。那是進階的部署策略，見 [Backend 部署 rollout / drain / rollback](/backend/05-deployment-platform/deployment-rollout-drain-rollback/) 與 [CI/CD](/ci/)。

先搞懂「我的 code 到底該跑在哪」，往下讀 [主機形態光譜](/going-live/hosting-spectrum/)。
