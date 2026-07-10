---
title: "PCN（產品變更通知）"
date: 2026-07-10
description: "收到 PCN 要判斷變更類型、影響範圍與要不要重新驗證，或懷疑停產通知沒送到自己手上時查閱"
weight: 125
tags: ["business", "procurement", "knowledge-cards"]
---

PCN（Product Change Notification，產品變更通知）的核心概念是「原廠對料件即將發生的變更所發的正式預告」——製程調整、材料替換、產地移轉、封裝改版，一路到停產（EOL 通知常以 PCN 形式或伴隨 PCN 發布）。功能是給客戶一段評估期：在變更生效前判斷影響、決定要不要重驗或提出異議。跟 [料件生命週期](/business/procurement-planning/cards/lifecycle-status/) 卡相鄰：生命週期狀態描述走向，PCN 是走向落地成正式時點的載體。

## 概念位置

PCN 站在「原廠變更」與「客戶驗證」的介面上。變更要不要重跑驗證，看它觸及的層面：動到 form / fit / function（外形、配合、功能）的變更，下游要走接近 [PPAP](/business/procurement-planning/cards/ppap/) 的重新核准；純產地或物流層的變更，多數客戶備查即可。醫療、車用等受規範產業對 PCN 的評估與答覆有合規義務，紀錄要留全。

## 可觀察訊號與例子

一份 PCN 要抓的欄位：變更類型與原因、生效日、受影響料號清單，以及停產類 PCN 特有的 LTB（最後採購）截止日。收到停產類 PCN，等於 [EOL-LTB 買斷決策](/business/procurement-planning/eol-ltb-buyout-decision/) 的正式起跑點。

## 判讀方式

PCN 的送達機制決定它可靠度的邊界：通知寄給有直接交易關係的窗口，經現貨商或非授權管道買的料收不到，窗口離職也會斷鏈。判讀時把 PCN 當「存在時很準、缺席時無訊息」的來源——沒收到 PCN 推不出「沒有變更」，要配 BOM 對生命週期資料庫的定期比對兜底，接收機制的設計見 [生命週期監測與退場治理](/business/procurement-planning/lifecycle-phaseout-governance/)。
