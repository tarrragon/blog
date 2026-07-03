---
title: "DevOps 分類：內容缺口待辦"
date: 2026-07-03
description: "devops 分類八個模組的內容缺口盤點：哪些模組只有大綱沒有文章、產出的優先序與跨模組依賴，開工寫章節前先看這張清單"
draft: true
tags: ["devops", "backlog", "meta"]
---

這是 `content/devops/` 分類於 2026-07-03 盤點出的內容缺口。`draft: true` 不對外發佈，只做版本控管的待辦清單。

盤點背景：devops 八個模組中，只有模組三（流量管控）與模組七（突發流量）有完整文章；模組五只完成一章；模組一、二、四、六、八的 `_index.md` 只有 20 餘行大綱（「待寫章節」checklist 全部未勾），文章本體從未產出。根層 `_index.md` 的模組表與學習路線對讀者承諾了八個模組的內容——五個模組是入口幻覺，點進去只有大綱。合計約 30 章待寫。

## 產出紀律（每個模組開工前讀）

- 每個模組是跨 5 章的教學模組，走 AGENTS 模組級流程：先寫讀者定位聲明、有 case 庫的先讀 case 抽 findings、寫完跑 multi-round review 至少三輪。
- 每寫完一章，把該模組 `_index.md` 的「待寫章節」checkbox 勾起、大綱行換成文章連結；模組寫完後把「待寫章節」段改成文章表格（比照模組三、七的完成形）。
- 章節檔名與 slug 小寫、leaf 頁 sibling 連結加 `../` 前綴；提交前跑 `./bin/mdtools cards content/` 與 `fmt --fix`。
- 素材優先引用站內已完成的實測內容（linux debug、infra、monitoring、backend），避免 LLM 自生通用 best practice 充數。

## 優先序與依賴

優先序由三個訊號決定：學習路線的位置（根層 `_index.md` 的四條路線都從某個缺口模組起步或經過）、跨模組依賴（誰是誰的前提）、站內素材完備度（有沒有現成實測內容可引）。

| 順位 | 模組        | 理由                                                                            | 依賴 |
| ---- | ----------- | ------------------------------------------------------------------------------- | ---- |
| 完成 | 04 服務探活 | 已於 2026-07-03 完成 5 章（case-first 從 index 轉出）；linux backlog #10 待回收 | 無   |
| 完成 | 01 負載平衡 | 已於 2026-07-03 完成 5 章；nginx 配置實測過（1.30.3）                           | 無   |
| 完成 | 05 容量規劃 | 已於 2026-07-03 補完 5 章（backend/09 case-first）；k6 實測；成本術語已就位     | 無   |
| 完成 | 02 水平擴展 | 已於 2026-07-03 完成 5 章（collector + backend/01 case-first）                  | 無   |
| 完成 | 06 高可用   | 已於 2026-07-03 完成 5 章（backend/06 + infra case-first）                      | 無   |
| 完成 | 08 成本管理 | 已於 2026-07-03 完成 5 章（infra + backend + monitoring case-first）            | 無   |

## 各模組缺口明細

### 1. 模組四：服務探活與自動恢復 — 已完成（2026-07-03）

- **章節**（全數完成）：health check endpoint 設計、liveness vs readiness、systemd watchdog + 自動重啟、process supervisor 選型、graceful shutdown。`_index.md` 待寫章節已轉文章表格。
- **站內素材**：[服務掛了怎麼自動知道](/linux/debug/service-failure-monitoring/)（OnFailure、hung 偵測、canary、heartbeat 的單機實測）、[程序、服務與狀態怎麼判](/linux/debug/process-service-state-diagnosis/)（「進程活著 ≠ 子系統活著」正是 liveness 深度判準的實例）、[monitoring dashboard-devops](/monitoring/04-collector/dashboard-devops/)（下游消費者）。
- **寫完後的連鎖動作**：回 linux backlog 第 10 項——`OnFailure` / drop-in 成為跨模組共用術語，屆時建 `linux/dotfile/knowledge-cards/` 的 systemd drop-in / OnFailure 卡並雙向連結。

