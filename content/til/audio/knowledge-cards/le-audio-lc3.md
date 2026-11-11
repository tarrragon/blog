---
title: "LE Audio and LC3（低功耗藍牙音訊與 LC3 編碼）"
slug: "le-audio-lc3"
date: 2026-11-11
description: "在新手機、耳機、助聽器或公共場所的廣播標示上看到 LE Audio、LC3 或 Auracast，要判斷它跟傳統藍牙音訊與 SBC、AAC 差在哪裡、自己的設備用不用得到時"
weight: 28
tags: ["til", "音響", "knowledge-cards"]
---

LE Audio 是藍牙在低功耗藍牙（Bluetooth Low Energy）上重新設計的一套音訊架構，跟耳機過去一直用的傳統藍牙音訊（Classic Bluetooth 的 A2DP）是兩條不同的傳輸方式。它的核心傳輸功能放進藍牙核心規格 5.2，整套音訊規格在 2022 年完成。LC3（Low Complexity Communication Codec）是 LE Audio 規定每一台設備都要支援的[藍牙音訊編碼格式](/til/audio/knowledge-cards/bluetooth-audio-codec/)，角色相當於傳統藍牙音訊裡的 SBC。

## 跟其他概念的關係

LE Audio 改變的有兩層。編碼層：LC3 在較低的位元率達到跟 SBC 相近的聽感，常被引用的例子是 LC3 約 160 kbps 的立體聲對照 SBC 約 345 kbps（藍牙技術聯盟引用的聽感測試）；LC3 的位元率可以在一個範圍內依需要選，160 kbps 是常見的設定，不是固定值。傳輸層：同一個來源可以一次送給多副耳機，叫 Auracast 廣播，用在機場、健身房的電視音訊與助聽器。

它跟傳統藍牙的格式（SBC、AAC、aptX、LDAC）是兩套並存的系統：耳機與手機都支援 LE Audio 時才走這一條，否則照舊用傳統藍牙，格式照兩端共同支援的那一種選（AAC、aptX、LDAC 這類，沒有共同支援的格式時才是 SBC），跟[取樣率與位元深度](/til/audio/knowledge-cards/sample-rate-and-bit-depth/)描述的檔案格式無關。

## 可觀察訊號與例子

- 手機或耳機的規格寫「LE Audio」「LC3」「Auracast」；藍牙設定裡出現「LE 音訊」的開關。
- LE Audio 把助聽器列為主要用途之一，新的助聽器與部分真無線耳機開始支援它，因為低功耗的傳輸讓同一顆電池的使用時間較長；多數真無線耳機的預設連線仍是傳統藍牙（2026 年）。
- 公共場所標示 Auracast 的廣播頻道，支援的耳機可以直接收聽，不必一對一配對。

## 判斷條件與後果

判斷 LE Audio 對自己有沒有用，先看兩端是否都支援：手機、耳機或電視只要有一端只有傳統藍牙，就用不到 LC3 與 Auracast。兩端都支援時，LC3 換到的是在較低位元率下維持音質，對連線穩定度與耗電有利；它跟 LDAC、LHDC 這類高位元率格式的設計目標不同，位元率也只在同一種格式之內比得出高低，兩者沒有在同樣條件下的盲聽對照。想收聽公共場所的 Auracast 廣播，耳機要支援 Auracast 接收，這一項跟音質無關。

藍牙格式的選擇規則與延遲在〔[數位訊源的構造與選擇](/til/audio/digital-streaming-source-guide/)〕的〈藍牙的音訊編碼格式：SBC、AAC、aptX、LDAC、LHDC、LE Audio 與手機的支援〉；無線耳機的連線與內建處理在〔[耳機與耳機擴大機](/til/audio/headphones-and-headphone-amplifiers/)〕的〈無線耳機：編碼、主動降噪與內建等化〉。
