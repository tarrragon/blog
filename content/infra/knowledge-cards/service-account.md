---
title: "Service Account（服務帳號）"
date: 2026-10-24
description: "程式、排程或雲端服務要以自己的身分呼叫雲端 API、要決定給它哪些角色、遇到「狀態正常卻呼叫失敗」的權限問題、或看到 IAM 綁定裡的 serviceAccount: 成員時，查服務帳號是什麼、它的權限要從「它能做什麼」與「誰能以它的身分行事」兩邊設，以及它和人的帳號在管理上的差別"
weight: 62
tags: ["infra", "knowledge-cards", "gcp", "iam", "security"]
---

服務帳號（service account）是給程式使用、而不是給人使用的身分。部署在雲端的程式要呼叫雲端的 API（讀寫儲存、發布訊息、修改帳單設定）時，以一個服務帳號的身分送出請求，[IAM](/infra/knowledge-cards/iam/) 依這個身分被授予的角色決定是否允許這個請求。GCP 的服務帳號以 email 形式的位址識別（`<name>@<project-id>.iam.gserviceaccount.com`），在 IAM 綁定裡寫成 `serviceAccount:<位址>`；AWS 對應的是 IAM role 被服務或程式承接（assume，AWS 中文文件寫作「擔任」）的用法。

## 概念位置

服務帳號在 IAM 裡同時是一個身分、也是一個資源，權限也因此分成兩邊來設：

- **它是一個身分：它能做什麼**。在 [IAM](/infra/knowledge-cards/iam/) 授予它角色，決定它能對哪些資源做什麼。例如一個[依預算通知停用帳單的函式](/infra/cloud-providers/gcp/spend-protection-gcp-budget-killswitch/)，它的服務帳號要有解除專案帳單連結的角色。
- **它是一個資源：誰能以它的身分行事**。別的身分要「以它的身分行事」（把它掛到 VM 上、用它部署函式、用它的身分呼叫另一個服務），要對這個服務帳號本身持有角色。例如在啟用 OS Login 的 VM 上，登入一台掛著服務帳號的 VM 的人，要有那個服務帳號的 `roles/iam.serviceAccountUser`。

兩邊漏設時的症狀不同。「誰能以它的身分行事」那一邊漏設時，部署或掛載的那一步就被拒絕；「它能做什麼」那一邊漏設時，部署與元件狀態都顯示正常，要到程式實際呼叫 API 的那一刻請求才被拒絕。

程式取得服務帳號憑證的方式有兩種：在雲端裡執行的程式（VM、函式、容器）由平台自動提供短期憑證，不需要金鑰；在雲端外面的程式（CI、地端伺服器）可以下載一把長期金鑰，或改用 [workload identity](/backend/knowledge-cards/workload-identity/) 以外部平台簽發的 token 換到短期憑證。長期金鑰外洩等於這個身分外洩，能用短期憑證時不發金鑰。

## 可觀察訊號

- IAM 綁定裡出現 `serviceAccount:` 開頭的成員：`gcloud projects get-iam-policy <project-id>` 列得出專案層級的綁定
- VM 掛著哪個服務帳號：`gcloud compute instances describe <instance-name> --zone=<zone>` 輸出的 `serviceAccounts[].email`；用主控台預設值建立的 VM 會掛上 Compute Engine 預設服務帳號（`<project-number>-compute@developer.gserviceaccount.com`），instance template 的 `describe` 對它顯示為 `default`
- 程式的錯誤訊息是 `The caller does not have permission` 或 403，而部署與狀態都顯示正常：服務帳號缺少這個 API 呼叫需要的權限，用 `gcloud iam roles describe <role>` 查它持有的角色裡有沒有那一項；錯誤訊息沒寫權限名稱時，API 參考文件裡那個方法的頁面列出它需要的權限（例如 `projects.getBillingInfo` 需要 `resourcemanager.projects.get`）

## 設計責任

- **一個用途一個服務帳號**：每個程式或每類工作用自己的服務帳號，角色只給它需要的那幾個（[least privilege](/backend/knowledge-cards/least-privilege/)）；共用預設服務帳號時，任何一個程式被入侵都拿得到其他程式的權限
- **查角色實際包含哪些權限**：角色名稱看起來管的那件事，角色本身不一定涵蓋其中的每一個動作，`gcloud iam roles describe <role>` 列得出它的權限清單；例如 GCP 的 `roles/billing.projectManager` 只能建立與刪除專案的帳單連結，讀取帳單狀態要另外的權限
- **呼叫鏈上的每一段都要授權**：由事件觸發的程式（Pub/Sub 推送、Eventarc 觸發器）有「觸發器以哪個身分呼叫程式」與「程式以哪個身分呼叫 API」兩段，兩段各自要有角色
- **設定完以實際觸發驗收**：「它能做什麼」那一邊的缺漏在部署時看不出來，所以設定完要實際觸發一次它要做的事、看結果，而不是看部署的回傳值，做法見[平常不動作的防護機制的部署驗證](/report/protection-proves-itself-by-firing/)
- **「以它的身分行事」的權限也是權限**：持有某個服務帳號的 `roles/iam.serviceAccountUser` 或可以產生它的 token 的人，等同持有那個服務帳號的全部角色，盤點權限時要一起算

## 鄰卡

- [IAM](/infra/knowledge-cards/iam/) — 服務帳號的角色由 IAM 授予
- [Workload Identity](/backend/knowledge-cards/workload-identity/) — 雲端外的程式不發金鑰、以短期憑證取得服務帳號身分
- [Least Privilege（最小權限）](/backend/knowledge-cards/least-privilege/) — 服務帳號的角色範圍原則
- [OS Login](/infra/knowledge-cards/os-login/) — 登入掛著服務帳號的 VM 時另外需要 `roles/iam.serviceAccountUser`
