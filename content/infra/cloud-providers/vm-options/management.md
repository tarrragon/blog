---
title: "代理程式、中繼資料服務與維護行為"
date: 2026-10-24
description: "建立虛擬機時管理區塊的選項：業者裝在主機裡的代理程式與它的各個 plugin 做什麼、中繼資料服務的存取驗證、開機時執行的初始化腳本、底層硬體維護時主機會被遷移還是重開，以及標籤"
weight: 6
tags: ["infra", "cloud-providers", "vm", "agent", "metadata"]
---

這篇說明建立頁上不影響主機規格、而影響「主機跟業者的服務怎麼互動」的選項。這些欄位多半可以維持預設，例外是要用到某個 plugin 的功能、或對中繼資料服務的安全性有要求的時候。範圍以 Oracle Cloud 的建立頁為主，其他兩家對照名稱。

## 代理程式與 plugin：業者裝在主機裡的程式

平台映像預先裝了業者自己的代理程式，Oracle Cloud 的叫 Oracle Cloud Agent。代理程式在主機裡執行，替業者的雲端服務做需要在作業系統裡完成的事：回報 CPU 與記憶體用量、收集日誌、執行遠端指令、替區塊磁碟建立連線。每一項功能是一個 plugin，可以個別開關。

Oracle Cloud 官方列出的 plugin 與各自的用途：

| Plugin                                                       | 做什麼                                                     |
| ------------------------------------------------------------ | ---------------------------------------------------------- |
| Compute Instance Monitoring                                  | 回報主機的健康、容量與效能指標給 Monitoring 服務           |
| Custom Logs Monitoring                                       | 把主機上的自訂日誌送進 Logging 服務；不支援 Ampere A1 機型 |
| Compute Instance Run Command                                 | 從主控台或 API 在主機裡執行腳本，用來遠端設定與排錯        |
| Bastion                                                      | 讓 Bastion 服務對沒有公開 IP 的主機建立 SSH 工作階段       |
| Block Volume Management                                      | 替主機設定區塊磁碟的連線                                   |
| OS Management Hub Agent                                      | 管理與監看作業系統的更新與修補                             |
| Vulnerability Scanning                                       | 掃描主機上的弱點，例如需要更新的套件                       |
| Management Agent                                             | 替整合 Management Agent 的服務收集作業系統與應用程式的資料 |
| Cloud Guard Workload Protection                              | 管理 Instance Security agent 的更新                        |
| High Performance Computing                                   | HPC 機型的 RDMA 網路設定與監控                             |
| Fleet Application Management、Oracle Java Management Service | 給對應的應用程式管理服務用                                 |

建立頁的預設值依映像檔與代理程式的版本而定。實測一個 Ubuntu 24.04 的 A1 主機，建立頁上預設開啟的是 Compute Instance Monitoring、Custom Logs Monitoring、Compute Instance Run Command 與 Cloud Guard Workload Protection，Bastion 與其餘 plugin 預設關閉。

判斷要開哪些，看會不會用到它背後那個服務：

- **要用 Bastion 服務的 managed SSH session 登入**：一定要開 Bastion。主機沒有放 SSH 金鑰、又沒有開這個 plugin 時，Bastion 的 managed SSH session 建不起來。
- **要在主控台看主機的 CPU、記憶體圖表**：維持 Compute Instance Monitoring 開啟。
- **其餘**：用不到的維持預設或關閉，代理程式少做一件事。

Plugin 在建立之後可以在主機頁面的 Oracle Cloud Agent 分頁開關，官方說明變更最多要 10 分鐘生效。所以建立時漏開的 plugin 不必重建主機，回頭打開再等幾分鐘即可。官方的 plugin 說明頁沒有提到費用；plugin 本身是代理程式的一部分，費用來自它背後的服務（例如 Logging 收進來的日誌量）。

## 中繼資料服務與 Authorization header

