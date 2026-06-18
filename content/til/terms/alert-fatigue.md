---
title: "alert fatigue：告警疲勞"
slug: "alert-fatigue"
date: 2026-06-18
description: "alert fatigue 指誤報或告警太多、人對告警逐漸麻木，連真正重要的也忽略。它不是 false positive 的同義詞，而是 false positive 持續累積造成的人因後果"
tags: ["til", "術語", "跨領域", "alert-fatigue"]
---

> 這個詞出現在「[告警太多，反而沒人看](../alert-overload/)」這個問題裡——它是這條因果鏈的終點。

alert fatigue（告警疲勞）指**誤報與告警太多，人對告警逐漸麻木，連真正重要的也一起忽略**。

要注意它和「誤報」本身不是同一件事：alert fatigue 不是 [false positive](../false-positive/) 的另一個叫法，而是 false positive **持續累積造成的人因後果**。源頭常見於醫療（病房監視器整天響）與資安維運。

## 怎麼形成

[false alarm](../false-alarm/) 與 [noise](../noise/) 累積 → 每個告警的可信度下降 → 人開始預設「大概又是誤報」→ 真事件來時也被當誤報略過。測試領域的對應是把 [flaky](../flaky/) 紅燈一律重跑、不再查。

## 解法方向

- **降噪**：提高告警 [precision](../precision/)，少報無關的。
- **分級**：可行動的才叫醒人，其餘進儀表板。
- **可行動性**：每個告警都附「該做什麼」，否則它只是 noise。

## 相關概念

- 累積成它的來源：[false positive](../false-positive/)、[false alarm](../false-alarm/)、[noise](../noise/)。
- 測試領域的類比：[flaky](../flaky/) 被一律重跑。
