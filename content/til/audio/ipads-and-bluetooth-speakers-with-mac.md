---
title: "用 iPad 與藍牙喇叭擴充 Mac 的聆聽配置：Airfoil 把 iPad 當成 Mac 的喇叭、iPad 經由 AirPlay 或 USB 把聲音送進 Mac，以及各台 iPad 獨立播放"
slug: "ipads-and-bluetooth-speakers-with-mac"
date: 2026-11-12
weight: 11
description: "手上有一台 Mac、幾台 iPad 與藍牙喇叭，想讓 iPad 也加入家裡的播放，或把 iPad 上 App 的聲音交給 Mac 接的喇叭播放時，查 iPad 為什麼進不了 macOS 的多重輸出裝置、Airfoil 與 Airfoil Satellite 怎麼讓各台裝置同步播放、Mac 的 AirPlay 接收器與 USB 音訊輸入怎麼收 iPad 的聲音，以及各台 iPad 獨立播放適合的條件"
tags: ["til", "音響", "macOS", "iPad", "Airfoil", "AirPlay", "藍牙"]
---

這篇寫手上有一台 Mac、幾台 iPad 與藍牙喇叭時，把 iPad 加進聆聽配置的做法：iPad 不在 macOS 的輸出清單裡、進不了多重輸出裝置的原因；用第三方軟體 Airfoil 與 Airfoil Satellite 把 iPad 當成 Mac 的喇叭，它怎麼讓 Mac、iPad 與藍牙喇叭同步發聲、付出什麼；反方向把 iPad 上 App 的聲音送進 Mac，分成經由 Wi-Fi 的 AirPlay 接收器與經由傳輸線的 USB 音訊輸入；不經過 Mac、各台 iPad 各自播放（藍牙喇叭配給其中一台）適合的條件；最後是依「要不要同步」「聲音從哪一台出發」選做法的條件。macOS 內建的多重輸出裝置（建立步驟、主要裝置、偏移修正、延遲差造成的回音）在〔[macOS 的多重輸出裝置](/til/audio/macos-multi-output-device/)〕，本篇沿用那一篇的延遲與回音的說明。本篇的功能與步驟取自 Rogue Amoeba 與 Apple 的官方文件，介面文字取自 macOS 15.3.1 的繁體中文介面；寫作時沒有在 iPad 上實跑，每一處沒有實測的地方都標明。各軟體的版本、價格與支援的系統會改變，以官方頁面為準。

## iPad 不在 macOS 輸出清單裡的原因：iPadOS 沒有 AirPlay 接收器

macOS 的多重輸出裝置只能加入 Mac 的輸出清單裡看得到的裝置：有線連接的裝置、配對連線的藍牙裝置，以及 AirPlay 接收端（Apple TV、HomePod、支援 AirPlay 的電視與喇叭、開了接收器的另一台 Mac）。Mac 用 AirPlay 送聲音給另一台裝置，前提是那台裝置在執行 AirPlay 的接收端。Apple 的〈Continuity features and requirements for Apple devices〉（支援文件 108046）列出的 AirPlay 接收端裡，Mac 從 macOS Monterey 起可以接收，iPad 不在其中；iPadOS 只有送出 AirPlay 的功能。

所以 iPad 要接收 Mac 的聲音，需要在 iPad 上另外執行一個接收端的 App，Mac 上也要有對應的送出端。這種 App 送的是它自己的串流格式，不經過 macOS 的輸出清單，多重輸出裝置看不到它；同步與音量由那一組軟體自己處理。

## 把 iPad 當成 Mac 的喇叭：Airfoil 與 Airfoil Satellite

Airfoil 是 Rogue Amoeba 出的 Mac 軟體，作用是把 Mac 上的聲音同時送到多個輸出，並讓它們同步播放。它送得到的輸出有 AirPlay 裝置、Google Cast 裝置、Sonos、跟 Mac 配對的藍牙裝置，以及執行 Airfoil Satellite 的電腦與行動裝置（Airfoil 手冊〈Supported Outputs〉）。Airfoil Satellite 有 Mac、Windows、iOS（含 iPad）、Android 與 Apple TV 的版本，官方頁面寫它是「Airfoil 的音訊接收端與遙控器」，iOS 版免費下載、要求 iOS 11.1 以上。所以在每台 iPad 上裝 Airfoil Satellite，iPad 就成了 Airfoil 清單裡的一個輸出，跟藍牙喇叭、Mac 自己的喇叭並列。

