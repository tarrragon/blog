---
title: "Admission Control（准入控制）"
date: 2026-10-02
description: "要決定湧入的使用者誰能進入、什麼時候進入時，例如開賣的虛擬等候室、waitlist、事前註冊與抽籤；和負載卸除、限流的分工，以及和 Kubernetes admission controller 的區分"
weight: 447
tags: ["backend", "performance", "admission-control", "knowledge-card"]
---

Admission control（准入控制）的核心概念是「在請求進入受保護的路徑之前，決定誰能進入、什麼時候進入」。被擋下的使用者留在受保護的路徑外面等候，看到的是等候畫面或排隊位置，而不是錯誤。可先對照 [Load Shedding](/backend/knowledge-cards/load-shedding/) 與 [Rate Limit](/backend/knowledge-cards/rate-limit/)。

## 概念位置

准入控制和負載卸除、限流處理的是同一個過載問題的不同位置。[Load Shedding](/backend/knowledge-cards/load-shedding/) 依整個系統的狀態，決定已經到達的請求要不要處理；[Rate Limit](/backend/knowledge-cards/rate-limit/) 依送出請求的呼叫者分配配額；准入控制在請求到達受保護的路徑之前，決定一個人或一個會話能不能進入、排在第幾位。三者常一起出現：等候室放進受保護區的人數由准入控制決定，受保護區裡個別使用者的請求頻率由限流管，整體仍然過載時由負載卸除拒絕低優先的請求。

服務過載的語境裡，這個詞也用在入口依系統狀態逐請求拒絕，例如 Envoy 的 admission control filter 依成功率拒絕請求；那個用法和 [Load Shedding](/backend/knowledge-cards/load-shedding/) 重疊，本卡講的是以人或會話為單位的放行。這個詞在 Kubernetes 裡另有一個意思：admission controller 是 API server 在寫入物件之前檢查或改寫請求的外掛（例如 Gatekeeper、Kyverno）。那是設定治理的機制，和這張卡講的流量准入無關。

## 可觀察訊號與例子

需要准入控制的訊號是需求在一個時間點集中湧入、而且超過系統能承接的量，例如演唱會開賣、限量商品發售、新服務上線。常見的形態有四種：虛擬等候室（開賣前把請求導到另一頁，到時間依吞吐量放行，或只讓受保護區容納固定並發人數、其餘排隊）、waitlist（逐批邀請）、事前註冊（開賣前先驗證身分，只讓通過的人進入佇列）、抽籤（把先到先得改成隨機抽選，搶快就沒有優勢）。准入控制只決定誰能進入受保護的路徑，被擋下的人與機器人的請求仍然打在網站上，所以總流量要另外靠邊緣快取、WAF 與負載卸除吸收。案例與完整推導見 [9.15 無預警瞬時大流量：流量來源辨識、擴展緩衝、請求優先等級、准入控制、體積型攻擊與退路](/backend/09-performance-capacity/unplanned-traffic-surge/) 的〈准入控制：虛擬等候室（virtual waiting room）、waitlist 與事前註冊〉，以及 [SeatGeek：DynamoDB + Lambda 打造的虛擬等候室](/backend/09-performance-capacity/cases/seatgeek-virtual-waiting-room/)。

## 設計責任

准入控制要定義放行的規則（先到先服務、依身分優先、隨機）、放行的速度（每分鐘多少人、受保護區的並發上限）、排隊者看到什麼，以及排隊本身的保護：等候室也是公開入口，前面要放 DDoS 防護與 WAF。事前註冊要能篩掉機器人，前提是註冊本身有成本或驗證；放行速度要和後端實際容量一起調整，太快會讓受保護區過載，太慢則讓可售的名額賣不完。
