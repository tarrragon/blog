---
title: "Vendor 深度技術文章方法論的演化紀錄：開場輪替的驗證、審查方式、實作文章的分工、同一個工具在兩個模組各有一頁與選題的候選來源"
slug: "vendor-deep-article-methodology"
date: 2026-05-18
description: "要寫 vendor 的深度文章、想知道現行的選題來源、6 段結構、審查方式與分頁規則是從哪幾次寫作演化出來、各自依據什麼時讀"
tags: ["writing-methodology", "vendor-article", "technical-writing", "case-first", "retrospective"]
---

vendor overview 寫完之後，往下寫單一功能的深度文章（deep article）時，選題與結構要用另一套方法論。操作步驟維護在 `.claude/skills/vendor-deep-article/`，這篇記錄那套方法論怎麼一路改到現在的樣子：兩批 deep article 驗證了 6 段結構與開場輪替，也就是寫前替每篇預先指定不同的開場寫法，用來防止批量寫作時開場句型同質化；審查方式從單一 reviewer 改成多輪審查；讀者照著做的操作從 deep article 分出去，寫成實作文章；同一個工具在兩個模組各有一頁時，兩頁怎麼分工；選題的候選來源在 overview 的結構改變之後怎麼重寫。最後一節把每一次修改對到 skill 的版號與觸發它的那一次寫作。每一條規則現在怎麼寫，以 skill 為準，這篇只記它們從哪裡來。

## 背景：deep article 跟 overview 是兩種文章

本 blog 的 backend 教學模組替每個 vendor 寫了一篇 overview，讀者在那一頁判斷該不該選這個 vendor、它跟同類差在哪；deep article 往下寫單一功能怎麼設定、會在哪裡出錯、容量怎麼規劃。兩者的讀者在做不同的決定，所以 overview 的章節套不到 deep article 上，第一篇 deep article 照 overview 的章節寫時就發現不合用。同一批工作也寫了 migration playbook，三種文章的差異見 [migration playbook 方法論演化紀錄](/posts/migration-playbook-methodology/)。

方法論剛建立時，deep article 的題目取自 overview 頁尾一段叫「預計實作話題」的清單。後來 overview 的結構改了，這一段已經不在任何一頁上，選題來源在 2026-10-28 重寫，見〈選題的候選來源〉。

## 跨 vendor 的那一批：五種開場與 6 段結構

這一批 5 篇分屬不同 vendor，用來驗證 6 段結構（問題情境 → 概念 → 配置 → 演練 → 容量 → 整合）能不能套在不同主題上：

| 篇                                                                                                           | Variant  | 開場寫法                                          | 行數 |
| ------------------------------------------------------------------------------------------------------------ | -------- | ------------------------------------------------- | ---- |
| [pgBouncer 配置](/backend/01-database/vendors/postgresql/pgbouncer-config/)                                  | A 標準   | 標準「問題情境」                                  | 263  |
| [Vault dynamic credential](/backend/07-security-data-protection/vendors/hashicorp-vault/dynamic-credential/) | A 標準   | 標準「問題情境」                                  | 222  |
| [K8s graceful shutdown](/backend/05-deployment-platform/vendors/kubernetes/graceful-shutdown/)               | B 痛點   | 痛點宣告「沒做對、每次 deploy 都吃 502」          | 213  |
| [Splunk RBA](/backend/07-security-data-protection/vendors/splunk/risk-based-alerting/)                       | C 反向   | 概念反向定義「alert fatigue 是 detection 天花板」 | 193  |
| [Cloudflare Page Shield](/backend/07-security-data-protection/vendors/cloudflare-waf/page-shield-csp-sri/)   | D 對照表 | 對照表驅動「Attack pattern x Defense mechanism」  | 214  |

6 段的內容在 5 篇都成立，開場那一節的寫法卻因主題不同而自然分化成四種，都讀得通。所以 6 段結構從那時起是內容的指引，不是章節標題的模板：開場那一節不必死守「問題情境」這個標題。

