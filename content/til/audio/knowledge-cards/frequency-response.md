---
title: "Frequency Response（頻率響應）"
slug: "frequency-response"
date: 2026-11-11
description: "讀 DAC、擴大機、喇叭或耳機的頻率響應規格與量測曲線，要分辨整體傾斜、峰與谷、衰減點各代表什麼，以及不同設備的曲線該照什麼標準讀時"
weight: 4
tags: ["til", "音響", "knowledge-cards"]
---

比較兩台設備的音色平衡、判斷一台設備改變了哪些頻段的音量時，看的是它的頻率響應（frequency response）：設備在各頻率的輸出大小畫成的一條曲線，橫軸是頻率（對數刻度，20 Hz 到 20 kHz，每個八度（octave：頻率加倍）佔同樣的寬度），縱軸是音量（[dB](/til/audio/knowledge-cards/decibel/)）。規格表常寫成「20 Hz–20 kHz ±0.5 dB」，意思是在這個範圍內，曲線上下偏離不超過 0.5 dB。

## 概念位置

頻率響應是描述電子設備的三項規格之一，另外兩項是[總諧波失真加雜訊](/til/audio/knowledge-cards/thd-n/)（THD+N，total harmonic distortion plus noise）與訊噪比（SNR）。同一個名詞套在不同設備上，理想的曲線形狀不同：

- **電子設備**（DAC、擴大機）：理想的曲線是一條水平線，代表每個頻率經過設備之後的比例不變；實際的偏離以零點幾 dB 計。
- **喇叭**：起伏以幾 dB 計，還分正前方（軸向）與各角度（[離軸](/til/audio/knowledge-cards/directivity/)）的多條曲線。
- **房間**：在聆聽位置量到的曲線，低頻常有 10 dB 以上的起伏，成因是 [駐波](/til/audio/knowledge-cards/room-modes/)。
- **耳機**：用人工耳（ear simulator）量耳膜位置的聲音；人的耳廓與耳道本身會放大 2 到 5 kHz，所以耳機的目標曲線在那一段有突起。

設備之間的接法也會改變頻率響應：擴大機或耳擴的 [輸出阻抗](/til/audio/knowledge-cards/output-impedance/) 高、而喇叭或耳機的 [負載阻抗](/til/audio/knowledge-cards/load-impedance/) 隨頻率變化時，頻率響應會跟著阻抗曲線起伏。

## 可觀察訊號與例子

- 輸出阻抗 1 Ω 到 3 Ω 以上的真空管擴大機接同一顆喇叭，頻率響應依阻抗曲線起伏約 2 dB 到 5 dB：阻抗高的低音共振處變大聲、阻抗低的頻段變小聲。
- Harman 目標曲線（Harman target curve）是 Sean Olive 與 Todd Welti 用盲聽研究得出、多數聽者偏好的耳機頻率響應：低頻比中頻高，耳罩式約高 4 到 6 dB，入耳式約高 8 到 10 dB。
- 現代的 DAC 與固態擴大機，第三方量測裡多數達到[辨識門檻](/til/audio/knowledge-cards/audibility-threshold/)的頻率響應：可聽範圍兩端的衰減在正負 0.5 dB 以內。

## 判讀方式

讀一條曲線看三件事：

- **整體的傾斜**（tilt）：曲線從低頻往高頻緩緩下降或上升，聽起來整體偏暖或偏亮。中段（約 100 Hz 到 10 kHz）的寬頻傾斜在零點幾 dB 就會影響比較時的偏好，一兩 dB 時多數人聽得出來。
- **局部的峰與谷**（peak、dip）：某一段突起幾 dB，那一段的聲音特別突出；窄而深的谷比同樣深的峰較難聽出來。
- **兩端的衰減點**：常用比中段低 3 dB 或 6 dB 的頻率標示（−3 dB 點、−6 dB 點），就是頻寬的上下限。

量測條件也要對上：不同的人工耳或量測方法得出的耳機曲線不完全相同，[D 類擴大機](/til/audio/knowledge-cards/class-d-amplifier/)在電阻負載與模擬喇叭負載下的高頻響應可能不同，所以比較兩條曲線時，只比同一個量測者用同一套設備與負載量的結果。

曲線的讀法與各設備的曲線在〔[家用音響的基礎概念](/til/audio/audio-fundamentals/)〕的〈頻率響應與量測圖的讀法〉；喇叭的軸向與離軸曲線在〔[喇叭的規格與構造](/til/audio/speaker-components-and-upgrade-path/)〕的〈挑喇叭時看的量測規格：軸向頻率響應、離軸頻率響應、頻寬與靈敏度〉；耳機在〔[耳機與耳機擴大機](/til/audio/headphones-and-headphone-amplifiers/)〕的〈耳機的頻率響應與目標曲線〉。
