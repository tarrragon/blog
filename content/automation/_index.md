---
title: "免伺服器自動化實務指南：用免費雲端服務給靜態站補上動態能力"
date: 2026-07-06
description: "不租主機、用免費雲端服務給靜態站或個人專案補上收資料、存資料、排程彙總能力時的實作與選型"
tags: ["automation", "serverless", "apps-script", "google-sheets", "static-site", "beacon", "no-server"]
weight: 40
---

本指南處理一類具體的工程問題：手上有一個沒有後端的靜態站或小專案，需要一點點動態能力（收一筆表單、記一次瀏覽、每天彙總一次資料），但這個需求撐不起、也不值得租一台伺服器。核心概念是「膠水層」——用別人已經在跑、且對個人用量免費的雲端服務，補上靜態站缺的那一小塊伺服器端邏輯，讓你不必自己維護一台開機的主機。

靜態站的能力邊界很明確：瀏覽器把 HTML/JS 抓下來後，所有邏輯都在使用者的瀏覽器裡跑，沒有任何一段程式碼在你控制的伺服器上執行。這代表任何「要記在你這邊」的資料——誰來看過、表單填了什麼、累積計數——都需要一個瀏覽器以外、由你掌握的接收端。這個接收端不必是傳統伺服器；它可以是一段掛在免費平台上、只在被呼叫時才執行的函式。本指南教怎麼用這種函式把靜態站的能力補齊。

貫穿全指南的案例是「幫這個架在 GitHub Pages 上的 blog 做流量統計」。GitHub Pages 不給 access log、也不能跑伺服器端程式碼，所以流量資料只能靠瀏覽器主動回報。這個案例會從模組零的架構推導、一路實作到模組五的上線與配額管理，讀者跟著做完會得到一個真的能用、資料完全在自己手上的流量統計系統。

第一種膠水工具選 Google Apps Script + Google Sheets：它對個人 Google 帳號免費、不需要信用卡、Sheets 直接當資料庫兼儀表板，起步門檻是所有選項裡最低的。指南後續會加入其他膠水工具（例如 Cloudflare Workers）作為對照，說明各自的適用邊界——Apps Script 適合資料量小、需要人可直接讀寫試算表的場景；當量體變大或需要低延遲時，模組五會給出換工具的判準與遷移路徑。

## 教材邊界

| 類型     | 放在本指南                                                             | 不放在本指南                                                 |
| -------- | ---------------------------------------------------------------------- | ------------------------------------------------------------ |
| 心智模型 | 靜態站能力邊界、膠水層架構、client beacon、免費額度的思考方式          | 大型後端架構、微服務拆分                                     |
| 工具地基 | Apps Script web app 部署模型（`doGet`/`doPost`）、授權模型、V8 runtime | Apps Script 在 Workspace 企業版的進階整合                    |
| 實作     | beacon 前端、接收端 handler、Sheets 讀寫、觸發器排程、配額與安全       | 商業級 analytics 平台的自建（見 [Monitoring](/monitoring/)） |
| 選型     | Apps Script vs Workers 的適用邊界、何時該換工具                        | 雲端主機比價、Kubernetes                                     |

流量分析的**概念層**（事件分類、漏斗、cohort、歸因）不在本指南，在 [Monitoring 監控體系](/monitoring/)。本指南是**動手做**的那一半：怎麼用免費工具把資料真的收進來、存起來、彙總出報表。兩者互補——先看 Monitoring 想清楚要收什麼，再回本指南把管線搭起來。

## 章節

| 章節                                                              | 責任                                                                           |
| ----------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| [模組零：心智模型](/automation/00-mental-model/)                  | 靜態站能力邊界、膠水層、client beacon 架構、免費額度、GAS vs Workers 選型      |
| [模組一：Apps Script 地基](/automation/01-apps-script-basics/)    | Apps Script 是什麼、V8 runtime、web app 部署模型、授權模型、跟一般伺服器的差異 |
| [模組二：流量 beacon 實作](/automation/02-analytics-beacon/)      | 前端 beacon、接收端 handler、寫進 Sheet、CORS 的雷與解法，從零到第一筆         |
| [模組三：Sheets 當資料庫](/automation/03-sheet-as-database/)      | `appendRow`、資料模型、並發與 `LockService`、Sheets 的容量邊界                 |
| [模組四：觸發器與排程](/automation/04-triggers-automation/)       | time-driven trigger 每日彙總、`onFormSubmit`、把原始 log 變成日報              |
| [模組五：部署、配額與安全](/automation/05-deploy-quota-security/) | 部署權限、免費配額上限、CORS 設定、防濫用、隱私與 PII 邊界                     |

## 讀者旅程

想直接把流量統計做出來：模組零建立架構直覺後，跳模組二照著實作，缺概念再回模組一補。想完整理解這套膠水模式、之後套用到其他專案：模組零到五順讀。只想查某個 Apps Script 術語：看 [knowledge-cards](/automation/knowledge-cards/)。

---
