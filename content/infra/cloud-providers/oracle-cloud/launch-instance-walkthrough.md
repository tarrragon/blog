---
title: "Oracle Cloud 建立主機的實測紀錄：主控台各分頁的 Always Free 設定值與遇到的錯誤"
date: 2026-10-24
description: "在 Oracle Cloud 主控台建立一台 Always Free 的 A1 Ubuntu 主機時，Basic information、Security、Networking、SSH keys、Storage 與 Management 各分頁填了什麼、為什麼這樣填，等效的 CLI 指令，以及容量不足、VCN 選單找不到、Bastion plugin 預設關閉這幾個實測遇到的狀況"
weight: 3
tags: ["infra", "cloud-providers", "oracle-cloud", "oci", "vm", "free-tier"]
---

這篇記錄在 Oracle Cloud 主控台建立一台主機的實際設定，目標是 Always Free 額度內、沒有公開 IP、之後經由 Bastion 服務登入的 A1 Ubuntu 主機。範圍從進入 Compute → Instances → Create instance 開始，到按下 Create 為止；每個欄位背後的概念連到 [建立雲端虛擬機的選項](/infra/cloud-providers/vm-options/) 底下對應的那一篇，這裡只寫 Oracle Cloud 的欄位與這次的取值。實測日期 2026-10-24，區域 `ap-batam-1`。

進建立頁之前要先建好兩項資源：放實驗資源的 compartment，以及主機要接上的 VCN 與 private subnet。這次兩者都先用 CLI 建好（compartment `blog-verify`、VCN `verify-vcn`、subnet `private-subnet`，subnet 的 security list 只放行同一個 subnet 內的 22 port），所以建立頁上一律選既有的。

## Basic information：名稱、compartment、位置、映像檔與機型

| 欄位                  | 這次的值                                     | 理由與對應的概念篇                                                                                                      |
| --------------------- | -------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| Name                  | `verify-a1`                                  | 自動產生的 `instance-<日期>-<時間>` 在清單裡認不出用途                                                                  |
| Create in compartment | `blog-verify`                                | 實驗資源集中在一個 compartment，清理時不碰 root 裡的設定                                                                |
| Availability domain   | AD-1                                         | 這一區只有一個 AD，見 [位置](/infra/cloud-providers/vm-options/placement/)                                              |
| Capacity type         | On-demand                                    | Always Free 以隨用隨付計算；preemptible 會被收回，見 [機型與映像檔](/infra/cloud-providers/vm-options/shape-and-image/) |
| Fault domain          | Let Oracle choose the best fault domain      | 單一台主機指定故障域沒有好處，還會縮小可用容量                                                                          |
| Image                 | Canonical Ubuntu 24.04（build 2026.09.18-0） | 平台映像，架構跟著機型選 aarch64                                                                                        |
| Shape                 | `VM.Standard.A1.Flex`，1 OCPU、6 GB          | Always Free 上限是 2 OCPU、12 GB，先用一半，不夠再加（加要重開機，不必重建）                                            |

「Change shape」的視窗依處理器分欄。這一區的 Ampere 欄有 `VM.Standard.A1.Flex` 並標示 Always Free-eligible；AMD 欄只有 `VM.Standard.E5.Flex`，沒有 Always Free 的 `VM.Standard.E2.1.Micro`。E5.Flex 不在免費額度內，選了會照一般價格計費。區域之間提供的機型不同，這一點見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)。

## Security：Shielded instance

Secure Boot、Measured Boot、Trusted Platform Module 三項預設都是 Disabled，這次維持關閉。三項在建立之後不能改，要測試這個功能時另外建一台；判斷要不要開見 [安全開機](/infra/cloud-providers/vm-options/shielded-boot/)。

## Networking：VCN、subnet 與公開 IP

| 欄位                                     | 這次的值                                         |
| ---------------------------------------- | ------------------------------------------------ |
| Primary network                          | Select existing virtual cloud network            |
| Virtual cloud network compartment        | `blog-verify`                                    |
| Virtual cloud network                    | `verify-vcn`                                     |
| Subnet                                   | Select existing subnet → `private-subnet`        |
| Private IPv4 address                     | Automatically assign                             |
| Automatically assign public IPv4 address | 關閉（private subnet 不允許公開 IP，開關是灰的） |
| VNIC name                                | 留空（顯示用，之後可以改）                       |
| DNS record                               | Yes                                              |
| Use network security groups              | No                                               |

這一頁實測卡住的地方是 VCN 下拉選單：它只列出「Virtual cloud network compartment」那一欄選定的 compartment 裡的 VCN，而那一欄預設停在 root compartment。`verify-vcn` 建在 `blog-verify`，所以要先把那一欄切過去，選單裡才會出現它。

選「Create new virtual cloud network」會建一個新的 VCN，它帶的預設 security list 對 `0.0.0.0/0` 開放 22 port，見 [網路](/infra/cloud-providers/vm-options/networking/) 的〈預設防火牆規則對外開放了 22 port〉。

## SSH keys

