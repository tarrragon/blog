---
title: "NCNR（不可取消不可退）"
date: 2026-07-09
description: "說明訂單的可取消性與改單截止日如何影響策略性下單"
weight: 110
tags: ["business", "procurement", "knowledge-cards"]
---

NCNR（Non-Cancellable Non-Returnable，不可取消不可退）的核心概念是「一旦下單就無法取消或退貨的訂單條件」。它的反面是「可在某個截止日前無條件改單或取消」的一般訂單。NCNR 直接決定 [Risk Buy](/business/procurement-planning/cards/risk-buy/) 的成本：可取消的單先卡位不會有損失，NCNR 的單一下去就要吃下。

## 概念位置

NCNR 站在「先卡產能」與「承擔呆料」之間。若一個料號在改單截止日前可以無條件修改或取消，就能大膽先下遠期單卡住產能，之後再依實際需求調整。反過來，NCNR 或已過截止日的單，等於買斷，要用 [Forecast](/business/procurement-planning/cards/forecast/) 信心足夠的量才下。判斷一顆料的下單策略前，要先搞清楚它受哪些原廠與代理商規則約束。

## 可觀察訊號與例子

判讀下單彈性的訊號：這個料號是不是 NCNR、改單或取消的截止日（例如某些代理商的 CXD，cancel 截止日）在什麼時候、有沒有 small-reel、EOL-LTB、NRND 這類例外限制。以某代理商的某原廠料為例，除了 small-reel、EOL-LTB、NRND 以外，只要在截止日前都可以無條件修改或取消—這種規則下，可以直接把常用料號下遠期單卡位，反正不是 NCNR。

## 判讀方式

面對每顆料，先確認它的可取消性與截止日，再決定卡位多遠。可無條件取消的料，往前多下卡產能幾乎沒有下檔風險；NCNR 的料，下單量要收斂到 forecast 有把握的範圍。常見陷阱是不分規則一律保守下單，白白錯過可取消料的卡位機會；或反過來對 NCNR 料過度樂觀，下太多變呆料。策略性下單的前提是先讀懂每顆料的訂單規則。
