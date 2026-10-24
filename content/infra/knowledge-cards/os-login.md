---
title: "OS Login"
date: 2026-10-23
description: "GCP 專案要讓 SSH 登入權限跟著 Google 帳號與 IAM 走、啟用 OS Login 之後管理員或 CI 連不進 VM、或盤點專案 metadata 裡殘留的 SSH 公鑰時，查 OS Login 的運作方式、IAM role 與它和 metadata 金鑰的差別"
weight: 57
tags: ["infra", "knowledge-cards", "gcp", "ssh", "iam"]
---

OS Login 是 GCP Compute Engine 管理 VM 登入權限的機制：VM 在有人登入時，向 Google 查詢這個 Google 帳號的 SSH 公鑰與它在 [IAM](/infra/knowledge-cards/iam/) 裡的角色，依角色決定是否允許登入、是否允許使用 sudo。持有 `roles/compute.osLogin` 的帳號以一般使用者登入，持有 `roles/compute.osAdminLogin` 的帳號另外拿得到 sudo。帳號停用或角色移除之後，下一次登入就會失敗，不必回到每台 VM 刪除公鑰；已經建立的工作階段不受影響，要另外在 VM 上結束（`loginctl terminate-user <username>`），結束已建立工作階段的動作在應用程式的層次叫 [session invalidation](/backend/knowledge-cards/session-invalidation/)。啟用方式是在專案或 VM 的 metadata 設定 `enable-oslogin=TRUE`。

## 概念位置

OS Login 出現之前，GCP 把 SSH 公鑰交給 VM 的方式是 metadata 金鑰：公鑰寫在專案或 VM 的 metadata 的 `ssh-keys` 欄位，VM 上的 guest agent（GCP 映像預裝、負責把 metadata 套用到作業系統的常駐程式）讀出來寫進對應帳號的 `authorized_keys`。這些公鑰和 Google 帳號沒有連動，帳號停用後公鑰仍然留在 metadata 裡，運作方式等同 [SSH](/infra/knowledge-cards/ssh/) 卡描述的靜態公鑰。

OS Login 改成每次登入時才向 Google 查詢，登入權限因此跟著帳號走。不分廠商來看，這是主機登入驗證（登入主機用的金鑰怎麼發、怎麼收回）裡「由中央服務決定可用的公鑰」的那一種，AWS 的 EC2 Instance Connect 屬於同一類，差別是它在連線前推送一把只在短時間內有效的公鑰；讓登入權限自動到期的另一種做法見 [SSH Certificate（SSH 憑證）](/infra/knowledge-cards/ssh-certificate/)。

OS Login 常與 GCP 的 [Identity-Aware Proxy（身分感知代理）](/infra/knowledge-cards/identity-aware-proxy/) 一起用。兩者都依 IAM 判斷，但檢查的是兩件事：IAP 的 IAM 權限決定是否允許開通道，OS Login 的 IAM 權限決定進入通道之後是否允許登入、是否允許使用 sudo。

## 可觀察訊號

- 專案或 VM 的 metadata 有 `enable-oslogin=TRUE`：專案層級用 `gcloud compute project-info describe` 查，輸出的 `commonInstanceMetadata.items` 裡列著專案層級的 metadata；VM 層級用 `gcloud compute instances describe <instance-name> --zone=<zone>` 查，看輸出的 `metadata.items`
- 登入 VM 之後的使用者名稱是由 Google 帳號位址轉成的名稱（例如 `alice_example_com`），不是管理員自己在 metadata 裡指定的名稱
- 專案 metadata 的 `ssh-keys` 欄位仍然有公鑰——啟用 OS Login 的 VM 不再讀它，但沒啟用的 VM 仍會讀，盤點時要一起清

## 設計責任

OS Login 啟用後，VM 只認 IAM 角色，metadata 裡的公鑰立即失效，所以啟用前要先把角色與順序排好：

- **啟用順序**：先把登入角色授予每一位管理員與每一個要登入 VM 的[服務帳號](/infra/knowledge-cards/service-account/)（CI、Ansible）、對一台 VM 啟用並連通，再做專案層級；順序反過來時，還沒拿到角色的管理員與自動化工具在啟用那一刻就登不進去
- **啟用範圍**：專案層級啟用涵蓋專案內所有 VM，VM 層級的設定會蓋過專案層級；組織要新建的 VM 一律啟用時用 Organization Policy 的 `compute.requireOsLogin`，既有 VM 要另外盤點
- **sudo 的授予**：`roles/compute.osAdminLogin` 只給確實需要 root 權限的群組，其餘給 `roles/compute.osLogin`
- **服務帳號的附帶權限**：VM 以服務帳號身分執行時，登入的使用者另外需要那個服務帳號的 `roles/iam.serviceAccountUser`。從主控台用預設值建立的 VM 會掛上 Compute Engine default service account，所以多數 VM 都落在這個情況；VM 掛的是哪個服務帳號，看 `gcloud compute instances describe` 輸出的 `serviceAccounts[].email`
- **組織外的帳號**：外包人員用組織以外的 Google 帳號時，要在組織層級另外授予 `roles/compute.osLoginExternalUser` 才能登入
- **登入時的兩步驟驗證**：metadata 設 `enable-oslogin-2fa=TRUE` 後，每一次 SSH 登入都要再過一次 Google 帳號的第二因素；還沒在 Google 帳號上設定第二因素的管理員會在啟用那一刻被擋在外面

## 鄰卡

- [SSH](/infra/knowledge-cards/ssh/) — OS Login 取代的是靜態 `authorized_keys` 的金鑰發放方式
- [IAM](/infra/knowledge-cards/iam/) — OS Login 的登入權限由 IAM role 決定
- [Identity-Aware Proxy（身分感知代理）](/infra/knowledge-cards/identity-aware-proxy/) — 常一起使用的通道授權層
- [GCP VM 的 SSH 與 RDP 管理通道](/infra/03-network-foundation/gcp-iap-ssh-access/#ssh-金鑰在-gcp-上的管理位置metadata-金鑰與-os-login-的啟用順序與還原) — 授予角色、單台先行啟用與還原的指令
