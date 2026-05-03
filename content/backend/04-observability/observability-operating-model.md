---
title: "4.18 Observability Operating Model"
date: 2026-05-02
description: "定義 platform / service team / on-call 對訊號、dashboard、alert 與成本的 ownership"
weight: 18
---

## 大綱

- operating model 的責任：定義誰擁有訊號、誰維護 dashboard、誰處理 alert、誰承擔成本
- 角色分工：platform team、service team、on-call、incident commander、security / compliance
- ownership 欄位：owner、review cadence、retention、cost center、runbook link、deprecation date
- 生命週期：新增、審核、使用、修訂、淘汰
- 治理節奏：dashboard review、alert review、cost review、post-incident write-back
- 跟 04.15 cost attribution 的關係：成本歸屬是 operating model 的一部分
- 跟 08 的關係：事故時使用同一組 owner 與 escalation route
- 反模式：平台團隊擁有所有 alert；service team 不看 dashboard；成本無 owner

Observability operating model 的價值是把觀測從「工具責任」改成「服務責任」。只靠平台團隊維護訊號，通常會得到技術完整但業務脈絡不足的監控；只靠服務團隊則常出現跨服務標準不一致。模型的目的就是把兩者接口固定下來。

## 概念定位

Observability operating model 是把觀測資產的責任分配明確化的治理模型，責任是讓訊號有人維護、告警有人回應、成本有人決策。

這一頁處理的是 ownership。可觀測性需要平台工具、服務脈絡、操作責任與淘汰條件一起維持。

這層的判準不是 dashboard 數量或 alert 覆蓋率，而是事故當下是否能立刻知道誰要看哪個面板、誰有權調整閾值、誰負責決定淘汰過期訊號。

## 核心判讀

判讀 operating model 時，先看每個觀測資產是否有 owner，再看 owner 是否有權限與節奏採取行動。

重點訊號包括：

- dashboard 是否有明確使用者與 review cadence
- alert 是否有 [runbook](/backend/knowledge-cards/runbook/)、owner 與 escalation path
- 高成本訊號是否能對應服務價值與成本中心
- post-incident review 是否能回寫到訊號 owner
- orphan dashboard 與 stale alert 是否有清理流程

| 資產類型         | Owner                  | 週期   | 關閉條件               |
| ---------------- | ---------------------- | ------ | ---------------------- |
| Dashboard        | service team + on-call | 月檢   | 無使用者、無判讀價值   |
| Alert            | service owner          | 週檢   | 重複、誤報高、無行動   |
| Query / Schema   | platform + service     | 變更檢 | 欄位漂移、查詢成本失控 |
| Cost Attribution | cost owner             | 月檢   | 無法對應服務價值       |

## 判讀訊號

- alert 觸發後沒人知道該由平台或服務團隊處理
- dashboard 存在但半年無人打開
- 成本暴增時只能找平台團隊吸收
- post-incident review 指派 action item，但沒有訊號 owner
- service team 調整欄位後，平台查詢與 dashboard 斷裂

實務上常見的治理斷點是「有 owner 名字，沒有 owner 權限」。如果 owner 不能調整 alert、不能建立或下架 dashboard、不能分配成本，治理流程會回到平台集中處理，最後形成積壓與責任模糊。

## 交接路由

- 04.4 dashboard / alert：設計 owner、runbook 與停止條件
- 04.8 signal governance loop：淘汰 stale alert 與 orphan dashboard
- 04.15 cost attribution：把成本接回 owner 與服務
- 08.2 incident command roles：事故時使用相同 ownership 模型
- 08.16 runbook lifecycle：把觀測資產接進 runbook 版本治理
