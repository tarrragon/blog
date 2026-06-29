---
title: "多輪審查至少三輪是硬底線"
date: 2026-06-29
description: "多輪審查跑完 Round 2 想收手時回來讀 — Round 3 的 steelman/outbound frame 在每次實測都找出 10+ 項、問要不要跑等於問要不要跑一定有產出的審查"
weight: 202
tags: ["report", "review", "multi-round-review"]
---

## 結論

多輪審查（multi-round-review）的最低輪數是三輪，不是「看 finding 數決定要不要繼續」。Round 3 不是可選的加深，而是覆蓋 Round 1-2 結構性盲區的必要輪。

## 為什麼

Round 1（compliance / baseline）和 Round 2（cadence / reader journey）用的 frame 都是「從作者端出發」的維度——規範有沒有遵守、句型有沒有重複、讀者走路線順不順。這兩輪能 catch 的問題有一個共同特徵：它們在「文章已經寫出來的內容」裡找錯。

Round 3 的 frame 是「從文章沒寫的東西出發」——enumeration 有沒有漏選項（steelman）、其他系列有沒有反向引用（outbound）、搜尋落地粒度夠不夠（search landing）、知識卡缺口。這類問題在 Round 1-2 的 frame 下結構性不可見，因為 reviewer 在已有內容裡掃描時，不會主動問「這裡應該還有一個選項但沒寫」。

## 反模式

「Round 2 修完、finding 數下降、覺得差不多了就停」是最常見的反模式。multi-round-review skill 已經明確寫了「停止訊號是 frame 涵蓋、不是 finding 數遞減」，但實際執行時仍然會在 Round 2 結束後問「要不要繼續」——這個提問本身就是 finding 遞減直覺在主導判斷。

## Evidence

Dotfile 系列（29 篇 + 知識卡）三輪審查的 finding 分布：

| Round | Frame                      | Finding 數 |
| ----- | -------------------------- | ---------- |
| 1     | 規範 / fact-check / 一致性 | 15         |
| 2     | Cadence / 讀者旅程 / 冷讀  | 14         |
| 3     | Steelman / Outbound        | 14         |

Round 3 的 14 項不是 Round 1-2 的殘餘——它們是全新類型的問題：macOS 原生 tiling 遺漏、yadm/mise 選項缺失、跨系列反向引用斷裂、知識卡缺口。這些問題在 Round 1-2 的 frame 下不會被 catch。

先前的 backend 教學模組 review 也觀察到類似分布：三輪各 catch 不同類型的問題、finding 數不遞減。

## 修法

把「至少三輪」從「建議」升級為「硬底線」。Round 3 結束後才進入「要不要繼續」的判讀——此時用七軸涵蓋度和「想不出新 frame」作為停止訊號。

## 跟其他原則的關係

- [#114 multi-pass frame 顆粒度盲點](/report/writing-multi-pass-review/) — 同 frame 多輪無增益，多輪價值在 frame 切換
- [#148 跨輪 review 停止訊號](/report/cross-round-review-stopping-signal/) — 停止訊號是 frame 涵蓋、不是 finding 遞減
- [#126 review 七軸完整度](/report/writing-review-multi-axis-completeness/) — 七軸動完是停止條件之一，三輪是動完七軸的最低路徑

## 判讀徵兆

以下情境代表三輪硬底線正在被繞過：

- Round 2 結束後問「要不要繼續」「到這裡收嗎」
- Round 3 的 frame 規劃被跳過、直接宣布 review 完成
- 用「Round 2 finding 數比 Round 1 少」作為停止依據
