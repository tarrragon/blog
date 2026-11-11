---
title: "LHDC（藍牙高解析編碼格式）"
slug: "lhdc"
date: 2026-11-11
description: "在 Android 手機的開發人員選項、藍牙耳機規格或 Hi-Res Wireless 標章上看到 LHDC，要判斷手機與耳機用不用得到它、跟 LDAC 與 AAC 怎麼比時"
weight: 27
tags: ["til", "音響", "knowledge-cards"]
---

LHDC（Low latency High-Definition audio Codec）是台灣的音訊晶片公司 Savitech 開發的[藍牙音訊編碼格式](/til/audio/knowledge-cards/bluetooth-audio-codec/)，跟 LDAC 屬於同一類：用比 SBC、AAC 高的位元率傳送，主打高解析音訊。依公開的規格整理，位元率的範圍約 160 到 1000 kbps；第 3、4 版的上限約 900 kbps，第 5 版約 1000 kbps；第 5 版宣稱支援 24 位元、192 kHz。

## 跟其他概念的關係

LHDC 跟其他藍牙格式一樣，要傳送端與接收端都支援才會被使用，兩端沒有共同支援時退回 AAC 或 SBC。支援它的主要是部分 Android 手機品牌（第一支支援的手機是 2017 年的 Huawei Mate 10，之後有 OPPO、OnePlus、Xiaomi、Nothing 的部分機型）；iPhone 不支援（2026 年）。LDAC 從 Android 8.0 起就是 Android 原生支援的格式；LHDC 到 2026 年的 Android 17 才在 Pixel 的開發人員選項以 LHDC v5 出現（依 Android Authority 等媒體的報導）。在這之前與其他品牌的手機上，支援與否取決於那個品牌有沒有自己把它加進系統。

它宣稱的 24 位元、192 kHz 描述的是編碼器接受的格式；耳機收到多少資訊，仍由實際傳送的位元率決定，跟檔案的[取樣率與位元深度](/til/audio/knowledge-cards/sample-rate-and-bit-depth/)是兩回事。

## 可觀察訊號與例子

- Android 手機的「開發人員選項」→ 藍牙音訊編解碼器裡列出 LHDC，代表手機支援；實際用的是哪一種，要在連上耳機之後看同一個選項。
- 耳機或喇叭的包裝印有 Hi-Res Audio Wireless 標章，常見的對應格式是 LDAC 或 LHDC，aptX Adaptive、LC3plus 等格式也通過了這個標章的認證。
- Nothing 的手機預設開啟 LHDC（官方說明），其他品牌多半要在藍牙設定裡手動選。

## 判斷條件與後果

判斷一組設備值不值得為 LHDC 挑選，先確認兩端都支援：手機是 iPhone、或手機品牌沒有把 LHDC 加進系統時，耳機標榜 LHDC 也用不到。兩端都支援之後，LHDC 跟 LDAC 一樣，位元率只在同一種格式之內比得出高低，沒有在同樣條件下跟 AAC 256 kbps 對照的盲聽結果，所以較高的位元率不能當成聽感更好的證據。連線不穩時，高位元率的格式會降到較低的等級。

藍牙格式的選擇規則與各格式的位元率在〔[數位訊源的構造與選擇](/til/audio/digital-streaming-source-guide/)〕的〈藍牙的音訊編碼格式：SBC、AAC、aptX、LDAC、LHDC、LE Audio 與手機的支援〉；有損格式的盲聽結果在同一篇的〈有損與無損壓縮〉。
