---
title: "Google：Postmortem Action Item Closure 治理"
date: 2026-05-07
description: "把 blameless postmortem 從會議文件變成可追蹤的可靠性治理機制：action item 分級、完成條件與回寫節奏。"
weight: 12
---

Postmortem 的核心責任不是解釋事故，而是把事故轉成會被完成的工程改進。Google 的做法重點在 action item closure：每個改進項都要有 owner、完成條件、追蹤節奏與逾期處理規則。

## 問題場景

很多團隊 postmortem 寫得完整，但事故仍反覆發生。根因通常不是分析能力不足，而是 action item 沒有被制度化追蹤。當改進工作和日常 feature 競爭同一批資源時，沒有 closure 機制的 action item 很容易被延後到失效。

## 治理機制

可靠的 closure 機制要先把 action item 分級，再對應不同完成標準。

| 分級 | 風險型態             | 最低完成標準                      |
| ---- | -------------------- | --------------------------------- |
| P0   | 重複事故高機率再發生 | 需在下個 release 週期前完成並驗證 |
| P1   | 會放大事故影響面     | 要有落地日期與 gate 條件          |
| P2   | 提升診斷或操作效率   | 可排入 backlog，但要保留追蹤節點  |

分級之後要做三件事：

1. 為每個 action item 指派單一 owner。
2. 寫出可驗證完成條件（不是「優化」「強化」這類抽象字）。
3. 把 closure 狀態納入固定 review cadence。

## 可觀測訊號

| 訊號                           | 判讀重點                       | 對應章節                                                       |
| ------------------------------ | ------------------------------ | -------------------------------------------------------------- |
| overdue action-item ratio      | 是否長期積壓高風險改進         | [8.5](/backend/08-incident-response/post-incident-review/)     |
| repeated-incident similarity   | 同型事故是否仍反覆發生         | [8.13](/backend/08-incident-response/repeated-incident-toil/)  |
| gate bypass count              | 是否在高風險情況下跳過治理閘門 | [6.8](/backend/06-reliability/release-gate/)                   |
| verification evidence coverage | 完成項是否附驗證證據           | [6.23](/backend/06-reliability/verification-evidence-handoff/) |

## 常見陷阱

最常見陷阱是把 action item 當作「會後待辦」而不是 release policy 的一部分。這會讓高風險改進沒有實際約束力。正確做法是把 P0/P1 項目直接綁到 release gate，未完成時不得放行關聯變更。

## 下一步路由

先在 [8.19 Incident Decision Log](/backend/08-incident-response/incident-decision-log/) 保留 action item 的決策脈絡，再到 [8.22 Incident Evidence Write-back](/backend/08-incident-response/incident-evidence-write-back/) 回寫觀測與驗證項目。若要把 closure 變成制度，回到 [6.21 Reliability Debt Backlog](/backend/06-reliability/reliability-debt-backlog/) 進行排序治理。

## 引用源

- [Google SRE Book](https://sre.google/sre-book/table-of-contents/)
- [Google SRE Workbook](https://sre.google/workbook/table-of-contents/)
