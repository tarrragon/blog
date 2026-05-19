---
title: "Sibling Vendor Cross-Link 雙向性 Audit：寫 Vendor Batch 結束必跑"
date: 2026-05-19
description: "當寫 sibling vendor batch（A vs B）、cross-link 容易單向 — A 提 B 多次、B 沒回提 A、形成 navigation asymmetry。Case：MySQL 18 篇對 PG sibling cross-link 9 條、PG 對 MySQL cross-link 0 條。機制：寫第二個 batch 時 reference 第一個 batch 是自然行為、但 reverse direction 必須主動補。修法：vendor batch 結束跑 bidirectional link audit、`A → B` 跟 `B → A` 對比、缺一邊就補。"
weight: 136
tags: ["report", "事後檢討", "工程方法論", "寫作", "vendor", "cross-link"]
---

## 核心：Sibling vendor batch 容易單向 cross-link

當寫 sibling vendor batch（A 跟 B 是同類角色的 vendor）、cross-link 容易單向：

- A 是後寫 batch、提 B 多次（「跟 PG sibling 對比」「PG 的 X 行為跟 MySQL 不同」）
- B 是先寫 batch、預設沒提 A（寫的時候 A 還不存在）
- 結果：A → B 有 9 條 link、B → A 有 0 條 link

讀者從 B 進入、看不到 A 的存在；只有從 A 進入才知道兩者並列。

問題不在 *單向 link 本身錯*、在 *vendor batch 結束沒跑 bidirectional audit*、就以為「cross-link 已建立」。

## Case：MySQL ↔ PostgreSQL cross-link asymmetry

4-reviewer audit（Reviewer B）finding：

- MySQL 18 篇對 PG sibling 的 cross-link：9 條（vs PostgreSQL 對比段 / 連到 PG vendor page / 連到 PG sibling article）
- PG 11 篇對 MySQL 的 cross-link：0 條

讀者站 PG `pgbouncer-config` 不會跳到 MySQL `proxysql-config`；站 MySQL `proxysql-config` 直接看到「跟 PG pgBouncer 對比」段。Navigation asymmetric。

## 機制：為什麼會單向

### 1. 寫第二個 batch 時 reference 第一個 batch 是自然行為

寫 MySQL `replication-topology` 時、PG `patroni-ha` 已存在、自然連去做對比。寫 PG `patroni-ha` 時、MySQL `replication-topology` 還不存在、不可能 link。

這是 *sequential 寫作的時間性結構性*、不是疏忽。

### 2. Bidirectional link audit 不在預設寫作流程

寫完 batch B 後、預設 audit：

- lint / cards
- emoji / 裸 URL
- 跨檔一致性

**沒有** *向上回補 sibling A 的 cross-link* 這一步。

### 3. Sibling A 寫好後、不會自動 trigger A 的更新

寫 vendor batch B 完成時、A 的內容不變、沒人 trigger「現在 sibling B 存在了、A 應該加 cross-link 回 B」。

## 修法：Bidirectional cross-link audit

### Audit 步驟

寫完 vendor batch B（B 跟 sibling A 存在對應）後、跑：

```bash
# 1. Count A → B link
rg -c "\]\(/path/to/B/" content/path/to/A/*.md

# 2. Count B → A link
rg -c "\]\(/path/to/A/" content/path/to/B/*.md

# 3. 對比
# 若 A→B 顯著少於 B→A、補 A 端 cross-link
```

### 補 A 端 cross-link 的位置

每個 A article 應該在：

1. **「相關連結」段** — 列對應 sibling B article
2. **「跟其他 vendor 的取捨」段**（若有） — 提到 sibling B 的對應
3. **「下一步路由」 / 「替代路徑」段** — 列 B 作為 alternative

### Audit cadence

- 每個 sibling vendor batch 寫完、跑一次 bidirectional audit
- 不只寫完 *第二個* batch、寫完 *第三 / 第四個* 也跑（A↔B↔C 三方對稱）
- vendors/_index 內容覆蓋進度表加 `link_density` 欄、揭露 asymmetry

## 跟既有原則的關係

- [Sibling Coverage Asymmetry Blindspot in Priority](../sibling-coverage-asymmetry-blindspot-in-priority/)：本卡是 cross-link asymmetry、那卡是 coverage asymmetry、同型但不同 axis
- [Cards as Living System Iteration](../cards-as-living-system-iteration/)：cross-link 維護是 living system 部分、不是 one-shot

## 反向驗證

不該誤用：

- *Sibling vendor* 限同類角色（PG / MySQL 都 SQL baseline）、不是任意兩個 vendor。MySQL 沒必要 link Spanner（不同類）
- 雙向不等於 *對稱數量* — A 18 篇可能有 9 條 link、B 11 篇有 6 條 link 是合理（不是 9 對 9）
- Migration playbook 結構性單向（A → B 是遷移、不是 B → A）— 對 migration playbook 是 *單向結構*、不適用本 audit
