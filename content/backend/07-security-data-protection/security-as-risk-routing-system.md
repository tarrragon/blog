---
title: "7.15 資安作為風險路由系統"
tags: ["資安治理", "Risk Routing", "Security Design"]
date: 2026-04-30
description: "建立資安作為風險路由系統的導讀大綱，串接問題節點、控制面與跨模組交接"
weight: 85
---

本篇的責任是把資安整理成工程路由語言。讀者讀完後，應該能把一個資安疑慮判斷成身份、入口、資料、憑證、供應鏈、偵測或例外治理問題，再交接到對應模組。

## 核心論點

資安路由系統的核心概念是「先判斷風險落點，再選擇控制面」。Checklist 可以提醒團隊涵蓋基本項目，路由系統會回答哪個風險先處理、誰承接、如何驗證、何時重評估。

## 讀者入口

本篇適合放在 [模組七：資安與資料保護](/backend/07-security-data-protection/) 之後閱讀。它不展開單一控制技術，而是把 [7.8 模組路由](/backend/07-security-data-protection/security-routing-from-case-to-service/) 的表格寫成一篇可讀的導論。

## 為什麼要用路由語言

路由語言的責任是把「擔心出事」轉成「哪個控制面承接」。當問題能被放進正確控制面，團隊就能同時做到三件事：

1. 決定處理順序：先收斂高爆炸半徑風險，再處理低影響項目。
2. 決定承接角色：平台、服務、資安、SRE、incident owner 的邊界清楚。
3. 決定驗證方式：每個控制面都有可觀測訊號與關閉條件。

Checklist 擅長提醒「有哪些基本項目」，路由語言擅長回答「這次先做哪件事、做到什麼程度算收斂」。

## 風險路由的四步驟

資安路由系統的核心流程是四步驟：

1. 定義問題：把事件寫成一個可判讀的服務問題。
2. 判讀落點：判斷主要風險落在身分、入口、資料、供應鏈或偵測治理。
3. 指派控制面：把問題交接到對應章節與模組負責面。
4. 回寫閉環：把結果回寫到主章判讀訊號與 incident workflow。

### 步驟一：定義問題

問題定義的責任是建立可交接的最小語句。建議格式：

```text
事件：發生了什麼
影響：最壞後果與影響範圍
條件：攻擊或誤用成立的前提
```

### 步驟二：判讀落點

判讀落點的責任是找「主控制面」，不是一次把所有控制面都開工。

| 判讀問題                                                                                     | 主落點章節                                                                                                           |
| -------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| 這是誰可以做什麼的問題嗎                                                                     | [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)                                 |
| 這是對外暴露與入口治理問題嗎                                                                 | [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)                   |
| 這是資料暴露、匯出或證據鏈問題嗎                                                             | [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)               |
| 這是 [artifact provenance](/backend/knowledge-cards/artifact-provenance/) 信任與交付鏈問題嗎 | [7.12 供應鏈完整性與 Artifact 信任](/backend/07-security-data-protection/supply-chain-integrity-and-artifact-trust/) |
| 這是偵測不到、訊號品質不足、重評估機制缺口問題嗎                                             | [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)          |

### 步驟三：指派控制面

控制面指派的責任是給出可執行任務，不只給概念名稱。每次交接至少帶四項資訊：

1. 判讀訊號：你如何判定這是該控制面的問題。
2. 風險邊界：目前先處理到哪個範圍。
3. 驗證條件：什麼訊號代表控制面開始生效。
4. 下一步路由：收斂後要交給哪個模組接手。

### 步驟四：回寫閉環

回寫的責任是讓同類問題下次更早被判讀。回寫位置至少包含：

1. 主章判讀訊號（7.x 章節）
2. red-team 問題卡片
3. incident workflow 檢查點

## 三個路由案例

### 案例一：身份擴散

核心判讀是「權限邊界比功能邊界更寬」。

1. 主落點：7.2 身分與授權邊界
2. 補落點：7.13 偵測覆蓋率（補異常行為偵測）
3. 下一步：`08 incident-response` 新增權限回收與 token 失效化流程

### 案例二：資料外送

核心判讀是「資料路徑先於資料格式」。

1. 主落點：7.4 資料保護與遮罩治理
2. 補落點：7.11 資料駐留、刪除與證據鏈
3. 下一步：`06 reliability` 補資料匯出審核、回滾與證據保存流程

### 案例三：供應鏈 artifact 信任

核心判讀是「交付鏈的身分與完整性不可分離」。

1. 主落點：7.12 供應鏈完整性與 Artifact 信任
2. 補落點：7.14 例外治理與 [Tripwire](/backend/knowledge-cards/tripwire/)
3. 下一步：`05 deployment-platform` 補簽章驗證、凍結策略、版本恢復演練

## 判讀訊號與風險邊界

| 訊號                                                                                                                                     | 代表風險                         | 建議路由                       |
| ---------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------- | ------------------------------ |
| 權限模型文件與實際 API 行為不一致                                                                                                        | 身分邊界漂移                     | 7.2 → 7.13                     |
| 對外匯出流程沒有分級與審核                                                                                                               | 資料外送與合規風險擴散           | 7.4 → 7.11                     |
| 發佈前缺少 [artifact provenance](/backend/knowledge-cards/artifact-provenance/) 來源與完整性檢查                                         | 供應鏈注入風險                   | 7.12 → 7.14                    |
| [Security exception](/backend/knowledge-cards/security-exception/) 決策沒有到期日與重評估 [Tripwire](/backend/knowledge-cards/tripwire/) | 風險接受狀態永久化               | 7.14 → 8 incident workflow     |
| 事故復盤只有時間線，沒有控制面失效語言                                                                                                   | 同類缺口無法回寫，問題會重複出現 | 7.16 case-to-workflow 回寫流程 |

## 邊界與常見誤判

路由語言的邊界是決策層，不直接替代每個模組的實作章節。常見誤判如下：

1. 把路由結果當最終解法：正確做法是路由後交接到 05/06/08 模組落實。
2. 一次啟動所有控制面：正確做法是先主落點，再按風險擴散補落點。
3. 只關注事故故事：正確做法是把故事轉成控制面失效語言並回寫。

## 必連章節

- [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)
- [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/)
- [7.4 資料保護與遮罩治理](/backend/07-security-data-protection/data-protection-and-masking-governance/)
- [7.8 模組路由：問題到服務實作](/backend/07-security-data-protection/security-routing-from-case-to-service/)
- [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)

## 完稿判準

完稿時要讓讀者能拿一個功能需求做路由判斷。文章需要至少示範三種問題：身份擴散、資料外送、供應鏈 [artifact provenance](/backend/knowledge-cards/artifact-provenance/) 信任，並把每種問題導向不同的下一步章節。
