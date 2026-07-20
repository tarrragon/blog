---
title: "Stub"
date: 2026-07-20
description: "測試作者手動寫死回應資料的 test double：驗證的是假設成立時邏輯是否正確，假設本身錯誤時無法檢出"
weight: 14
tags: ["testing", "stub", "test-double", "fake-backend"]
---

Stub 是測試作者手動寫死回應資料的 test double：呼叫者拿到的每一筆資料，都是測試在建置階段逐條餵進去的固定值。它跟[語意級假後端](/testing/knowledge-cards/semantic-fake-backend/)的分野在狀態的歸屬——stub 的回應由測試作者寫死，假後端自己持有狀態、隨操作演變。Stub 回放的是測試作者對後端行為的假設，假設錯了，測試照樣綠燈，這是它的結構性限制，不是實作疏忽。

## 概念位置

Stub 驗證的標的是「假設成立時、前端邏輯是否正確」，不是「假設本身是否成立」。假設與斷言出自同一人之手，永遠自洽——這一點讓 stub 沒有能力檢出「對後端行為的理解本身就錯了」這一類 bug。[Mock 遮蔽](/testing/knowledge-cards/mock-masking/)描述的是協議層的結構性盲區，stub 的盲區發生在更上游：連需要驗證的行為假設都由同一人設計。兩種盲區疊加時，測試綠燈能證明的範圍比表面上小得多。

## 可觀察訊號與例子

辨識訊號是「stub 資料與斷言預期出自同一次測試撰寫」——沒有獨立於測試作者的行為出處。典型案例：前端把後端資料的 id 凍結在本地記錄裡，單元測試建立記錄時順手把對應資料餵進 stub，凍結 id 與 stub 資料恆常一致；真實世界裡讓 id 失效的是後端的合併操作，stub 沒有這個行為，於是「id 失效」這個狀態在測試裡永遠不會出現，功能全壞、測試全綠（[T.C5](/testing/cases/stale-reference-stub-blindspot/)）。

## 設計責任

判斷「stub 夠不夠」的問句是：如果把 stub 換成真實服務，斷言結果會不會改變？只驗證程式碼內部邏輯（狀態機轉換、錯誤處理分支）時，stub 夠用；驗證對象是「對後端行為的假設」本身時，stub 結構上驗證不出來，需要換成持有狀態、行為有實測出處的[語意級假後端](/testing/knowledge-cards/semantic-fake-backend/)。凡是前端持有後端 id 的地方，都要追問後端的哪些操作會讓這個 id 死亡，並把「id 失效」的劇本納入測試範圍——見[凍結參照與活解析](/testing/knowledge-cards/frozen-vs-live-reference/)。
