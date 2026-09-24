---
title: "從章節到實作的兩條 chain：機制與交付"
date: 2026-09-24
description: "本模組各章交付的問題節點、判讀訊號與控制面連結，怎麼沿機制與交付兩條 chain 走到實作，以及兩條 chain 走完才算交付完整的完成條件"
weight: 71
tags: ["backend", "security", "routing"]
---

各章節交付三樣：問題節點清單、判讀訊號、控制面 link。判讀完成後沿兩條 chain 進入 implementation：

1. **Mechanism chain**：點問題節點表的 `[control-name]` link 進 [knowledge-cards](/backend/knowledge-cards/)、那層展開機制 / 邊界 / context-dependence。例：`[authentication]` 的 knowledge-card 是該 control 的 mechanism SSoT。
2. **Delivery chain**：章節「交接路由」欄位指向下游模組——`04-observability`（偵測 / 稽核 / 證據訊號）/ `05-deployment-platform`（入口 / 配置 / 平台邊界）/ `06-reliability`（驗證 / 回退 / 演練）/ `08-incident-response`（分級 / 指揮 / 通報 / 復盤）。

兩條 chain 走完，控制面交付完整。Implementation 強度取決於兩條 chain 的完成度，章節閱讀本身完成 routing 階段。

各章節在「從本章到實作」段給該章的具體 control-name 例子跟交接路由 list，這一篇是全模組共用的規格。