### 2. 模組一：負載平衡與反向代理 — 已完成（2026-07-03）

- **章節**（全數完成）：反向代理職責、負載分散演算法、nginx 實務配置（1.30.3 實測）、健康檢查路由設計、LB 是水平擴展前提。`_index.md` 待寫章節已轉文章表格。
- **站內素材**：[infra ALB 上 IaC](/infra/05-core-services/loadbalancer-alb/)（listener / target group / 健康檢查的 IaC 描述）、[infra 網路地基](/infra/03-network-foundation/)（public/private subnet 分層）。
- **注意**：健康檢查路由章跟模組四的 health check endpoint 章是同一概念的兩側（LB 怎麼用 vs 服務怎麼提供），先寫模組四可讓本模組直接引用而非重講。

### 3. 模組五：容量規劃 — 已完成（2026-07-03，6/6）

- **章節**（全數完成）：流量模型建立、峰值估算、壓力測試工具與方法（k6 實測）、規模拐點判斷、成本模型、容器化資源設計。`_index.md` 待寫章節已轉文章表格。
- **站內素材**：[backend 效能容量](/backend/09-performance-capacity/)（case 庫、AGENTS 點名可引）、模組七已完成的四章（規模分級應對表是拐點判斷的鄰居）。
- **注意**：壓測工具章屬 CLI 工具教學，適用驗證導向流程（實機跑過才寫、Docker fixture）；成本模型章是模組八的直接輸入、術語要先對齊（reserved / on-demand / spot）。

### 4. 模組二：水平擴展 — 已完成（2026-07-03）

- **章節**（全數完成）：stateless 設計原則、session 處理、shared storage 選型、擴展觸發與縮回、垂直 vs 水平判斷。`_index.md` 待寫章節已轉文章表格。
- **站內素材**：[monitoring Collector](/monitoring/04-collector/)（stateless 多實例的應用場景）、[backend 資料庫](/backend/01-database/)（shared storage 的 DB 側）。
- **依賴**：模組一先行——「LB 是水平擴展的前提」的引用要有落點。

### 5. 模組六：高可用 — 已完成（2026-07-03）

- **章節**（全數完成）：單點故障盤點、冗餘設計模式、failover 機制、disaster recovery 策略、高可用的成本。`_index.md` 待寫章節已轉文章表格。
- **站內素材**：[infra stateful 資源保護](/infra/05-core-services/stateful-protection-dependency/)（multi-AZ 能力層）、[backend 可靠性](/backend/06-reliability/)。
- **依賴**：模組四先行——failover 的觸發條件是探活，`_index.md` 已明寫這條引用。

### 6. 模組八：成本管理 — 已完成（2026-07-03）

- **章節**（全數完成）：計費模式理解、right-sizing、成本監控與告警、開發環境成本控制、自架 vs 雲端交叉點。`_index.md` 待寫章節已轉文章表格。
- **站內素材**：[infra 治理好習慣](/infra/08-governance-habits/)（tagging 地基）、[monitoring 商業方案](/monitoring/06-commercial-comparison/)。
- **依賴**：模組五的成本模型章先行——學習路線「成本控制」是「模組八 → 模組五」，讀者從八進來時五要接得住。

## 完成判準

- 六個模組的 `_index.md` 都沒有「待寫章節」段、全部換成文章表格。
- 根層 `_index.md` 的模組表與學習路線承諾全部兌現、入口幻覺消除。
- linux backlog 第 10 項（OnFailure / drop-in 卡）隨模組四完成一併回收。
- 每個模組寫完都跑過 `mdtools cards`（0 broken）、`fmt --fix`、emoji 掃描與 multi-round review 三輪。
