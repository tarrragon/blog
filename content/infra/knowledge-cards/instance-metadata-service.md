---
title: "Instance Metadata Service（實例中繼資料服務）"
date: 2026-10-24
description: "看到建立主機頁上的 IMDSv2、authorization header、metadata 選項，主機上的程式要取得自己的 ID、區域或身分憑證，或評估網頁應用程式的 SSRF 漏洞會不會讓攻擊者讀到主機的憑證時，查中繼資料服務提供什麼、第二版的存取驗證防的是什麼"
weight: 104
tags: ["infra", "knowledge-cards", "cloud", "security"]
---

實例中繼資料服務（instance metadata service，IMDS）是雲端業者在每台主機上提供的一個 HTTP 端點，位址固定是 `169.254.169.254`，只有主機自己連得到。主機上的程式向它查詢這台主機的資訊：主機 ID、所在區域與可用區、網路設定、建立時放進去的 SSH 公鑰與初始化腳本，以及業者發給這台主機的身分憑證（讓主機上的程式不必存放長期金鑰就能呼叫雲端 API，見 [Service Account（服務帳號）](/infra/knowledge-cards/service-account/)）。

## 概念位置

開機流程依賴它：cloud-init 在主機第一次開機時從中繼資料服務讀出 [SSH](/infra/knowledge-cards/ssh/) 公鑰寫進 `authorized_keys`、讀出初始化腳本並執行。業者的代理程式也從這裡讀主機的設定。

同一個特性也是它的風險：主機上任何能發 HTTP 請求的程式都讀得到它。網頁應用程式有 SSRF（server-side request forgery，伺服器端請求偽造）漏洞時，攻擊者可以讓應用程式替他去讀 `169.254.169.254`，取得主機的身分憑證，再拿那份憑證在雲端帳號裡以主機的權限行事。

第二版的存取方式（AWS 與 Oracle Cloud 叫 IMDSv2）要求請求帶上特定的標頭或先取得一個 token，第一版不帶標頭的請求直接拒絕。多數 SSRF 漏洞只讓攻擊者控制網址、控制不了標頭，所以這一個要求就擋掉了大部分的攻擊路徑。Google Cloud 的中繼資料伺服器固定要求 `Metadata-Flavor: Google` 標頭，作用相同。

## 可觀察訊號

- 建立頁上有「Require an authorization header」（Oracle Cloud）、「Metadata version: V2 only (token required)」（AWS）這類選項
- 主機上的舊程式或舊版工具讀不到中繼資料、請求回錯誤：它還在用第一版的請求方式
- 安全掃描報告指出某台主機允許 IMDSv1：那台主機上的應用程式一旦有 SSRF 漏洞，身分憑證就讀得到

## 設計責任

- **新主機**：開啟第二版的強制要求；Oracle Cloud 的條件是映像檔支援第二版，目前的平台映像都支援
- **既有主機改成只允許第二版**：先確認主機上讀中繼資料的程式（代理程式、SDK、自己的腳本）都已支援第二版，再切換
- **主機的身分權限**：中繼資料服務發的憑證帶著主機身分的全部權限，權限只給這台主機上的程式需要的那些

## 鄰卡

- [Service Account（服務帳號）](/infra/knowledge-cards/service-account/) — 中繼資料服務發放的憑證代表的身分
- [IAM](/infra/knowledge-cards/iam/) — 決定那份憑證能做什麼
- [代理程式、中繼資料服務與維護行為](/infra/cloud-providers/vm-options/management/) — 建立主機時的中繼資料服務選項
