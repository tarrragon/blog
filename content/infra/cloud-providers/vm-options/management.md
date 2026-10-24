---
title: "代理程式、中繼資料服務、初始化腳本、維護行為與標籤"
date: 2026-10-24
description: "建立虛擬機時管理區塊的選項：業者裝在主機裡的代理程式與它的 plugin 怎麼決定開關、中繼資料服務的第二版存取驗證、開機時執行的初始化腳本、底層硬體維護時主機會被遷移還是重開，以及標籤"
weight: 6
tags: ["infra", "cloud-providers", "vm", "agent", "metadata"]
---

建立頁的管理區塊不影響主機的規格，影響的是主機跟業者的服務怎麼互動：業者的程式在主機裡做什麼、主機怎麼取得自己的設定、業者維修硬體時主機會怎樣。這些欄位多半維持預設就好，例外是要用到某個 plugin 背後的服務、或對中繼資料服務的安全性有要求的時候。例子以 Oracle Cloud 的建立頁為主，Google Cloud 與 AWS 的對應名稱列在文末的表。

## 代理程式與 plugin：業者裝在主機裡的程式

業者的平台映像預先裝了業者自己的代理程式（agent）：Oracle Cloud 的叫 Oracle Cloud Agent，Google Cloud 的是 guest agent 與 Ops Agent，AWS 的是 SSM Agent 與 CloudWatch agent。代理程式在主機裡執行，替業者的雲端服務做需要在作業系統裡完成的事：回報 CPU 與記憶體用量、收集日誌、執行遠端指令、替區塊磁碟建立連線、替管理通道服務把臨時的登入金鑰放進主機。

Oracle Cloud 把每一項功能做成一個 plugin，在建立頁上個別開關。判斷要開哪些，看會不會用到它背後的那個服務：

- **要用 Oracle Cloud 的 Bastion 服務、以 managed SSH session 登入**：一定要開 Bastion plugin。主機沒有放 SSH 金鑰、又沒有開這個 plugin 時，managed SSH session 建不起來。
- **要在主控台看主機的 CPU、記憶體圖表**：維持 Compute Instance Monitoring 開啟。
- **其餘**：維持建立頁的預設。預設關閉的 plugin 背後的服務（作業系統修補、弱點掃描這類）都要在各自的服務裡另外啟用，用到時再回來打開。

Plugin 建立之後可以在主機頁面的 Oracle Cloud Agent 分頁開關，官方說明變更最多要 10 分鐘生效，所以建立時漏開的 plugin 不必重建主機。Plugin 本身是代理程式的一部分，官方的 plugin 說明頁沒有寫它的費用；費用來自它背後的服務，例如 Logging 服務依收進來的日誌量計費。Oracle Cloud 全部 plugin 的用途與一台 A1 Ubuntu 主機上的實際預設值，整理在 [Oracle Cloud 建立主機的實測紀錄](/infra/cloud-providers/oracle-cloud/launch-instance-walkthrough/) 的 Management 段。

## 中繼資料服務與 Authorization header

每台雲端主機都能從一個只有主機自己連得到的位址（`169.254.169.254`）查詢自己的資訊：主機 ID、所在區域、建立時放進去的公鑰與初始化腳本。這個服務叫實例中繼資料服務（instance metadata service，IMDS），cloud-init（多數 Linux 雲端映像預先裝好、開機時讀中繼資料做初始設定的程式）開機時就是從這裡讀出 SSH 公鑰。知識卡見 [Instance Metadata Service（實例中繼資料服務）](/infra/knowledge-cards/instance-metadata-service/)。

Oracle Cloud 的中繼資料服務有兩個版本。第一版的路徑是 `/opc/v1`，請求不必帶任何標頭；第二版的路徑是 `/opc/v2`，每個請求都要帶 `Authorization: Bearer Oracle` 這個標頭。建立頁上的「Require an authorization header」打開之後，主機只接受第二版的請求，送到第一版路徑的請求回 404、沒帶標頭的請求被拒絕。這個限制防的是 SSRF（伺服器端請求偽造）：主機上的網頁應用程式有漏洞、被誘導去讀某個網址時，攻擊者可以讓它讀 `169.254.169.254` 而取得主機的資訊；多數這類漏洞只能控制網址、加不了自訂的標頭，所以要求標頭能擋掉這條路。

這個選項成立的前提是主機上讀中繼資料的程式都會用第二版。官方〈Getting Instance Metadata〉列出支援第二版的平台映像只有 Oracle Linux 與 Oracle Autonomous Linux（2020 年中之後的版本），並寫明其他平台映像、多數自訂與市集映像不支援；自訂的 Linux 映像要 cloud-init 20.3 以上、Oracle Cloud Agent 0.0.19 以上才可能支援。而建立頁的預設值跟這份清單不一致：2026-10-24 建立 Ubuntu 24.04 的 A1 主機時，這個選項預設是開的，Ubuntu 卻不在清單上。所以：

