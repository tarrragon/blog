---
title: "Moving Iron Cartridge（動鐵式唱頭，MI）"
slug: "moving-iron-cartridge"
date: 2026-11-11
description: "選唱頭時看到 MI、moving iron、動鐵式，或 Grado、Soundsmith 這類唱頭不屬於 MM 也不屬於 MC，要判斷它該接哪一種 Phono 輸入、負載怎麼設時"
weight: 29
tags: ["til", "音響", "knowledge-cards"]
---

動鐵式唱頭（moving iron，MI）的磁鐵與線圈都固定在唱頭本體，針桿上只帶一小塊導磁的鐵片。唱針被溝槽推動時，鐵片跟著動，改變穿過線圈的磁通量，線圈因此感應出電壓。它跟 [MM 與 MC 唱頭](/til/audio/knowledge-cards/mm-and-mc-cartridges/)的分類用的是同一個依據：跟著針桿動的是哪一樣。MM 動的是磁鐵，MC 動的是線圈，MI 動的是鐵片。

## 概念位置

MI 把磁鐵與線圈都留在本體上，所以針桿要帶動的質量可以做得很小；代價是鐵片小時，能改變的磁通量也小，輸出電壓不能只靠加大磁鐵與線圈來補回。結果是各家 MI 的輸出電壓分布很廣，從接近 MC 的零點幾毫伏到跟 MM 相當的幾毫伏都有，接法要依那一顆的輸出決定，不能只看「MI」這個名稱。它的線圈固定在本體上、圈數可以多，電氣上多半接近 MM：負載用 MM 輸入的 47 kΩ 一類，增益看輸出電壓對到[線路電平](/til/audio/knowledge-cards/line-level/)需要多少。

## 可觀察訊號與例子

依廠商與零售商公布的規格（2026 年）：

- Grado 的 Timbre 系列分高輸出（約 4.0 mV）與低輸出（約 1.0 mV）兩種版本。
- Soundsmith 的 Mezzo、Nautilus 約 1.1 mV，SMMC1 約 2.1 mV，都設計給 MM 的唱頭放大器用；同一家的 Zephyr MIMC 約 0.4 mV，要接增益約 58 到 64 dB 的 MC 唱頭放大器。
- 不同零售商對 Grado 低輸出版是否需要額外增益的說法互相矛盾，以 Grado 的規格表為準。

## 判讀方式

一顆 MI 唱頭接哪一種輸入，看它標示的輸出電壓，不看名稱：輸出在 2 mV 以上時，接 MM 的 Phono 輸入；約 1 mV 時，接 MM 輸入可能音量偏小，要確認唱頭放大器的增益或選有較高增益設定的機種；落在 MC 的範圍（零點幾毫伏）時，照 MC 的增益接。負載多半照 MM 的 47 kΩ，以唱頭規格表的建議值為準。換針、有效針尖質量與唱臂的共振搭配，照各自的判斷看，跟唱頭屬於哪一類無關。

MM 與 MC 的電壓、增益與負載在〔[黑膠唱盤的構造、選購與安裝調整](/til/audio/turntable-buying-guide/)〕的〈MM 與 MC 唱頭：發電方式、輸出電壓與換針〉與〈唱頭放大器的三種位置：內建在唱盤、內建在擴大機、獨立一台〉。
