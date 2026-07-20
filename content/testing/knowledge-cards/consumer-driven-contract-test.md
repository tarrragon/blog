---
title: "Consumer-Driven Contract Test"
date: 2026-07-20
description: "client 與 server 分屬不同團隊、後端無法本機或容器啟動時，用契約取代對真實服務的協議整合測試"
weight: 15
tags: ["testing", "contract-test", "protocol-integration-test", "consumer-driven"]
---

Consumer-driven contract test 是 [protocol integration test](/testing/knowledge-cards/protocol-integration-test/) 的延伸形態：client 團隊定義「我期望的 request/response 格式」（契約），server 團隊在自己的 CI 裡驗證實作是否符合這份契約。跟直接對真實服務跑協議測試的差別在於，驗證分成兩側各自進行——client 端在本地對契約驗證自己的行為，不需要每次都打到對方的服務。

## 概念位置

這個形態解決的是[成本判斷](/testing/03-protocol-integration-test/cost-judgment/)裡「高成本」那一格：服務是外部 SaaS 或跨團隊 API、無法本機啟動、也不可寫入時，protocol integration test 需要的真實服務不存在於可控範圍內，consumer-driven contract test 成為主要出路。這跟[真實後端驗證測試](/testing/knowledge-cards/real-backend-verification-test/)處理的是同一個「無法本機啟動」的問題、但前提不同——真實後端驗證測試的前提是對象為自家可寫入的共用測試環境，consumer-driven contract test 的前提是對象不可寫入、且 provider 團隊願意在自己的 CI 裡驗證契約。

## 可觀察訊號與例子

適用的訊號是「API 有多個 consumer、且各自需要獨立部署」——每個 consumer 定義自己期望的契約，server 端彙整所有契約做相容性驗證，不需要等每個 consumer 團隊排期做整合測試。反訊號同樣明確：自用工具、或 client/server 由同一人開發，契約帶來的團隊協調成本沒有對應的收益，直接對真實 server 跑 protocol integration test 更簡單。工具生態（Pact、Spring Cloud Contract）自動化了契約的定義、驗證與版本管理，這類工具本身不是判準、是判準成立後的落地手段。

## 設計責任

導入前先確認 provider 團隊是否願意在自己的 CI 裡跑契約驗證——這是這個形態成立的協作前提，前提不成立時契約會變成 client 端單方維護、provider 端行為漂移仍然檢不出來。契約覆蓋的範圍要跟 protocol integration test 一致（request 格式、response 解析、error body 結構），否則契約驗證通過但真實互動仍可能因為契約沒覆蓋到的欄位而失敗。深入的 schema 相容性控制與跨服務契約演進見 [Backend 可靠性：Contract Testing 與 Schema 演進](/backend/06-reliability/contract-testing/)。