開場句型同質化（cadence collapse）是這一批要驗的另一件事。在這批之前，backend/07 的 51 篇 vendor overview 是在沒有預先分配開場的情況下批量寫成的，51 篇全部用同一族「任一缺失」的開場句型。這一批的後 4 篇在寫之前先分配了四種開場：

| 維度                   | backend/07 的 51 篇 vendor overview | deep article 後 4 篇 |
| ---------------------- | ----------------------------------- | -------------------- |
| 「任一缺失」族句型重複 | 51/51 (100%)                        | 0/4 (0%)             |
| 開場寫法的種類         | 1 種                                | 4 種                 |

## 同一個 vendor 的 sub-tool 系列：同質化風險最高的情境

PostgreSQL 系列的 5 篇刻意選同質化風險最高的組合：同一個 vendor（PostgreSQL）、同一種文章、同一批讀者、同一個 6 段結構。

| 篇                                                                                                      | Variant              | 開場寫法                                                                            | 行數 |
| ------------------------------------------------------------------------------------------------------- | -------------------- | ----------------------------------------------------------------------------------- | ---- |
| [Patroni HA](/backend/01-database/vendors/postgresql/patroni-ha/)                                       | E lifecycle-driven   | 「Failover lifecycle 5 段不是一條曲線」                                             | 243  |
| [autovacuum tuning](/backend/01-database/vendors/postgresql/autovacuum-tuning/)                         | B pain-driven        | 「你的 autovacuum 永遠追不上 bloat — 為什麼」                                       | 202  |
| [declarative partitioning](/backend/01-database/vendors/postgresql/declarative-partitioning/)           | C concept-reversed   | 「Partition 不是『把大表切小』、是『讓 planner pruning + 縮小 maintenance scope』」 | 244  |
| [logical replication + Debezium](/backend/01-database/vendors/postgresql/logical-replication-debezium/) | D table-driven       | 「Replication slot x Failure x Recovery 對照」                                      | 227  |
| [PITR + WAL archiving](/backend/01-database/vendors/postgresql/pitr-wal-archiving/)                     | A standard 6-section | 「問題情境」                                                                        | 273  |

表中的開場是當時的原文，照錄；其中幾句的寫法（對讀者喊話、否定起手）後來被本站的句子規範列為要改的類型。

兩批對照：

| 維度           | 跨 vendor 的那一批（N=4） | 同 vendor sub-tool 系列（N=5） |
| -------------- | ------------------------- | ------------------------------ |
| 開場寫法的種類 | 4（A / B / C / D）        | 5（A / B / C / D / E）         |
| 句型同質化     | 0/4 (0%)                  | 0/5 (0%)                       |
| 共同的條件     | 6 段結構                  | 6 段結構 + 同 vendor + 同讀者  |

同 vendor 的系列在 N=5 時仍然沒有同質化，也多出 lifecycle-driven 這一種開場；五種開場各自對應主題自然的進入方式，沒有出現硬配的情形。同質化檢查的抽樣位置因此訂在批次進度的 60-80%：進度 10-20% 時只有 1 篇可比，訊號弱，60-80% 時有 4 篇可以互相對照。這幾個比例來自這兩批共 9 篇，樣本小，是當時的經驗值。

## 審查方式：從單一 reviewer 到多輪審查

前兩批的 deep article 都只經過一位 reviewer。理由是 deep article 的焦點窄（單一功能）、跨章重複的風險低、案例引用少（每篇 1 到 2 個對照），一位 reviewer 檢查 config 對不對與敘事順不順就夠；skill 至今仍以「單一 reviewer 即可」作為一般情形的寫法。

