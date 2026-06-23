---
title: "8.3 止血、降級與回復策略"
date: 2026-04-23
description: "把短期止血與正式回復拆成可執行步驟"
weight: 3
tags: ["backend", "incident-response"]
---

止血、降級與回復策略的核心責任是讓事故處理有明確節奏：先停止擴散，再維持最小可用，最後回到可驗證穩態。

## 概念定位

止血、降級與回復是事故處理中不同時間尺度的三種策略。止血的責任是先把擴散停住，降級的責任是讓服務在功能變少的情況下仍能活著，回復的責任則是把系統帶回正常狀態。三者如果混在一起，現場就會失去優先序。

這個節點先處理 containment，再處理完整回復。先問現在應不應該砍功能、切流量、停寫入、關入口，然後再問何時恢復、恢復後怎麼驗證。這樣讀，才會知道事故處理不是一下子把所有東西修好，而是先讓局勢可控。

## 大綱

- containment priority
- [degradation](/backend/knowledge-cards/degradation/) path
- rollback checkpoints
- recovery validation

## 判讀訊號

- 止血優先級跟回復優先級衝突、現場臨時做選擇
- rollback checkpoint 沒測、按下去才知道掛了
- degradation 路徑沒設計、事故時臨時砍功能
- recovery 完成判讀無客觀標準、靠 [incident command system](/backend/knowledge-cards/incident-command-system/) 主觀宣告
- containment 後驗證關閉缺步驟、同事故反覆再起

## 核心判讀

止血的責任是把擴散先停住。當事故正在擴大時，最重要的不是恢復所有功能，而是先讓影響面停止擴張。這可能意味著切流量、停寫入、暫時關閉某些入口，或把高風險功能降級。止血做得越早，後面的回復成本通常越低。

降級的責任是讓服務保持最小可用狀態。不是所有事故都能立即回復，有些事故需要先讓部分功能退場，再用 degraded mode 撐住核心路徑。回復的責任則是把系統帶回完整狀態，並在回來之後做驗證，確認事故沒有再起。

判讀止血策略時，先看擴散速度，再看回復可行性。當 error rate、impact scope 或依賴失效還在擴大，優先目標是停止擴散；當擴散停止且穩態訊號開始回線，才進入回復節奏。

| 階段        | 決策問題                 | 最小門檻                                                                      | 常見動作                            |
| ----------- | ------------------------ | ----------------------------------------------------------------------------- | ----------------------------------- |
| Containment | 影響面還在擴大嗎         | error rate 不再上升、impact scope 不再擴張                                    | 限流、停寫入、隔離 tenant、停入口   |
| Degradation | 能否保住核心旅程         | 核心成功率維持門檻、次要功能可暫停                                            | read-only、fallback、load shedding  |
| Recovery    | 是否可逐步回到完整服務   | 依賴穩定、資料一致性可驗證、回復步驟可重播                                    | 分批恢復、回放驗證、解除降級        |
| Validation  | 是否可宣告恢復與關閉事故 | [steady state](/backend/knowledge-cards/steady-state/) 回線、關鍵指標連續達標 | 宣告恢復、進入 post-incident review |

止血決策的重點不是「修好」，而是「先不要更壞」。回復決策的重點不是「盡快全開」，而是「按可驗證順序回線」。

## 案例對照

AWS S3 和 Cloudflare 很適合看止血，因為這兩類事故最容易出現配置推送後的快速擴散，必須先切開傳播路徑。GitHub 與 Azure AD 適合看回復順序，因為 replication 與 identity 問題都會讓回復比止血慢得多。Slack、Discord 與 Datadog 則適合看降級，因為通訊平台和觀測平台在事故中都可能需要先維持部分能力，再逐步恢復完整服務。

Atlassian、Roblox 與 Heroku 也能提供不同視角。Atlassian 告訴我們多租戶誤刪後，降級與恢復要和客戶通訊一起走；Roblox 告訴我們 prolonged recovery 需要長尾驗證；Heroku 告訴我們入口路由出問題時，先止血比硬修單一應用更重要。這些案例放在一起，會讓 containment 成為一條具體的操作路線，而不是抽象口號。

## 回復步驟

| 步驟            | 目的                         | 常見驗證                     |
| --------------- | ---------------------------- | ---------------------------- |
| stop the bleed  | 先讓影響面停止擴散           | 流量下降、錯誤率不再上升     |
| degrade safely  | 保住核心功能，放掉非必要功能 | 核心路徑可用、次要功能關閉   |
| recover service | 把服務帶回正常               | 功能恢復、依賴穩定、指標回穩 |
| validate again  | 確認事故沒有反覆             | 重放失敗情境、觀察是否再起   |

這些步驟的價值在於順序。事故處理常見的錯誤，是把 recover service 當成第一步，結果在局勢還沒穩定前就把風險重新打開。

## 案例回扣

Cloudflare 2019 的教訓是規則推送錯誤會在秒級擴散，containment 必須先切傳播路徑，再處理規則內容。AWS S3 2017 的教訓是共享子系統恢復有順序，對外通訊要清楚分開「哪些操作已恢復、哪些仍在回復中」。

這兩個案例都指向同一件事：回復順序與驗證門檻必須早於「全面恢復」承諾，否則會產生二次失信與反覆事故。

## 常見反模式

| 反模式             | 表面現象                       | 修正方向                            |
| ------------------ | ------------------------------ | ----------------------------------- |
| 止血與回復同時全開 | 還在擴散就開始大規模回復       | 先完成 containment，再進 recovery   |
| 回復無分批         | 一次全開導致次生異常           | 用 staged recovery + checkpoint     |
| 宣告恢復靠主觀感覺 | 指標短暫回穩就關閉事故         | 以 6.22 steady state 的連續門檻判斷 |
| 通訊與狀態不同步   | 對外說已恢復，內部仍在手動修復 | 對外更新必須引用 8.19 decision log  |
| 只修功能不修流程   | 下次遇到同型事故仍無路由       | 回寫 8.22 evidence write-back       |

## 交接路由

- [6.7 DR 演練與 Rollback Rehearsal](/backend/06-reliability/dr-rollback-rehearsal/)：演練結果作為事中決策素材
- 08.15 vendor 事故：依賴方掛掉時的止血手段
- [6.17 Feature Flag Governance](/backend/06-reliability/feature-flag-governance/)：ops flag（kill switch）作為事中止血手段
- 08.17 security vs operational：止血策略差異
- [6.20 Experiment Safety Boundary](/backend/06-reliability/experiment-safety-boundary/)：把止血邊界轉成演練門檻
- [6.22 Steady State Definition](/backend/06-reliability/steady-state-definition/)：用同一門檻判斷恢復完成
- 08.19 incident decision log：記錄每一步的條件與回退門檻
