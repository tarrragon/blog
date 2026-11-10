---
title: "家用音響的知識卡片"
slug: "knowledge-cards"
date: 2026-11-11
description: "讀家用音響各篇、規格表或評測時碰到 dB、音壓、阻抗、頻率響應、靈敏度、取樣率、藍牙編碼、LHDC、LE Audio、D 類、數位擴大機、USB-C 供電、指向性、駐波、SBIR、唱頭、唱頭殼、循軌力、受過訓練的聽者這類術語，要查它的定義、在訊號流程裡的位置與判讀方式時"
weight: 9
tags: ["til", "音響", "knowledge-cards"]
---

這個資料夾收錄家用音響各篇反覆用到的術語，一張卡一個術語，或一組成對使用的術語：定義、它在訊號流程或聆聽環境裡的位置、什麼情形下它成為判讀重點、判斷的條件，以及名字相近的概念各自指什麼。各篇文章在術語第一次出現的位置連到卡，之後裸用；完整的換算與推導留在 [家用音響的基礎概念](/til/audio/audio-fundamentals/) 與各設備的文章，卡片連過去當深讀。

## 卡片索引

### 量與單位

| 卡片                                                                                                   | 核心內容                                                                                     |
| ------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| [Decibel（分貝，dB）](/til/audio/knowledge-cards/decibel/)                                             | 兩個量的比值取對數：功率比與電壓比的換算差一倍係數                                           |
| [Sound Pressure Level（音壓，SPL）](/til/audio/knowledge-cards/sound-pressure-level/)                  | 以聽覺門檻為參考值的絕對音量，喇叭規格與聆聽音量都用它                                       |
| [Noise Floor（底噪）](/til/audio/knowledge-cards/noise-floor/)                                         | 設備沒有訊號時的輸出雜訊，以及房間的環境聲；設備的雜訊換算成聆聽位置的音壓之後才能跟環境聲比 |
| [Frequency Response（頻率響應）](/til/audio/knowledge-cards/frequency-response/)                       | 輸出音量隨頻率變化的曲線，讀法依電子設備、喇叭、房間與耳機而不同                             |
| [Phase（相位）](/til/audio/knowledge-cards/phase/)                                                     | 波形在一個週期裡走到的位置，以角度計；兩個同頻率的波之間的相位差決定疊加時加強還是抵消       |
| [Resonance（共振）](/til/audio/knowledge-cards/resonance/)                                             | 彈簧加質量的系統在某個頻率反應特別大，阻尼決定峰值多尖                                       |
| [Sample Rate and Bit Depth（取樣率與位元深度）](/til/audio/knowledge-cards/sample-rate-and-bit-depth/) | PCM 每秒量幾次與每個值用幾個位元記錄，分別限制能記錄的最高頻率與動態範圍                     |

### 設備之間的搭配

| 卡片                                                                                             | 核心內容                                                                                       |
| ------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------- |
| [Load Impedance（負載阻抗）](/til/audio/knowledge-cards/load-impedance/)                         | 下一級設備對訊號呈現的阻抗，決定上一級要供多少電流                                             |
| [Output Impedance（輸出阻抗）](/til/audio/knowledge-cards/output-impedance/)                     | 訊號源內部的阻抗，跟負載阻抗的比值決定負載端拿到的電壓與頻率響應                               |
| [Sensitivity（靈敏度）](/til/audio/knowledge-cards/sensitivity/)                                 | 喇叭或耳機在固定輸入下發出的音壓，決定要多少功率或電壓                                         |
| [Line Level（線路電平）](/til/audio/knowledge-cards/line-level/)                                 | 訊源與前級之間約定的訊號電壓範圍，唱頭與喇叭的訊號都不在這個範圍                               |
| [DAC（數位類比轉換器）](/til/audio/knowledge-cards/dac/)                                         | 把數位音訊的取樣值轉成類比電壓的元件，內建在多數播放設備裡                                     |
| [Clock Jitter（時脈抖動）](/til/audio/knowledge-cards/clock-jitter/)                             | 數位音訊的取樣時間點偏離理想時刻的量，轉成類比時變成失真                                       |
| [Ground Loop（接地迴路）](/til/audio/knowledge-cards/ground-loop/)                               | 兩台設備經由兩條接地路徑相連時形成的迴路，產生交流電頻率的嗡聲                                 |
| [Bluetooth Audio Codec（藍牙的音訊編碼格式）](/til/audio/knowledge-cards/bluetooth-audio-codec/) | 藍牙傳送端壓縮、接收端解碼的格式，兩端共同支援的才會被使用，同一種格式裡位元率決定丟掉多少資訊 |
| [LHDC（藍牙高解析編碼格式）](/til/audio/knowledge-cards/lhdc/)                                   | Savitech 開發、跟 LDAC 同類的高位元率藍牙格式，兩端都支援才用得到，iPhone 不支援               |
| [LE Audio and LC3（低功耗藍牙音訊與 LC3 編碼）](/til/audio/knowledge-cards/le-audio-lc3/)        | 低功耗藍牙上的音訊架構與它的必備格式 LC3，跟傳統藍牙的格式並存，另有一對多的 Auracast 廣播     |
| [USB-C Power Delivery（USB-C PD 供電）](/til/audio/knowledge-cards/usb-c-power-delivery/)        | USB-C 供電時兩端協商一檔固定電壓，協商到的電壓與充電器的瓦數決定擴大機的輸出上限               |

