---
title: "Google"
date: 2026-05-01
description: "Google SRE 實踐原典：SLI / SLO / Error Budget / Postmortem 文化"
weight: 1
---

Google 是 SRE 概念的原始來源、SRE Book 與 Workbook 是領域 canonical text。教學重點不在單一事故、而在 SRE 工程文化、量化方法與組織節奏。

## 規劃重點

- SLI / SLO / Error Budget：可靠性目標的量化方法、為何選 SLO 而非 100%
- Postmortem 文化：blameless / action items / 行動追蹤的閉環設計
- Toil 量化：把運維工作變成可預算的工程資產
- [on-call](/backend/knowledge-cards/on-call/) 與 burnout：值班輪值、shadow / primary 結構、心理安全
- [readiness](/backend/knowledge-cards/readiness/) review：服務上線前的 SRE 接管門檻

## 預計收錄實踐

| 議題                      | 教學重點                                                   |
| ------------------------- | ---------------------------------------------------------- |
| SRE Book Ch.1-4           | 概念基礎、為何 SLO、為何 50/50                             |
| Postmortem Culture        | blameless 操作化、action items 追蹤                        |
| Toil & Engineering Time   | 量化 toil、長期投資工程的政策                              |
| Hierarchy of Reliability  | Monitoring → IR → PIR → Testing → Capacity → Dev → Product |
| Embedded SRE / Consulting | SRE 介入服務的多種模式                                     |

## 案例定位

Google 這個案例在講的是可靠性如何變成一套可操作的工程制度，而不是單一工具或單一事故。讀者先抓到 SLI / SLO、error budget、postmortem 與 toil 這幾個原語各自負責什麼，再把它們組成一條可執行的可靠性路徑。

## 判讀重點

當服務健康開始波動時，先看 SLO 是否真的被消耗，再看監控與告警是否能對應到使用者體感。當 [on-call](/backend/knowledge-cards/on-call/) 壓力升高時，重點也不在個人技巧，而在團隊是否把重複性工作轉成可預算的工程投資。

## 可操作判準

- 能否用一句話說明每個 SLI 對應的使用者行為
- 能否從 postmortem 找到明確 owner 與完成條件
- 能否把 toil 量化成可排程的工程時間
- 能否把監控、測試、容量、開發與產品決策串成同一條路由

## 與其他案例的關係

Google 提供的是可靠性的語言層，其他案例提供的是具體場景層。當讀者先懂 SLI / SLO 與 postmortem 這組原語，再看 Honeycomb 的 burn rate、Atlassian 的復原節奏或 GitHub 的 status communication，就能把抽象制度接到實際事故上。

## 代表樣本

- SLO 與 error budget 讓團隊把可靠性變成可量化的工程目標。
- postmortem 將事故轉成可追蹤的 action items，而不是只留下檢討文字。
- toil budget 讓重複性工作變成可預算的工程投資。
- [readiness](/backend/knowledge-cards/readiness/) review 讓服務在上線前先過可靠性門檻。
- [on-call](/backend/knowledge-cards/on-call/) 與 burnout 讓值班不是個人耐力測試，而是組織設計問題。
- hierarchy of reliability 讓 monitoring、testing、capacity、dev、product 串成一條路由。
- blameless culture 讓檢討聚焦在系統與流程，而不是個人責任。
- embedded SRE / consulting 讓可靠性能力可以以不同介入深度落到服務團隊。

## 引用源

- [sre.google](https://sre.google/)：Google SRE 官方資源入口，收錄 books 與主題更新。
- [The SRE book turns 6!](https://cloud.google.com/blog/products/devops-sre/the-sre-book-turns-6)：整理 SRE Book / Workbook 與延伸資源的官方入口。
- [Adopting SRE: Standardizing your SLO design process](https://cloud.google.com/blog/products/devops-sre/how-to-design-good-slos-according-to-google-sres)：補 SLO 設計方法與實務語境。