### 同步的方式：每一台都延後到跟最慢的那一台一致

Airfoil 跟多重輸出裝置的差別在延遲的處理。〔[macOS 的多重輸出裝置](/til/audio/macos-multi-output-device/)〕的〈各裝置的延遲不同〉寫過：多重輸出裝置把同一份聲音同時交給每個裝置，藍牙喇叭比有線裝置晚一百多毫秒，兩台都聽得到的位置會聽到回音。Airfoil 的手冊寫的是它「把所有輸出保持同步，把聲音延後，讓每一台都配合延遲最大的那一台」（〈Advanced Features〉）。延遲小的裝置被刻意延後，到達聆聽位置的時間跟延遲最大的那一台相同，回音就不會出現。

Mac 自己的喇叭也能加入同步：Airfoil 的輸出清單最上面固定有一項「Computer」，手冊寫它讓 Mac 在本機播放、跟遠端的喇叭同步（〈Using Airfoil〉）。在多重輸出裝置裡延遲對不齊的內建揚聲器加藍牙喇叭，在 Airfoil 裡改成 Computer 加藍牙喇叭兩個輸出，就會被對齊。

這個做法的代價是整套系統的延遲等於最慢的那一台。官方頁面沒有寫延遲的數值，也沒有寫哪一類輸出（AirPlay、藍牙、Satellite）最慢。只放音樂時，按下播放到聲音出來多等一下，聽的人感覺不到差別；邊看影片邊用 Airfoil 送聲音時，聲音被延後而畫面沒有，嘴型會對不上（這一項是由「延後到最慢的那一台」推論的，沒有實測）。手冊另外有每個輸出的「Sync」滑桿（在 Speakers 選單的 Advanced Speaker Options），用途是輸出接到的接收器自己又加了延遲時，讓 Airfoil 少延後一點；手冊強調多數人不需要調它，建議維持預設位置。

### 設定 Airfoil 的步驟

下面的步驟依 Airfoil 的官方手冊整理，本篇沒有實跑。每一步寫出它為什麼在這個位置，以及略過或做錯時的結果。

1. **在 Mac 安裝 Airfoil**：官方頁面寫的系統需求是 macOS 14.4 以上。同一個下載檔就是試用版與完整版，試用期間「傳送十分鐘之後音質會被降低」（手冊〈Purchasing Airfoil〉），所以試用時只能確認能不能連上、同不同步，長時間聆聽要購買授權；價格在官方的購買頁（`https://rogueamoeba.com/airfoil/mac/buy.php`）。第一次開啟時，macOS 會要求授與「系統音訊存取」權限，手冊寫這是 Airfoil 運作必需的；不授與時抓不到 Mac 上的聲音。
2. **在每台 iPad 安裝 Airfoil Satellite，並連上跟 Mac 相同的 Wi-Fi**：Airfoil 在區域網路上找 Satellite，iPad 與 Mac 不在同一個網路時，iPad 不會出現在 Airfoil 的輸出清單裡。Satellite 要在 iPad 上開著才收得到聲音；iPad 鎖定或切到別的 App 之後是否繼續接收，官方頁面沒有寫，本篇也沒有實測。
3. **在 Airfoil 視窗上方的「Source」選單選聲音來源**：手冊寫 Airfoil 可以只送某一個 App 的聲音，不必送出 Mac 的全部聲音；也可以選 USB 收音機、麥克風這類輸入裝置。只送音樂 App 時，系統的提示音與其他 App 的聲音留在 Mac 本機，不會在每個房間的 iPad 上響起；選系統全部的聲音時，連提示音也會送到每一台。
4. **對要用的每個輸出按「Transmit」**：iPad、藍牙喇叭與 Computer 各自一列，按下的那幾列開始播放。藍牙喇叭要先在 macOS 的藍牙設定配對，並出現在系統的聲音輸出清單裡，才會出現在 Airfoil 的清單；手冊另外提到 Speaker Groups，可以把一組輸出存成群組、一次開啟。
5. **調每個輸出的音量**：Airfoil 的主視窗可以分別調「送到每個輸出的音量」，Effects 視窗另有對全部輸出的總音量。iPad 自己的音量鍵仍然作用在 iPad 的喇叭上，所以 Airfoil 裡的音量用來在幾台之間調平衡，iPad 上的音量用來在那個房間調大小。

