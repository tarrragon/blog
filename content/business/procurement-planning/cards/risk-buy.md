---
title: "Risk Buy（風險備料）"
date: 2026-07-09
description: "說明在需求確定前先備關鍵料或原材料的風險備料手法"
weight: 30
tags: ["business", "procurement", "knowledge-cards"]
---

Risk Buy（風險備料，也寫作 Risky Buy）的核心概念是「在正式需求確定前，先自行承擔風險備下關鍵料」。目的是換取缺料時的供貨保障：市場一有缺料訊號，就先卡住料或產能，而不是等需求單下來才動。Risk Buy 是 [Forecast](/business/procurement-planning/cards/forecast/) 的進階操作—根據預測的風險比例先下手，承擔備錯的成本。

## 概念位置

Risk Buy 站在「風險管理」與「呆料成本」之間。備得早能避免 [斷料](/business/procurement-planning/cards/stockout/)，但若需求沒來，備下的料就變庫存壓力。判斷關鍵是備什麼、備多少：不一定要備成品，可以只針對長 [Lead Time](/business/procurement-planning/cards/lead-time/) 的原材料，按 forecast 風險備一定比例，把呆料風險控制在原材料層而不是成品層。

## 可觀察訊號與例子

該不該 Risk Buy，看幾件事：市場是否傳出某類料要缺（原廠發 allocation、PCN 停產通知、broker 現貨價跳動都是徵兆）、這顆料的 LT 是否長到「等需求確定再下單就來不及」、上游零件是否出現漲價或緊縮。市場傳 GPU 缺料時，先備足兩家 MOSFET 並跟原廠綁季度產能，Server 案子就不會被單一供應商卡死—這就是把上游趨勢轉成 Risk Buy 動作的例子。

## 判讀方式

考慮 Risk Buy 時，先分層決定風險落在哪：長交期料備原材料而非成品，把備錯的損失壓在最低層級。同時確認公司文化能不能承擔—有些組織對呆料零容忍，Risk Buy 空間就小。會出事的通常是把 Risk Buy 當成「多囤一點總沒錯」，忽略備錯的呆料與現金佔用成本。Risk Buy 是有意識地拿呆料風險換供貨保障，兩邊都要秤。
