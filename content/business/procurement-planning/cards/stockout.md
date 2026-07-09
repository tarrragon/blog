---
title: "斷料（Stockout）"
date: 2026-07-09
description: "說明產線缺料停線作為採購最高禁區的判讀意義"
weight: 60
tags: ["business", "procurement", "knowledge-cards"]
---

斷料（Stockout）的核心概念是「產線需要某顆料時，手上沒有可用庫存，導致無法生產」。在電子業採購裡，斷料是最高禁區—整個 planning 體系的目標可以濃縮成一句話：絕對不可以斷料。所有備料手法，從 [Safety Stock](/business/procurement-planning/cards/safety-stock/) 到 [Risk Buy](/business/procurement-planning/cards/risk-buy/)，本質都是為了不讓斷料發生。

## 概念位置

斷料是採購所有風險管理動作的反面目標。[Forecast](/business/procurement-planning/cards/forecast/)、供應商佈局、[追料](/business/procurement-planning/cards/expediting/)、替代料、安全庫存看起來是五件事，其實是同一件事—圍繞「不斷料」這個底線各自佈防。斷料一旦發生，代價是停線，往下牽動交貨違約與客戶信任，遠高於呆料或多備一點的成本。

## 可觀察訊號與例子

判讀斷料風險升高的訊號：關鍵料的在途訂單覆蓋不到下一個 [Lead Time](/business/procurement-planning/cards/lead-time/)、單一供應商的品質或產能突然出狀況、地震颱風等事件衝擊供應商工廠。天災隔天，第一件事就是問廠商工廠產能供貨有沒有受影響—因為任何一顆關鍵料的供應中斷，都可能變成斷料。

## 判讀方式

把不斷料當成 planning 的第一原則，反推所有備料與供應商決策。判斷任何一個備料選項時，先問「這個安排能不能守住不斷料」，再談成本與效率。常見陷阱是為了壓庫存或省成本，把緩衝削到剛好夠—一有波動就破防。斷料的代價不對稱：省下的庫存成本遠小於停線的損失，所以底線要守在斷料之前留餘裕，而不是踩線。不過這個不對稱性對高衝擊料才成立：低毛利、易替代或走向 EOL 的料，永久 buffer 的持有成本可能反過來高於一次可控的缺料，所以斷料底線要分料看，搭配分層備料。