### 擴大機與喇叭的構造

| 卡片                                                                                  | 核心內容                                                                                                 |
| ------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| [Class D Amplifier（D 類擴大機）](/til/audio/knowledge-cards/class-d-amplifier/)      | 輸出級以高速開關工作的擴大機，特有的是輸出濾波器與負載的互動；外接電源的小型機另有供電電壓限制的輸出上限 |
| [Digital Amplifier（數位擴大機）](/til/audio/knowledge-cards/digital-amplifier/)      | D 類擴大機的俗稱；「數位」可能指 D 類的輸出級或數位輸入，兩件事分開查，放大過程本身是類比的              |
| [Filterless Class D（無濾波器 D 類）](/til/audio/knowledge-cards/filterless-class-d/) | 不接輸出濾波器、靠喇叭音圈的電感濾掉開關雜訊的 D 類，要求喇叭線短                                        |
| [Crossover（分音器）](/til/audio/knowledge-cards/crossover/)                          | 把全頻訊號依頻率分給不同單體的電路或 DSP，分頻點與斜率是它的規格                                         |
| [Directivity（指向性）](/til/audio/knowledge-cards/directivity/)                      | 喇叭的聲音集中往正前方的程度，隨頻率收窄，決定喇叭往牆面送出的聲音量與音色                               |

### 唱盤

| 卡片                                                                                                           | 核心內容                                                                                       |
| -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| [MM and MC Cartridges（動磁式與動圈式唱頭）](/til/audio/knowledge-cards/mm-and-mc-cartridges/)                 | 依跟著針桿動的是磁鐵還是線圈分成兩種唱頭，輸出電壓、增益、負載與換針方式不同                   |
| [Effective Mass and Compliance（有效質量與順服度）](/til/audio/knowledge-cards/effective-mass-and-compliance/) | 唱臂折算到唱針的質量加上唱頭的重量，與唱頭針桿的軟硬，決定唱臂與唱頭的共振頻率                 |
| [Moving Iron Cartridge（動鐵式唱頭，MI）](/til/audio/knowledge-cards/moving-iron-cartridge/)                   | 針桿只帶一小塊鐵片、磁鐵與線圈都固定的唱頭，輸出電壓依型號落在 MC 到 MM 的範圍，接法看輸出電壓 |
| [Headshell（唱頭殼）](/til/audio/knowledge-cards/headshell/)                                                   | S 臂、J 臂前端可拆的唱頭固定件，重量算進唱臂與唱頭共振的總質量                                 |
| [Tracking Force（循軌力）](/til/audio/knowledge-cards/tracking-force/)                                         | 唱針壓在溝槽上的力，以公克計，太輕時在溝槽裡跳動而失真、太重時加快磨耗                         |

### 房間與聽感比較

| 卡片                                                                               | 核心內容                                                                         |
| ---------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| [Room Modes（駐波）](/til/audio/knowledge-cards/room-modes/)                       | 房間尺寸決定的低頻共振，讓聆聽位置的低音在某些頻率特別多或特別少                 |
| [SBIR（喇叭與邊界的干涉）](/til/audio/knowledge-cards/sbir/)                       | 喇叭後方牆面的反射跟直達聲反相抵消，凹陷的頻率由喇叭到後牆的距離決定             |
| [ABX Test（ABX 測試）](/til/audio/knowledge-cards/abx-test/)                       | 音量對齊之後隨機播放、讓聽者判斷 X 是 A 還是 B 的盲聽方法                        |
| [Trained Listener（受過訓練的聽者）](/til/audio/knowledge-cards/trained-listener/) | 經過系統的聽音訓練、能穩定辨認聲音缺陷的聽者；盲聽結論常分這一組與未受訓練的一組 |