- **用 Oracle Linux 平台映像**：維持開啟。
- **用 Ubuntu 這類不在清單上的映像**：開著建立的主機，第一次開機後要確認公鑰有寫進 `authorized_keys`、初始化腳本有執行、代理程式的 plugin 狀態正常；這三項都是讀中繼資料才做得到的事，任何一項沒發生就先懷疑這個選項。那台 Ubuntu 主機因為容量不足沒有建成，這次沒有驗到它在 Ubuntu 上的實際結果。
- **用自訂或市集映像**：先查那個映像的說明有沒有支援第二版，查不到就先不開。

## 初始化腳本

建立頁的進階選項裡可以放一段初始化腳本（Oracle Cloud 的主控台欄位叫 Initialization script，經由中繼資料的 user data 傳進主機），常用來安裝套件、建立使用者、寫入設定檔。Oracle Cloud 的限制是使用者資料與其他中繼資料合計不超過 32,000 bytes；官方提醒腳本裡不要放會觸發重開機的指令，否則可能讓主機建立失敗。

腳本什麼時候執行，三家不一樣。Oracle Cloud 與 AWS 的初始化腳本由 cloud-init 執行，預設只在第一次開機時執行一次，之後修改中繼資料不會重新執行；Google Cloud 的 startup script 每次開機都執行，腳本要寫成重複執行也不出錯。要讓同一份設定能在新主機上重現，腳本本身要放在版本控制裡；主機與網路這些資源本身改用 IaC 管理，見 [IaC 工具選型與 state 地基](/infra/01-minimal-iac/iac-tool-state-backend/)。

## 硬體維護時的行為

業者要維修主機底下的實體硬體時，上面的虛擬機只有兩種處理方式：搬到另一台實體主機上（業者叫遷移，不中斷的叫即時遷移，要重開一次的叫重開機遷移），或是原地停機、等硬體修好再開。建立頁上的維護欄位決定業者優先用哪一種、以及硬體恢復之後主機要不要自動啟動。Oracle Cloud 有兩個欄位：

- **Live migration**：預設是讓 Oracle 選擇遷移方式。選「盡量用即時遷移」時，Oracle Cloud 先嘗試即時遷移，失敗時改用重開機遷移；選「送出維護通知」時，Oracle Cloud 在維護前通知，主機在期限前沒有自己重開的話，就由 Oracle Cloud 做即時遷移。部分機型不支援即時遷移，開了安全開機（shielded instance）的主機也不支援即時遷移與重開機遷移，見 [安全開機](/infra/cloud-providers/vm-options/shielded-boot/)。
- **Restart after infrastructure maintenance**（2026-10-24 主控台上的名稱，官方文件寫作 Restore instance lifecycle state after infrastructure maintenance）：預設勾選，維護事件影響到主機時，主機在硬體恢復之後自動重開。不勾的話，主機恢復後維持停止狀態，要手動啟動。

Google Cloud 對應的欄位是 On host maintenance（遷移或終止）與 Automatic restart，AWS 由 scheduled events 通知維護時間。一般用途維持預設。服務不能接受沒有預警的重開時，選送出維護通知，收到通知後在期限前、挑服務離峰的時間自己重開主機，或先把流量切到另一台。

## 標籤

標籤（tag）是附在資源上的鍵值對，用來分類資源、分攤費用、寫自動化腳本時篩選資源。Oracle Cloud 有兩種：自由格式標籤（有建立資源權限的人都能加）與預先定義的標籤（要有那個標籤命名空間的權限）。標籤可以在建立之後再加。成本分攤與標籤規範見 [Tagging 規範與 Secrets 不進 code](/infra/08-governance-habits/tagging-secrets/)。

## 各家的欄位名稱：代理程式、中繼資料、初始化腳本與維護行為

| 概念                   | Oracle Cloud                              | Google Cloud                            | AWS                             |
| ---------------------- | ----------------------------------------- | --------------------------------------- | ------------------------------- |
| 業者的代理程式         | Oracle Cloud Agent                        | Guest agent、Ops Agent                  | SSM Agent、CloudWatch agent     |
| 中繼資料服務的存取驗證 | Require an authorization header（IMDSv2） | 固定要求 `Metadata-Flavor: Google` 標頭 | IMDSv2（token required）        |
| 初始化腳本             | Initialization script（cloud-init）       | Startup script（每次開機執行）          | User data（cloud-init）         |
| 維護時的行為           | Live migration、Restart after maintenance | On host maintenance、Automatic restart  | Scheduled events、Auto-recovery |

不放 SSH 金鑰、改用 Bastion 登入時 plugin 要怎麼配合，見 [登入：SSH 金鑰、預設使用者、建立後加金鑰與不放金鑰時的登入服務](/infra/cloud-providers/vm-options/login/) 的〈不放金鑰時的登入服務〉。
