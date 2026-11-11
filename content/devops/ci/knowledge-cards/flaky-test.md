---
title: "Flaky Test"
date: 2026-05-06
description: "說明非決定性測試如何降低 CI gate 信任度與治理方式"
tags: ["CI", "test", "flaky", "knowledge-card"]
weight: 15
aliases: ["/ci/knowledge-cards/flaky-test/"]
---

Flaky Test 的核心概念是「同一版本在相同條件下測試結果不穩定」。它會把紅燈從有效訊號降級成噪音，直接影響 [CI](/devops/ci/knowledge-cards/ci-pipeline/) gate 信任度。

## 跟其他概念的關係

Flaky Test 位在 test stage 與 release gate 之間，會放大[重跑](/devops/ci/knowledge-cards/rerun/)成本與判讀延遲。

## 可觀察訊號

- 同一 commit 重跑結果時好時壞。
- 失敗集中在等待條件、時間假設或外部依賴。
- 團隊習慣以重跑代替根因修復。

## 接近真實服務的例子

UI 測試在動畫未完成時抓取元素，或整合測試依賴不穩定第三方 API，都容易出現 flaky pattern。

## 判斷條件與後果

Flaky test 留在 CI gate 裡時，紅燈不再代表這一版有缺陷，團隊改用重跑判斷結果，每次失敗多花一次 CI 時間，真正的回歸也可能被當成不穩定而重跑過去。把它隔離出 gate 讓紅燈恢復成有效訊號，代價是那個測試涵蓋的行為暫時沒有防護；隔離沒有搭配 owner 與修復期限時，測試一直停在隔離區，暫時的防護缺口變成長期的。重跑次數與時好時壞的測試清單沒有被記錄時，團隊判斷不出 flaky 的數量在增加還是減少。

跨領域詞源與近鄰詞（間歇 vs 偽失敗、與 alert fatigue 的因果鏈）見 [TIL 跨領域術語：flaky](/til/terms/flaky/)。