每台雲端主機都能從一個只有主機自己連得到的位址（`169.254.169.254`）查詢自己的資訊：主機 ID、所在區域、建立時放進去的公鑰與初始化腳本。這個服務叫實例中繼資料服務（instance metadata service，IMDS），cloud-init 開機時就是從這裡讀出 SSH 公鑰。知識卡見 [Instance Metadata Service（實例中繼資料服務）](/infra/knowledge-cards/instance-metadata-service/)。

Oracle Cloud 建立頁上的「Require an authorization header」選項，要求所有對中繼資料服務的請求改用第二版的端點並帶上授權標頭，第一版的請求一律拒絕；前提是映像檔支援第二版。這個限制防的是 SSRF（伺服器端請求偽造）：主機上的網頁應用程式有漏洞、被誘導去讀某個網址時，攻擊者可以讓它讀 `169.254.169.254` 而取得主機的資訊；多數這類漏洞只能控制網址、加不了自訂的標頭，所以要求標頭能擋掉這條路。目前的平台映像都支援第二版，維持開啟即可。

## 初始化腳本

建立頁的進階選項裡可以放一段初始化腳本（user data），主機第一次開機時由 cloud-init 執行，常用來安裝套件、建立使用者、寫入設定檔。Oracle Cloud 的限制是使用者資料與其他中繼資料合計不超過 32,000 bytes；官方提醒腳本裡不要放會觸發重開機的指令，否則可能讓主機建立失敗。

初始化腳本只在第一次開機時執行一次，之後修改中繼資料不會重新執行。要讓同一份設定能在新主機上重現，腳本本身要放在版本控制裡；長期維護的設定改用設定管理工具或 IaC，見 [最小可行 IaC](/infra/01-minimal-iac/)。

## 硬體維護時的行為

業者要維修主機底下的實體硬體時，上面的虛擬機要先移走。Oracle Cloud 建立頁上有兩個相關的欄位：

- **Live migration**：預設是讓 Oracle 選擇遷移方式。「盡量用即時遷移」會把主機在不中斷的情況下搬到另一台健康的實體主機，失敗時改用重開機遷移；「送出維護通知」會在維護前通知，主機在期限前沒有自己重開的話就被即時遷移。部分機型不支援即時遷移。
- **Restart after infrastructure maintenance**：預設勾選，維護事件影響到主機時，主機在硬體恢復之後自動重開。不勾的話，主機恢復後維持停止狀態，要手動啟動。

一般用途維持預設。服務不能接受沒有預警的重開時，選送出維護通知，並在服務裡處理那個通知。

## 標籤

標籤（tag）是附在資源上的鍵值對，用來分類資源、分攤費用、寫自動化腳本時篩選資源。Oracle Cloud 有兩種：自由格式標籤（有建立資源權限的人都能加）與預先定義的標籤（要有那個標籤命名空間的權限）。標籤可以在建立之後再加。成本分攤與標籤規範見 [治理好習慣](/infra/08-governance-habits/)。

## 各家的欄位名稱

| 概念                   | Oracle Cloud                              | Google Cloud                            | AWS                             |
| ---------------------- | ----------------------------------------- | --------------------------------------- | ------------------------------- |
| 業者的代理程式         | Oracle Cloud Agent                        | Guest agent、Ops Agent                  | SSM Agent、CloudWatch agent     |
| 中繼資料服務的存取驗證 | Require an authorization header（IMDSv2） | 固定要求 `Metadata-Flavor: Google` 標頭 | IMDSv2（token required）        |
| 初始化腳本             | Initialization script（cloud-init）       | Startup script / user-data              | User data                       |
| 維護時的行為           | Live migration、Restart after maintenance | On host maintenance、Automatic restart  | Scheduled events、Auto-recovery |

## 延伸閱讀：用到這些設定的功能

- [登入：SSH 金鑰與預設使用者](/infra/cloud-providers/vm-options/login/)：不放 SSH 金鑰、改用 Bastion session 登入時，Bastion plugin 的角色
- [磁碟：開機磁碟的大小、效能、加密與去留](/infra/cloud-providers/vm-options/storage/)：Block Volume Management plugin 設定的那些區塊磁碟
