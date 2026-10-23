---
title: "OS Login"
date: 2026-10-23
description: "GCP 專案要讓 SSH 登入權限跟著 Google 帳號與 IAM 走、或盤點專案 metadata 裡殘留的 SSH 公鑰時，查 OS Login 的運作方式、IAM role 與它和 metadata 金鑰的差別"
weight: 57
tags: ["infra", "knowledge-cards", "gcp", "ssh", "iam"]
---

OS Login 是 GCP Compute Engine 管理 VM 登入權限的機制：VM 在有人登入時，向 Google 查詢這個 Google 帳號的 SSH 公鑰與它在 [IAM](/infra/knowledge-cards/iam/) 裡的角色，依角色決定是否允許登入、是否允許使用 sudo。持有 `roles/compute.osLogin` 的帳號以一般使用者登入，持有 `roles/compute.osAdminLogin` 的帳號另外拿得到 sudo。帳號停用或角色移除之後，下一次登入就會失敗，不必回到每台 VM 刪除公鑰。啟用方式是在專案或 VM 的 metadata 設定 `enable-oslogin=TRUE`。

## 概念位置

GCP 上把 SSH 公鑰交給 VM 有兩種方式。metadata 金鑰把公鑰寫進專案或 VM 的 metadata，VM 上的 guest agent 讀出來寫進 `authorized_keys`，和 Google 帳號沒有連動，運作方式等同 [SSH](/infra/knowledge-cards/ssh/) 卡描述的靜態公鑰。OS Login 是在登入當下由中央服務提供公鑰與授權判斷，屬於[伺服器管理通道的設計](/infra/03-network-foundation/management-access-channel/)模型裡主機登入驗證這一層的「中央提供」做法；AWS 的 EC2 Instance Connect 屬於同一類，它在連線前推送一把只在短時間內有效的公鑰。讓登入權限自動到期的另一種做法見 [SSH Certificate（SSH 憑證）](/infra/knowledge-cards/ssh-certificate/)。

OS Login 常與 GCP 的 [Identity-Aware Proxy（身分感知代理）](/infra/knowledge-cards/identity-aware-proxy/) 一起用。兩者都依 IAM 判斷，但檢查的是兩件事：IAP 的 IAM 權限決定是否允許開通道，OS Login 的 IAM 權限決定進入通道之後是否允許登入、是否允許使用 sudo。

## 可觀察訊號

- 專案或 VM 的 metadata 有 `enable-oslogin=TRUE`：專案層級用 `gcloud compute project-info describe` 查，VM 層級用 `gcloud compute instances describe <instance-name> --zone=<zone>` 查
- 登入 VM 之後的使用者名稱是由 Google 帳號位址轉成的名稱，不是管理員自己在 metadata 裡指定的名稱
- 專案 metadata 的 `ssh-keys` 欄位仍然有公鑰——啟用 OS Login 的 VM 不再讀它，但沒啟用的 VM 仍會讀，盤點時要一起清

## 設計責任

啟用 OS Login 時要決定：

- **啟用順序**：啟用之後 VM 不再接受 metadata 裡的金鑰，所以先把登入角色授予每一位管理員、對一台 VM 啟用並連通，再做專案層級
- **啟用範圍**：專案層級啟用涵蓋專案內所有 VM，VM 層級的設定會蓋過專案層級；組織要新建的 VM 一律啟用時用 Organization Policy 的 `compute.requireOsLogin`，既有 VM 要另外盤點
- **sudo 的授予**：`roles/compute.osAdminLogin` 只給確實需要 root 權限的群組，其餘給 `roles/compute.osLogin`
- **服務帳號的附帶權限**：VM 以服務帳號身分執行時，登入的使用者另外需要那個服務帳號的 `roles/iam.serviceAccountUser`
- **登入時的兩步驟驗證**：metadata 設 `enable-oslogin-2fa=TRUE` 後，每一次 SSH 登入都要再過一次 Google 帳號的第二因素

## 鄰卡

- [SSH](/infra/knowledge-cards/ssh/) — OS Login 取代的是靜態 `authorized_keys` 的金鑰發放方式
- [IAM](/infra/knowledge-cards/iam/) — OS Login 的登入權限由 IAM role 決定
- [Identity-Aware Proxy（身分感知代理）](/infra/knowledge-cards/identity-aware-proxy/) — 常一起使用的通道授權層
- [GCP VM 的 SSH 管理通道](/infra/03-network-foundation/gcp-iap-ssh-access/) — 啟用 OS Login 與授予角色的指令
