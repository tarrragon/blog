---
title: "AMI"
date: 2026-06-26
description: "EC2 instance 的作業系統映像快照，包含 OS、軟體、設定與磁碟內容，從 AMI 開出的 instance 跟原始狀態一樣"
weight: 41
tags: ["infra", "knowledge-cards"]
---

AMI（Amazon Machine Image）是 [EC2](/infra/knowledge-cards/ec2/) instance 的完整映像快照。它包含作業系統、已安裝的軟體、設定檔、磁碟內容——從一個 AMI 啟動新的 instance，得到的是跟拍照時完全一樣的環境。

## 概念位置

AMI 在 infra 系列裡有兩個角色。第一個是接手維運時的保險——對 VM（即 [EC2](/infra/knowledge-cards/ec2/) instance）建一個 AMI 等於把整台機器拍下來，做任何改動前都有一個可回退的基線。第二個是環境標準化——把裝好軟體的 instance 做成 AMI（golden image），之後開新機器都從這個 AMI 啟動，確保每台機器的基線一致。

## 可觀察訊號

需要理解 AMI 的情境包括：接手一台不確定裡面裝了什麼的 EC2（先拍 AMI 再動）、要在另一個 region 或帳號複製一台同樣的機器、OS 升級時要保留舊環境作為 rollback、或設計 auto-scaling 的 launch template（需要指定 AMI）。

## 設計責任

| 操作                 | 用途                     | 注意事項                                         |
| -------------------- | ------------------------ | ------------------------------------------------ |
| 建立 AMI             | 對現有 instance 拍照     | `--no-reboot` 避免服務中斷，但檔案系統一致性略低 |
| 從 AMI 啟動 instance | 複製環境                 | 新 instance 有新的 IP、hostname、instance ID     |
| 跨 region 複製 AMI   | 災難復原或多 region 部署 | 複製是非同步的、完成後才能在目標 region 使用     |
| 共享 AMI             | 跨帳號使用同一個映像     | 需要設定 AMI 的 launch permission                |

AMI 包含 EBS snapshot——AMI 的儲存成本就是底層 EBS snapshot 的成本（按儲存量計費）。不再使用的 AMI 要記得 deregister 並刪除對應的 snapshot，否則持續計費。

跟 container image 的差別：AMI 是整台 VM 的映像（含 OS、kernel、系統套件），container image 只包含應用程式和它的依賴（共用 host OS 的 kernel）。AMI 以 GB 計（通常 8-50 GB），container image 以 MB 計（通常 50-500 MB）。

## 鄰卡

- [EC2](/infra/knowledge-cards/ec2/)
- [EBS](/infra/knowledge-cards/ebs/)
