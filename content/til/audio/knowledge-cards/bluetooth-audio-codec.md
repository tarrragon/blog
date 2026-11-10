---
title: "Bluetooth Audio Codec（藍牙的音訊編碼格式）"
slug: "bluetooth-audio-codec"
date: 2026-11-11
description: "用 iPhone 或 Android 手機接藍牙耳機、藍牙喇叭，或用唱盤的藍牙輸出時讀到 SBC、AAC、aptX、LDAC，要判斷實際用的是哪一種格式、音質與延遲各受什麼影響時"
weight: 18
tags: ["til", "音響", "knowledge-cards"]
---

藍牙傳音訊時，傳送端（手機、電腦）先把聲音用一種音訊編碼格式（codec）壓縮，再經由無線電送出；接收端（耳機、喇叭）收到之後解碼，交給內建的 [DAC](/til/audio/knowledge-cards/dac/) 與擴大電路。實際使用的格式由兩端共同決定：傳送端與接收端都支援的格式才會被使用，兩邊除了 SBC 沒有其他共同支援的格式時，退回到所有藍牙音訊設備都支援的 SBC。

## 概念位置

藍牙的編碼是訊號從手機到耳機或喇叭這一段的壓縮，跟音樂檔或串流服務本身的壓縮是兩次不同的編碼：串流服務送來的有損音樂在手機上解碼成 PCM，再經過一次藍牙的有損（lossy）編碼，兩次編碼的失真疊加。格式之間的差別以位元率（bitrate，每秒傳送的資料量）描述：同一種格式裡，位元率越高，壓縮時丟掉的資訊越少；不同格式的編碼效率不同，位元率只在同一種格式之內比得出高低。位元率跟檔案的[取樣率與位元深度](/til/audio/knowledge-cards/sample-rate-and-bit-depth/)是不同的量：Hi-Res 檔案經過藍牙時同樣要重新編碼，耳機收到什麼由藍牙格式的位元率決定，檔案的取樣率與位元深度不再決定它。

不經過藍牙編碼的做法是手機用線接 DAC，或改用 Wi-Fi 串流協定。

## 可觀察訊號與例子

- **SBC**：藍牙音訊的基本格式，最高位元率約 328 kbps，多數設備設定在較低的位元率等級，音質依實作而不同。
- **AAC**：Apple 設備主要使用的格式，藍牙上約 256 kbps；Android 手機的 AAC 編碼品質依手機而不同。
- **aptX 系列**（Qualcomm）：aptX 約 352 到 384 kbps，aptX HD 約 576 kbps，aptX Adaptive 依無線環境調整位元率，部分設備支援 aptX Lossless。
- **LDAC**（Sony）：最高約 990 kbps，實際使用時多在 330 到 660 kbps 之間依連線狀況自動調整，訊號不穩時降到低位元率。
- **[LHDC](/til/audio/knowledge-cards/lhdc/)**（Savitech）：跟 LDAC 同一類的高位元率格式，主要在部分 Android 品牌的手機上。
- **LC3**：[LE Audio](/til/audio/knowledge-cards/le-audio-lc3/) 的必備格式，走低功耗藍牙這一條傳輸，跟上面幾種傳統藍牙的格式是兩套並存的系統。

iPhone 與 iPad 只支援 SBC 與 AAC（2026 年），接標榜 aptX 或 LDAC 的喇叭或耳機時，接收端也支援 AAC 就以 AAC 播放，不支援就用 SBC。Android 手機實際用的格式，可以在「開發人員選項」的藍牙音訊編解碼器看到。部分入門唱盤有藍牙輸出，唱盤的類比訊號經過內建的[唱頭放大器](/til/audio/knowledge-cards/phono-preamp/)之後，同樣要經過一次藍牙的有損編碼。

## 判讀方式

一組藍牙設備實際用到的位元率由兩項決定：兩端共同支援的格式決定上限，連線狀況決定實際用到多少。聽到的音質另外受編碼器的實作（SBC 與 Android 的 AAC 依設備而不同）、串流本身的有損編碼、耳機內部的等化與降噪，以及藍牙喇叭本身的單體、箱體與 DSP 限制器影響；小型藍牙喇叭的低頻延伸，與大音量時把低音壓下來的限制器，都跟編碼格式無關。

位元率與聽感的對應來自有損編碼器的盲聽測試（[ABX](/til/audio/knowledge-cards/abx-test/) 或 ITU-R BS.1116 這類方法，音量對齊）。AAC 256 kbps 這個等級，未受訓練的聽者在多數音樂上分不出跟無損的差別；[受過訓練的聽者](/til/audio/knowledge-cards/trained-listener/)在少數難編碼的片段（打擊樂器的瞬間、高頻密集的樂器）上有機會分得出來。aptX 與 LDAC 沒有在同樣條件下跟 AAC 256 kbps 對照的盲聽結果；它們的位元率較高，而位元率只在同一種格式之內比得出高低，所以位元率較高不能當成聽感一樣好或更好的證據。SBC 的低位元率設定，以及訊號不穩時自動降下來的位元率，失真較容易聽出來。規格表上的最高位元率是連線良好時的上限，LDAC 在實際使用時多以較低的等級運作。

延遲（latency）是另一項跟格式有關的性質：從手機送出到喇叭發聲多在一百到兩百毫秒或更長，看影片時聲音與嘴型對不上；部分格式與設備有低延遲模式，電視與擴大機的影音延遲設定也可以讓聲音跟畫面對齊。

各格式的位元率與手機的支援在〔[數位訊源的構造與選擇](/til/audio/digital-streaming-source-guide/)〕的〈藍牙的音訊編碼格式：SBC、AAC、aptX、LDAC、LHDC、LE Audio 與手機的支援〉；盲聽測試的條件在同一篇的〈有損與無損壓縮〉；不經過藍牙編碼的 Wi-Fi 串流協定在同一篇的〈Wi-Fi 串流協定〉；電視的影音延遲設定在同一篇的〈有線介面：USB、光纖、同軸與 HDMI ARC〉；藍牙喇叭的單體與限制器在〔[喇叭的規格與構造](/til/audio/speaker-components-and-upgrade-path/)〕的〈各種配置的適用條件：多媒體、近場、書架、超低音（2.1）、落地、多顆超低音與多聲道〉；無線耳機的編碼、降噪與內建等化在〔[耳機與耳機擴大機](/til/audio/headphones-and-headphone-amplifiers/)〕的〈無線耳機：編碼、主動降噪與內建等化〉。