### iPad 當喇叭換到什麼、付出什麼

iPad 當成喇叭用，換到的是不必另外買喇叭，就能讓每個有 iPad 的房間同步播放同一首歌，而且 iPad 平常的用途不受影響。付出的是 iPad 喇叭的音質、對 Wi-Fi 的依賴與軟體的授權：

- **iPad 內建喇叭的聲音**：平板的喇叭單體小、箱體容積小，低頻的量少，最大音量也有限；單體尺寸與低頻、音量的關係在〔[喇叭的規格與構造](/til/audio/speaker-specs-and-construction/)〕。iPad 適合當背景音樂的分散音源，聽音樂的主要位置仍然用藍牙喇叭或更好的喇叭。
- **Wi-Fi 的穩定度**：聲音經由 Wi-Fi 傳到 iPad，訊號弱的房間會斷音；手冊的 Advanced Speaker Options 有一個 Statistics 顯示，嘗試復原的次數或比例偏高時，代表 Airfoil 連到那一台有困難。
- **軟體的授權與相容性**：Airfoil 是付費軟體，支援的 macOS 版本依官方頁面而定；iOS 版 Satellite 頁面列的版本是 2023 年 2 月的 2.2.0。

## 把 iPad 的聲音送進 Mac：AirPlay 接收器與 USB 音訊輸入

反方向的需求是聲音從 iPad 出發：iPad 上有某個 App（串流服務、遊戲、教學影片），想讓 Mac 接的喇叭播放它的聲音。macOS 內建兩條路，一條經由 Wi-Fi，一條經由傳輸線。

### 經由 Wi-Fi：Mac 的 AirPlay 接收器

Mac 從 macOS Monterey 起可以當 AirPlay 的接收端，Apple 支援文件 108046 列的 Mac 機型是 2020 年以後的 Mac mini、iMac Pro，以及 2018 年以後推出的其他 Mac；送出端是 iPadOS 14 以上的 iPad（iPad 第 6 代、iPad Air 第 3 代、iPad mini 第 5 代、iPad Pro 第 2 代或更新）。

設定位置在 Mac 的「系統設定」>「一般」>「AirDrop與接力」，打開「AirPlay接收器」。下方的「允許AirPlay」選單決定誰看得到這台 Mac：只允許目前的使用者時，只有登入同一個「Apple帳號」的裝置看得到；選「相同網路」或「所有人」時，網路上或附近的其他人的 iPhone、iPad 也會在 AirPlay 清單裡看到這台 Mac，可以另外打開「需要密碼」。iPad 都登入跟這台 Mac 相同的 Apple 帳號時，只允許目前的使用者就夠了；家人的 iPad 用別的帳號時，要選相同網路，並考慮設密碼。

打開之後，在 iPad 的音樂 App 或控制中心點 AirPlay 圖像，選這台 Mac，iPad 的聲音就從 Mac 播放。Apple 的說明寫這讓 Mac「像喇叭一樣使用」。Mac 用哪一個輸出裝置播放收到的 AirPlay 聲音，Apple 的文件沒有寫，本篇也沒有實測。如果它跟著 macOS 目前選的聲音輸出，那麼把輸出選成〔[macOS 的多重輸出裝置](/til/audio/macos-multi-output-device/)〕裡建好的多重輸出裝置，iPad 的聲音就會同時從 Mac 的幾個輸出出來；要確認時，播放之後看聲音從哪幾台出來。

這條路沒有線，iPad 可以在房間裡任何位置操作；代價是一次只有一台 iPad 能送到這台 Mac，而 AirPlay 的緩衝讓聲音晚於 iPad 上的操作，延遲的大小 Apple 沒有寫。

### 經由傳輸線：「音訊MIDI設定」的 iOS 裝置音訊輸入

「音訊MIDI設定」可以把用線接到 Mac 的 iPhone 或 iPad 變成 Mac 的音訊輸入裝置。介面上的說明是：按「啟用」讓 iOS 裝置進入「跨裝置音訊和MIDI模式」，在這個模式中 iPhone 或 iPad「會在Mac上顯示為音訊輸入裝置」，可以錄製非電話的音訊；說明寫的是 Lightning 對 USB 連接線，USB-C 的 iPad 用 USB-C 線的情形本篇沒有實測。Apple 的〈Set up audio devices in Audio MIDI Setup on Mac〉寫的步驟是：

