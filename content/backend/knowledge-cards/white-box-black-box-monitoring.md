---
title: "White-box and Black-box Monitoring（白箱與黑箱監控）"
date: 2026-10-14
description: "分不清一個監控是從外部行為判斷還是讀取內部狀態、或把「黑箱探測」當成一定站在服務以外的觀察者時，查白箱與黑箱監控各回答什麼問題、各自看不到什麼，以及黑箱為什麼不等於在失效域以外"
weight: 481
tags: ["backend", "observability", "monitoring"]
---

白箱監控（white-box monitoring）讀取系統的內部狀態：程式自己輸出的請求指標、log 與 trace，主機與容器由 exporter 轉出的資源數字。黑箱監控（black-box monitoring）只看外部行為：從外面發一個請求，看回應的狀態碼、內容與耗時，不需要知道系統裡面怎麼運作。Google 的《Site Reliability Engineering》以這組對照區分兩種監控，Prometheus 的 blackbox_exporter 取的是黑箱監控的名字。兩者分的是觀察方式，與 [Probe](/backend/knowledge-cards/probe/) 這類由平台使用結果的探測、與 [Synthetic Monitoring（合成監控）](/backend/knowledge-cards/synthetic-monitoring/) 這類模擬使用者的探測都有交集。

## 概念位置

黑箱監控回答「使用者此刻看到的是不是正常」，所以它擅長發現已經發生、使用者感受得到的故障，也就是症狀；它說不出原因。白箱監控回答「系統裡面每個元件的狀態」，所以它能找原因、也能看到還沒造成症狀的趨勢（磁碟快滿、佇列開始堆積）；它看不到請求在進到系統之前就失敗的情形（DNS、TLS 憑證、入口以外的那一段），因為那時系統裡面沒有任何元件記錄到那個請求。兩者是互補的一組，告警多半寫在黑箱或請求指標的症狀上，白箱的數字用來找原因與預警。

黑箱與白箱分的是觀察方式，不分位置。黑箱探測跑在服務同一台主機或同一個叢集裡時，它與服務共用 [Failure Domain（失效域）](/backend/knowledge-cards/failure-domain/)，主機停掉時跟著停，也不經過使用者在網際網路上走的公開路徑。要回答「使用者從外面連得到嗎」，黑箱探測還要放在失效域以外。

## 可觀察訊號與例子

同一個短網址服務上，白箱監控的例子是 node_exporter 給的主機 CPU 與磁碟、PostgreSQL 的連線數、程式輸出的每個端點錯誤率；黑箱監控的例子是 Gatus 或 blackbox_exporter 定期打一條測試短網址、檢查回應是 `302` 而且 `Location` 指向預期的網址。主機磁碟寫滿時，白箱的磁碟用量先升高；黑箱要等寫滿之後某一個需要寫入的請求失敗才看得到，只打轉址的探測可能一直成功。入口的 TLS 憑證過期時，白箱的數字只剩請求率下降、沒有一個越過門檻，只有走公開網址的黑箱探測失敗。

## 判讀方式

看到一個監控時，先問它是讀內部狀態還是看外部行為，再問它站在哪裡。名字帶 blackbox 的工具跑在服務主機上，是黑箱、但不在失效域以外；雲端業者從虛擬化層讀的指標是白箱、而位置在主機以外。監控分層裡各層各屬哪一種、各自的盲區由誰接手，見 [4.0 服務端監控的分層](/backend/04-observability/monitoring-layers/)；黑箱探測放到失效域以外的做法見 [4.28 單台主機的監控盲區與失效域以外的觀察者](/backend/04-observability/single-host-monitoring-outside-view/)。
