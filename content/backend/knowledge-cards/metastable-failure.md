---
title: "Metastable Failure（負載退去後仍停在失效狀態）"
date: 2026-10-14
description: "流量已經回到平常的量而服務仍然大量逾時或出錯、或要判斷一次過載為什麼沒有自己恢復時，查 metastable failure 的定義、讓它停在失效狀態的持續效應、偵測它要比對的訊號與脫離它的做法"
weight: 486
tags: ["backend", "reliability", "performance", "overload"]
---

Metastable failure 指服務在一次觸發（短暫的流量尖峰、一次依賴故障、一次重新部署）讓它過載之後，觸發已經消失、使用者發起的請求量也回到平常，服務仍然停在大量逾時或出錯的狀態。這個名字來自 Bronson 等人在 HotOS 2021 發表的〈Metastable Failures in Distributed Systems〉，論文把讓服務停在失效狀態的機制稱為持續效應（sustaining effect）：過載本身產生了額外的工作，額外的工作又維持過載。Huang 等人在 OSDI 2022 整理的公開事故中，超過一半由重試維持（[Retry Storm](/backend/knowledge-cards/retry-storm/)）。Metastable failure 與 [Cascading Failure](/backend/knowledge-cards/cascading-failure/) 描述同一次故障的兩個方向：cascading failure 是故障往其他元件擴散，metastable failure 是故障在觸發消失之後仍延續；兩者可以同時發生，論文也寫到持續效應會讓沒碰到觸發的元件跟著進入失效狀態。

## 概念位置

同一個服務平常處理得了的負載，在 metastable failure 期間處理不了，因為服務做的工作比進來的請求多。常見的持續效應：用戶端的重試讓同一個請求被送好幾次（[Retry Storm](/backend/knowledge-cards/retry-storm/)）；伺服器繼續處理已經逾時、沒有人在等結果的舊請求，佔掉處理新請求的資源；快取在故障或重啟後變空，原本由快取擋下的讀取全部打到資料庫（[Cache Warmup](/backend/knowledge-cards/cache-warmup/)）；過載造成的 GC、鎖競爭或 leader 反覆選舉，讓服務每秒處理得了的請求變少。Google《Site Reliability Engineering》的〈Addressing Cascading Failures〉舉的例子是一個在每秒一萬個請求下健康的服務，到每秒一萬一千時因當機開始連鎖失效；把負載降到每秒九千幾乎止不住當機，因為需求集中到剩下的少數伺服器上，假設只剩一成伺服器健康，要降到約每秒一千才能穩定並恢復；同一章也寫到，重試會讓後端在原始的請求率下降之後仍然過載，要大幅降低前端送進來的負載直到重試停止。

## 可觀察訊號與例子

判斷的依據是比對兩組數字：使用者發起的請求率（扣掉重試）已經回到平常的量，而每秒成功完成的請求數（goodput）或錯誤率仍沒有回到平常；總請求率可能因為重試而高於平常。另外兩個訊號是重試流量佔總請求的比例偏高，以及資料庫的讀取量明顯高於平常的同一時段（快取還沒熱）。短網址服務在一次資料庫切換之後，轉址請求的總量回到平常，成功的轉址卻只有平常的一半，log 裡同一個使用者在幾秒內重複送出同一個請求的紀錄大量出現，就是這個樣子（例子的數字是示意）。

## 判讀方式

流量回到平常而服務仍不恢復時，先確認兩件事。一是觸發已經消失：依賴的錯誤率與延遲回到平常、被移出的實例已經補回、新部署的版本已經回滾或確認每個請求的成本沒有變高；觸發是依賴故障或容量減少時，請求率從頭到尾都在平常的範圍，觸發仍在的過載也長得一樣。二是資源仍然飽和（等待連線的請求數、CPU 或資料庫讀取量高於平常），或依賴的配額被重試用完而回 429；兩者都沒有時，成因不是過載，要回到部署、設定與依賴的變更去找。資源飽和時要處理的是持續效應：等流量自己退不會讓服務恢復，加容量要加到能消化重試與舊請求帶來的額外工作才有效。脫離 metastable failure 要拿掉持續效應：把進入服務的負載壓到平常的量以下（負載卸除、准入控制）、讓用戶端停止重試或拉長退避、丟掉已經逾時的排隊請求、先預熱快取再恢復全部流量。預防的做法是在平常就限制持續效應：重試預算、有上限的佇列與逾時、依優先等級卸除。負載超過容量時服務呈現的各種結果與各自的判斷標準，見 [9.16 負載超過容量時服務的表現](/backend/09-performance-capacity/overload-outcomes/)；卸除與准入的做法見 [9.15 無預警瞬時大流量](/backend/09-performance-capacity/unplanned-traffic-surge/)。