1. 把 iPad 接到 Mac。
2. 在「音訊MIDI設定」的音訊裝置視窗，iPad 那一列先按「啟用」，再選它；iPad 可能要求輸入密碼解鎖，或詢問是否信任這台電腦，照做之後 Mac 才讀得到它的聲音。
3. 用 Control 鍵點一下 iPad 那一項，選「使用此裝置來輸入聲音」；不選也可以，錄音 App 裡另外指定它當輸入裝置即可。
4. 「格式」設成跟裝置相符的取樣率與位元深度。

這條路把 iPad 的聲音變成一個輸入，用途是錄製，或交給接收輸入的 App 處理（錄音軟體、直播軟體）。要讓這個輸入直接從 Mac 的喇叭播放，還需要一個把輸入送到輸出的 App；macOS 的 QuickTime Player 的「新增音訊錄製」視窗有音量滑桿，可以邊錄邊從輸出聽到輸入的聲音，這個用法本篇沒有實測。啟用期間 iPad 自己的喇叭是否還發聲，Apple 的文件沒有寫。跟 AirPlay 那條路相比，傳輸線不受 Wi-Fi 影響、同時還能替 iPad 充電；代價是 iPad 被線綁在 Mac 旁邊。

## 各台 iPad 獨立播放：藍牙喇叭配給其中一台

不經過 Mac 的做法是每台 iPad 各自當播放器：每個房間的 iPad 各自開串流 App 播放，藍牙喇叭跟其中一台 iPad 配對，成為那個房間的主要音源。每台 iPad 播的是自己的內容，彼此不同步，也不需要同步。

這個做法適合幾個房間的人各聽各的、或同一時間只在一個房間聽的情形：不需要任何付費軟體，沒有 Wi-Fi 串流的斷音與延遲疊加，Mac 也不必開著。它做不到的是同一首歌在幾個房間同步：在兩個房間各自按下播放，兩台的進度一開始就差了按鍵的時間差，走到兩台都聽得到的位置會聽到兩個錯開的聲音，原因跟〔[macOS 的多重輸出裝置](/til/audio/macos-multi-output-device/)〕〈各裝置的延遲不同〉的回音相同。

不支援同時連兩個來源（multipoint）的藍牙喇叭，一次只連一個來源：從 Mac 改給 iPad 用時，要在 Mac 斷開它，或讓 iPad 主動連線；支援 multipoint 的喇叭可以省掉這一步，喇叭是否支援寫在它的規格裡。藍牙的編碼格式與延遲在〔[數位訊源的構造與選擇](/til/audio/digital-streaming-source-guide/)〕。

## 依同步需求與聲音的出發點選做法

選哪一種做法，看兩個條件：幾個房間要不要同步播放同一首歌，以及聲音從哪一台裝置出發。

- **要同步，聲音從 Mac 出發**：用 Airfoil，iPad 裝 Satellite，藍牙喇叭與 Mac 自己的喇叭一起加入。本篇寫到的做法裡，Mac、藍牙喇叭與 iPad 同時發聲而沒有回音的只有這一種，代價是付費授權、整套延遲等於最慢的那一台、依賴 Wi-Fi。只用 Mac 的有線輸出與藍牙喇叭、不需要 iPad 時，多重輸出裝置免費，而兩台都聽得到的位置會有回音。
- **聲音從 iPad 出發，要經由 Mac 的喇叭播放**：要無線、iPad 在房間裡移動時，用 Mac 的 AirPlay 接收器；要錄音、或不想依賴 Wi-Fi 時，用傳輸線接 USB 音訊輸入，另外用一個 App 把輸入送到輸出。
- **不需要同步**：各台 iPad 獨立播放，藍牙喇叭配給最常聽的那個房間的 iPad。

幾台 iPad 加一台藍牙喇叭、還不確定需不需要同步時，從各台 iPad 獨立播放開始不必花錢，也不必改 Mac 的設定。之後要讓幾個房間同時播同一首歌時，再試用 Airfoil：試用版傳送十分鐘之後才降低音質，這段時間足夠確認每台 iPad 是否出現在 Airfoil 的輸出清單、各房間的聲音是否對齊。
