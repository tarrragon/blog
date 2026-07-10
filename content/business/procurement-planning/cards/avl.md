---
title: "AVL（合格供應商與料件清單）"
date: 2026-07-10
description: "判斷一顆料或一家供應商能不能直接採用、生命週期標記要不要反映到選型限制時查閱"
weight: 97
tags: ["business", "procurement", "knowledge-cards"]
---

AVL（Approved Vendor List，合格供應商清單，常跟核准料件清單一起維護）的核心概念是「公司核准可採用的供應商與料件範圍」——設計選型與採購下單的預設邊界。進入 AVL 要走過認證（供應商稽核、料件驗證，量產核准見 [PPAP](/business/procurement-planning/cards/ppap/)），所以 AVL 上的每一列都是一筆已付的認證投資。

## 概念位置

AVL 是多個決策的執行載體：[替代料](/business/procurement-planning/cards/alternate-part/) 要事先認證進 AVL 才有救援價值；[第二供應商](/business/procurement-planning/cards/second-source/) 養成的終點是 AVL 上多一列可下單的來源；生命週期治理靠在 AVL 上標記或移出 [NRND / EOL 料](/business/procurement-planning/cards/lifecycle-status/)，讓新設計自動避開。代工情境（EMS / ODM）的 AVL 常由客戶控制，換料與加源要走客戶核准——這會改寫上述每個決策的自由度。

## 可觀察訊號與例子

AVL 健康度的訊號：關鍵料有沒有兩列以上可下單的來源、NRND / EOL 標記是否及時反映（標記滯後等於新設計還在往停產料上押）、替代料的認證是否仍新鮮。設計選型系統直接讀 AVL 狀態擋料時，生命週期訊號就從「採購知道」升級成「設計端自動避開」。

## 判讀方式

AVL 是治理工具，維護即治理：清單只增不減、標記不更新，擋新案與導引選型的功能就失效。判讀一顆料的採用資格，除了在不在清單上，還要看狀態欄——同一顆料可能是「量產可用」「限維修使用」「僅既有設計」等不同粒度，粒度的設計本身承載退場政策；AVL 在退場治理中的角色——標記擋新案、擋住成長中的用量——展開見 [生命週期監測與退場治理](/business/procurement-planning/lifecycle-phaseout-governance/)。