本 repo 的審查規則後來把教學模組的新章節列為一定要跑多輪審查（至少三輪）的對象，deep article 住在教學模組裡，所以在本 repo 照多輪審查走。2026-10-27 的 Gatling 兩篇是照多輪審查寫的，跑了四輪，抓到的錯誤裡有三處，一位 reviewer 看 config 與敘事時不容易發現：原頁把 Gatling 的 `atOnceUsers`、`rampUsers` 歸成 closed model，跟官方文件〈Injection〉相反；原頁說開源版可以合併多台施壓端的 report，官方 FAQ 寫的是不支援；審查途中稿件一度改成解析 `simulation.log` 做跨次比較，第四輪的對抗驗證查到官方同樣不支援這種用法。這三處都要拿官方文件逐條核對才找得到，而那是事實核對這一輪的工作，不在「config 對不對、敘事順不順」的範圍裡。

## 跟實作文章的分工

2026-10-25 起，讀者照著做、從前置條件做到完成的操作（local lab、restore drill）不再寫進 deep article，改寫成 vendor 資料夾底下 `hands-on/` 的實作文章；deep article 只留判讀需要的關鍵 config 與故障判讀，再連到那一篇（skill 1.1.0）。分開的理由是兩種文章的讀者在做不同的事：讀 deep article 的人在建立判斷依據，一段完整的操作流程會蓋住論證；照實作文章操作的人要的是不漏步的順序與每一步該看到的輸出。同一次寫的實作文章不套 deep article 的單一 reviewer，照多輪審查跑，因為讀者會照著它在自己的環境操作。

## 同一個工具在兩個模組各有一頁

backend 的 06-reliability 與 09-performance-capacity 各有一份負載測試工具的 vendor 頁，k6、Gatling、JMeter、Locust 在兩邊各有一頁。2026-10-27 寫 Gatling 時發現，兩頁都從工具往外寫（它是什麼、怎麼裝、有哪些功能），拿到的是同一批材料，因為工具的事實不隨模組改變；兩個模組的讀者要做的判斷卻不同。可靠性模組的讀者要決定這一版的效能有沒有退化、能不能過 release gate，工具負責產生 regression 的證據；效能容量模組的讀者要找出受測服務的飽和點，工具負責把負載加到那一點。

處理方式是把兩頁逐段並排，依序問兩件事：這一段是不是操作細節；其餘的段落原封不動放進另一頁還成立嗎。兩頁都成立、而且是一個通用概念的，寫成知識卡（Gatling 這一次抽出 [Open and Closed Workload Model](/backend/knowledge-cards/open-closed-workload-model/) 與 [Load Generator Saturation](/backend/knowledge-cards/load-generator-saturation/) 兩張）；兩頁都成立而拆不成單一概念的工具層深度內容，寫在其中一邊；只在一個模組成立的，留在那個模組往下寫深。兩頁重疊時不合併：照從工具往外寫的現狀合併，留下來的是通用材料，另一個模組的觀點在合併後的那一頁沒有位置。結果是 Gatling 在 06 與 09 各一篇觀點文章：[Gatling 在效能 regression gate 的用法](/backend/06-reliability/vendors/gatling/gatling-performance-regression-gate/)、[Gatling 在容量探測的用法](/backend/09-performance-capacity/vendors/gatling/gatling-capacity-probing/)。推導與判讀寫在 [同一個工具在兩個模組各有一頁](/report/same-tool-page-per-module-derives-from-the-modules-question/)，skill 在 1.2.0 加上這一節。

## 選題的候選來源

方法論建立時，選題的規則寫成「從 overview 頁尾的『預計實作話題』挑」。後來 overview 的結構改了，那一段不在任何一頁上，待寫的題目散在三種位置：大多數 overview 的「進階主題」段；01-database 六個 vendor 頁的「後續擴充（仍待補）」段；模組目錄頁的 Backlog，而 Backlog 的列多半只寫「這幾個 vendor 要補 deep article」、不寫題目。2026-10-28 把選題來源改寫成四種候選議題（skill 1.3.0）：已經排進待寫清單的議題，Backlog 只點名 vendor 時，題目從那個 vendor 的 overview 取；跨 vendor 的議題；overview「進階主題」段點到、而那幾行說不清楚的議題；兩頁並排分段之後歸成本模組觀點的段落，以及歸成工具層深度內容、落點在這一邊的議題。

