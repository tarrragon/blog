---
title: "家用音響的知識卡片"
slug: "knowledge-cards"
date: 2026-11-11
description: "讀家用音響各篇、規格表或評測時碰到 dB、音壓、阻抗、頻率響應、靈敏度、分音器、駐波、接地迴路這類術語，要查它的定義、在訊號流程裡的位置與判讀方式時"
weight: 9
tags: ["til", "音響", "knowledge-cards"]
---

這個資料夾收錄家用音響各篇反覆用到的術語，一張卡一個術語：定義、它在訊號流程或聆聽環境裡的位置、什麼情形下它成為判讀重點，以及常見的誤判。各篇文章在術語第一次出現的位置連到卡，之後裸用；完整的換算與推導留在 [家用音響的基礎概念](/til/audio/audio-fundamentals/) 與各設備的文章，卡片連過去當深讀。

## 卡片索引

### 量與單位

| 卡片                                                                                  | 核心內容                                                                                     |
| ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| [Decibel（分貝，dB）](/til/audio/knowledge-cards/decibel/)                            | 兩個量的比值取對數：功率比與電壓比的換算差一倍係數                                           |
| [Sound Pressure Level（音壓，SPL）](/til/audio/knowledge-cards/sound-pressure-level/) | 以聽覺門檻為參考值的絕對音量，喇叭規格與聆聽音量都用它                                       |
| [Noise Floor（底噪）](/til/audio/knowledge-cards/noise-floor/)                        | 設備沒有訊號時的輸出雜訊，以及房間的環境聲；設備的雜訊換算成聆聽位置的音壓之後才能跟環境聲比 |
| [Frequency Response（頻率響應）](/til/audio/knowledge-cards/frequency-response/)      | 輸出音量隨頻率變化的曲線，讀法依電子設備、喇叭、房間與耳機而不同                             |
| [Phase（相位）](/til/audio/knowledge-cards/phase/)                                    | 波形在一個週期裡走到的位置，以角度計；兩個同頻率的波之間的相位差決定疊加時加強還是抵消       |
| [Resonance（共振）](/til/audio/knowledge-cards/resonance/)                            | 彈簧加質量的系統在某個頻率反應特別大，阻尼決定峰值多尖                                       |

### 設備之間的搭配

| 卡片                                                                         | 核心內容                                                         |
| ---------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| [Load Impedance（負載阻抗）](/til/audio/knowledge-cards/load-impedance/)     | 下一級設備對訊號呈現的阻抗，決定上一級要供多少電流               |
| [Output Impedance（輸出阻抗）](/til/audio/knowledge-cards/output-impedance/) | 訊號源內部的阻抗，跟負載阻抗的比值決定負載端拿到的電壓與頻率響應 |
| [Sensitivity（靈敏度）](/til/audio/knowledge-cards/sensitivity/)             | 喇叭或耳機在固定輸入下發出的音壓，決定要多少功率或電壓           |
| [Line Level（線路電平）](/til/audio/knowledge-cards/line-level/)             | 訊源與前級之間約定的訊號電壓範圍，唱頭與喇叭的訊號都不在這個範圍 |
| [DAC（數位類比轉換器）](/til/audio/knowledge-cards/dac/)                     | 把數位音訊的取樣值轉成類比電壓的元件，內建在多數播放設備裡       |
| [Clock Jitter（時脈抖動）](/til/audio/knowledge-cards/clock-jitter/)         | 數位音訊的取樣時間點偏離理想時刻的量，轉成類比時變成失真         |
| [Crossover（分音器）](/til/audio/knowledge-cards/crossover/)                 | 把全頻訊號依頻率分給不同單體的電路或 DSP，分頻點與斜率是它的規格 |
| [Ground Loop（接地迴路）](/til/audio/knowledge-cards/ground-loop/)           | 兩台設備經由兩條接地路徑相連時形成的迴路，產生交流電頻率的嗡聲   |

### 房間與聽感比較

| 卡片                                                         | 核心內容                                                         |
| ------------------------------------------------------------ | ---------------------------------------------------------------- |
| [Room Modes（駐波）](/til/audio/knowledge-cards/room-modes/) | 房間尺寸決定的低頻共振，讓聆聽位置的低音在某些頻率特別多或特別少 |
| [ABX Test（ABX 測試）](/til/audio/knowledge-cards/abx-test/) | 音量對齊之後隨機播放、讓聽者判斷 X 是 A 還是 B 的盲聽方法        |