這次選 No SSH keys：主機裡不放任何長期有效的公鑰，登入改用 Bastion 的 managed SSH session 臨時放進去的那一把。Oracle Cloud 對這個選項的說明是選了之後就不能再提供公鑰，所以這條路要求〈Management：Oracle Cloud Agent 與其他進階選項〉那一節的 Bastion plugin 一定打開。第一次建主機、還沒走通 Bastion 時，放自己的公鑰比較保險，理由見 [登入](/infra/cloud-providers/vm-options/login/)。

## Storage

開機磁碟維持映像檔的預設大小、效能等級 Balanced、Use in-transit encryption 為 Enabled、不指定自己的加密金鑰，不另外建立區塊磁碟。預設大小在 Always Free 的 200 GB 額度內。要記住的是刪除這台主機時，終止對話框裡的「Permanently delete the attached boot volume」預設不勾，不勾的話開機磁碟會留下來，見 [磁碟](/infra/cloud-providers/vm-options/storage/)。

## Management：Oracle Cloud Agent 與其他進階選項

建立頁的摘要上，Oracle Cloud Agent 的預設是 Custom Logs Monitoring、Compute Instance Run Command、Compute Instance Monitoring、Cloud Guard Workload Protection 四項開啟，Bastion 與其餘 plugin 關閉。官方的 plugin 說明寫著 Custom Logs Monitoring 不支援 A1 機型，而建立頁上它在 A1 主機的預設值仍是開啟。

這次要改的只有一項：**把 Bastion 打開**。沒有放 SSH 金鑰的主機只能經由 Bastion 的 managed SSH session 登入，而這個 plugin 預設關閉。漏開時不必重建，主機建好之後可以在主機頁面的 Oracle Cloud Agent 分頁打開，官方說明最多 10 分鐘生效。

其餘維持預設：Authorization header 為 Enabled（中繼資料服務只接受第二版的請求）、Live migration 讓 Oracle 選擇、Restart after infrastructure maintenance 為 Enabled、不放初始化腳本、不加標籤。各項的意義見 [代理程式、中繼資料服務與維護行為](/infra/cloud-providers/vm-options/management/)。

## 等效的 CLI 指令

同一組設定用 OCI CLI 建立（登入方式見 [從本機用 OCI CLI 操作 Oracle Cloud](/infra/cloud-providers/oracle-cloud/cli-session-login/)）：

```bash
oci compute instance launch \
  --compartment-id <compartment 的 OCID> \
  --availability-domain <AD 名稱，例如 XXXX:AP-BATAM-1-AD-1> \
  --display-name verify-a1 \
  --shape VM.Standard.A1.Flex --shape-config '{"ocpus":1,"memoryInGBs":6}' \
  --image-id <Ubuntu 24.04 aarch64 映像檔的 OCID> \
  --subnet-id <private subnet 的 OCID> \
  --assign-public-ip false \
  --agent-config '{"pluginsConfig":[{"name":"Bastion","desiredState":"ENABLED"}]}' \
  --auth security_token
```

- `--availability-domain`：AD 的完整名稱帶有 tenancy 專屬的前綴，用 `oci iam availability-domain list` 查，不能只寫 `AD-1`。
- `--image-id`：映像檔的 OCID 每個區域不同、每次更新都會換，用 `oci compute image list --compartment-id <tenancy 的 OCID> --operating-system "Canonical Ubuntu" --shape VM.Standard.A1.Flex` 查最新的那一個；加了 `--shape` 回傳的就只有 aarch64 的映像檔。
- `--agent-config`：只列出要改的 plugin，其餘維持預設。這裡把 Bastion 設成 `ENABLED`。
- 沒有給 `--ssh-authorized-keys-file`，等同主控台的 No SSH keys。

主控台與 CLI 的差別在錯誤訊息的可讀性：主控台會把不相容或這一區沒有的機型直接標成不可選，CLI 送出不存在的機型只回 `404 NotAuthorizedOrNotFound`，這個錯誤碼同時涵蓋權限不足與資源不存在。

## 按下 Create 之後的結果：容量不足

主控台回的訊息是：

```text
Out of capacity for shape VM.Standard.A1.Flex in availability domain AD-1. Create the instance in a different availability domain or try again later.
```

意思是這個 AD 裡跑 A1 的實體主機當下沒有空出來的資源，跟填的設定無關；同一段時間用 CLI 送出的請求回的是 `InternalError: Out of host capacity.`，偶爾是 `429 TooManyRequests`。訊息建議的兩條路在這一區都用不上：這一區只有一個 AD 可以換，fault domain 也已經是讓 Oracle 選。剩下的做法是隔一段時間再試，有人釋出資源時才會短暫空出位置。這次改用 CLI 每 5 分鐘重送一次同一組設定；重試結果與後續的 Bastion 登入測試記在本模組的 Backlog，完成後補進這一篇。

## 延伸閱讀：建立頁的概念與帳號層的限制

- [建立雲端虛擬機的選項](/infra/cloud-providers/vm-options/)：各分頁的欄位背後的概念，vendor 中立、附三家的欄位名稱對照
- [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)：為什麼這台主機只能建在 `ap-batam-1`、這一區缺哪些機型