這次改寫的審查本身示範了改規則的一種錯法。前兩輪的修法在判斷標準一加了一句「候選議題以外的不算」，逐句讀都通順；第三輪拿 repo 裡實際的 Backlog 與 vendor 頁照新規則走一遍，才發現這一句會把兩頁並排之後的本模組觀點段落排除在外，連前一天剛寫好的 Gatling 06 那一篇的選題，照新規則都算違規。同一次走查也發現兩個規則沒有涵蓋的情形：Backlog 指向一張「後續候選」表，表上的 vendor 還沒有 overview，那是要先寫的 overview，不是 deep article 的候選；待寫清單上也有 lab、遷移流程與選型判斷，這三類各自寫成實作文章、migration playbook，或寫回 overview。

## 方法論的演化對照

1.0.0 之前的版本標籤（v0 到 v1.3）是這篇文章當時自己的編號，跟 skill 的版號是兩套；skill 在 2026-06-29 從這篇文章拆出來，從 1.0.0 起算。

| 時間       | 版本          | 修改                                            | 觸發來源                                                                            |
| ---------- | ------------- | ----------------------------------------------- | ----------------------------------------------------------------------------------- |
| 2026-05    | 文章標籤 v0   | 直覺套 overview 的章節                          | 第一篇 deep article 不合用                                                          |
| 2026-05    | 文章標籤 v1   | 6 段結構、200-400 行的篇幅                      | 跨 vendor 的那一批 5 篇                                                             |
| 2026-05    | 文章標籤 v1.1 | 6 段是內容指引，不是章節標題的模板              | 開場那一節的寫法自然分化                                                            |
| 2026-05    | 文章標籤 v1.2 | 寫作時間預估從 2-4 小時降到 1-2 小時            | overview 已經建立 context                                                           |
| 2026-05    | 文章標籤 v1.3 | 同質化檢查的抽樣位置從進度 10-20% 移到 60-80%   | 同 vendor sub-tool 系列 N=5                                                         |
| 2026-06-29 | skill 1.0.0   | 操作步驟搬進 skill，這篇改成演化紀錄            | [一篇文章只承擔一種功能](/report/single-function-per-article-sop-vs-retrospective/) |
| 2026-08-26 | skill 1.0.1   | 「判準」改寫成「判斷標準」                      | 五份探針一致回報工程讀者讀不懂這個詞                                                |
| 2026-10-25 | skill 1.1.0   | 照著做的操作分出去，寫成 `hands-on/` 的實作文章 | 實作文章與概念文章分開放的規則                                                      |
| 2026-10-27 | skill 1.2.0   | 同一個工具在兩個模組各有一頁的分段與分工        | Gatling 在 06 與 09 的兩頁重疊                                                      |
| 2026-10-28 | skill 1.3.0   | 選題的候選來源改寫成四種候選議題                | overview 頁尾的「預計實作話題」段已經不存在                                         |

審查方式從單一 reviewer 改成多輪審查是本 repo 的審查規則管的，skill 的版號沒有對應的一條，所以不在這張表裡，見〈審查方式：從單一 reviewer 到多輪審查〉。

## 相關連結：skill、姊妹方法論與依據的卡

- Vendor Deep Article skill（`.claude/skills/vendor-deep-article/`）：選題、6 段結構、分頁與寫作步驟的現行寫法
- [Migration Playbook 方法論演化紀錄](/posts/migration-playbook-methodology/)：姊妹方法論，處理換 vendor 的流程文章
- [Case-First Agent Team Review Workflow](/posts/case-first-agent-team-review-workflow/)：教學模組級的批次寫作與審查流程
- [一篇文章只承擔一種功能](/report/single-function-per-article-sop-vs-retrospective/)：操作步驟搬進 skill、這篇只留演化紀錄的依據
- [同一個工具在兩個模組各有一頁](/report/same-tool-page-per-module-derives-from-the-modules-question/)：兩頁分段與抽卡的推導
