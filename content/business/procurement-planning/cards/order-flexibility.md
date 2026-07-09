---
title: "Blanket Order 與 Flex Fence（訂單彈性機制）"
date: 2026-07-10
description: "在「可取消」與「NCNR 買斷」之間找中間形態、要用需求確定性跟供應商交換供貨保障時查閱"
weight: 115
tags: ["business", "procurement", "knowledge-cards"]
---

訂單彈性機制的核心概念是「把『承諾』與『買斷』在時間軸上拆開的合約設計」。[NCNR](/business/procurement-planning/cards/ncnr/) 與可無條件取消是光譜的兩端，中間形態讓買賣雙方在不同時點交換不同程度的確定性：blanket order（框架單）承諾年度總量、依排程分批釋出（release）——量的承諾換到價格與產能保留，單批釋出後才進入買斷；三段式 reschedule window 把訂單沿時間分成三段——近端窗口內凍結買斷（凍結窗的邊界即 time fence）、中段可在約定比例內改量改期（各期可改比例的上限即 flex fence）、遠端自由調整。

## 概念位置

這組機制站在買方的「供貨保障」與賣方的「需求確定性」之間，是兩邊各讓一步的交換結構：買方拿到產能保留與價格，賣方拿到可排產的承諾。付款軸上的對應機制是 [寄售](/business/procurement-planning/cards/consignment/) 與 VMI（vendor-managed inventory，供應商代管庫存——付款遞延到動用）。整組規則怎麼組合成下單策略，展開在 [原廠與代理商規則的經濟學](/business/procurement-planning/vendor-lifecycle-rules/)。

## 可觀察訊號與例子

判讀一份合約彈性結構的訊號：fence 的段數與天數（凍結窗多長、彈性窗可改比例多少）、blanket 總量的達成義務是硬承諾還是盡力條款、未釋出餘量在年度結束時的處理（結轉、買斷、還是失效）。談判時的攻防集中在 fence 位置：供應商想把凍結窗拉長（排產確定性），買方想把它壓短（保留反應空間）。

## 判讀方式

用自己需求的不確定性形狀去談 fence：需求裡確定的底量放進 blanket 承諾換價格，波動的部分留在彈性窗內，投機的部分留在圍籬外。常見的失誤是把 blanket 總量按樂觀情境簽——總量承諾是軟性的 NCNR，年底達不成一樣要付代價（補償金、來年議價力受損）。承諾量收斂到 [forecast](/business/procurement-planning/cards/forecast/) 真正有把握的需求範圍，跟 NCNR 下單量收斂到置信區間是同一個判準（見 [原廠與代理商規則的經濟學](/business/procurement-planning/vendor-lifecycle-rules/)）。
