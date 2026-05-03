---
title: "8.2 事故指揮與角色分工"
date: 2026-04-23
description: "定義 incident commander 與跨角色協作責任"
weight: 2
---

## 概念定位

事故指揮與角色分工是把臨場混亂轉成可運作結構的核心節點。[incident command system](/backend/knowledge-cards/incident-command-system/) 定義路由決策，scribe 負責記錄時間線，liaison 負責對接外部或跨團隊資訊，owner 負責修復，這些角色的責任要先被切清楚，事故才能收斂。

這個節點先處理角色，再處理協作。只要角色重疊，事故就會在「誰決定、誰回報、誰修復」上卡住；只要角色缺失，事故就會在同步與交接時失真。這一章要建立的是協作路由，而不是英雄式處理。

## 大綱

- [incident command system](/backend/knowledge-cards/incident-command-system/)
- role ownership
- decision boundary
- [handover protocol](/backend/knowledge-cards/handover-protocol/)
- [on-call](/backend/knowledge-cards/on-call/)

## 核心判讀

[incident command system](/backend/knowledge-cards/incident-command-system/) 的責任是把注意力放在最重要的決策上，而不是親自修所有東西。當事故正在擴散時，incident commander 要先知道風險在往哪裡走，再決定是止血、降級還是切換。scribe 的責任不是做筆記而已，而是把決策、時間、責任與下一步整理成後續可回放的時間線。

role ownership 的責任是讓每個人知道自己在事故中的邊界。若 owner 不清楚，修復會被反覆來回拉扯；若 liaison 不清楚，對外資訊會失真；若 decision boundary 不清楚，討論就會卡在協商而不是行動。

## 判讀訊號

- incident commander / scribe / liaison 角色重疊或缺失
- 同一人兼太多角色、決策變 bottleneck
- decision boundary 不清、跨角色協商耗時
- [handover protocol](/backend/knowledge-cards/handover-protocol/) 靠口頭交接、無書面 state
- 工程師被臨時 page 進事故、不知道角色與職責

## 案例對照

Atlassian 是最適合看角色分工的案例，因為它把 14 天事故中的 incident commander 輪值、跨團隊協作與客戶溝通都完整公開。Slack 可以補通訊面，因為事故工具本身的可用性會直接影響對外節奏。GitHub 則能看出 status update 與內部復原如何維持同一條時間線。

Datadog 和 Roblox 也很有用，前者讓我們看到監控供應商自己失明時怎麼協作，後者讓我們看到長尾恢復時角色如何跨班次接力。把這些案例一起看，會發現角色分工不是形式，而是讓事故不會因為協作失序而延長的控制面。

## 角色分工

| 角色                  | 主要責任                   | 常見失誤                   |
| --------------------- | -------------------------- | -------------------------- |
| Incident Commander    | 決策路由、優先序、節奏控制 | 親自修復、過度介入技術細節 |
| Scribe                | 記錄時間線、決策與待辦     | 只記結果不記上下文         |
| Liaison               | 對外 / 對跨團隊溝通        | 沒有同步最新狀態           |
| Owner                 | 實際修復、驗證、回復       | 邊界不清、被多方拉扯       |
| Subject Matter Expert | 提供技術判斷與風險評估     | 直接搶走決策權             |

這張表的重點是分工清楚，不是職稱固定。小團隊可以兼任，但責任不能重疊到失去路由。

## 交接路由

- 08.12 [handover protocol](/backend/knowledge-cards/handover-protocol/)：長事故跨班次協調
- 08.14 multi-incident：meta-[incident command system](/backend/knowledge-cards/incident-command-system/) 角色與 incident command system pool 協調
