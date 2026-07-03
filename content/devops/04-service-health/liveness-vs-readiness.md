---
title: "Liveness 與 Readiness"
date: 2026-07-03
description: "分不清該用哪種探針、或探針失敗後平台重啟了不該重啟的服務時，回來釐清 liveness、readiness、startup 三種探針各自宣告什麼、失敗後平台做什麼"
weight: 2
tags: ["devops", "liveness", "readiness", "probe", "kubernetes"]
---

Liveness 跟 readiness 探測失敗時，平台採取的動作完全不同：readiness 失敗，平台把這個實例從流量目標裡摘掉、但讓它繼續跑；liveness 失敗，平台判定這個實例壞到無法恢復、直接重建它。兩者混淆的代價是用錯恢復動作——把一個只是暫時不能接流量的服務給重啟了，或把一個真的死掉的服務一直留在流量池裡。分清這兩種健康，是設計自動恢復的前提。

差別的根源是它們回答的問題不同。Readiness 問「現在可以安全地把流量送給它嗎」，liveness 問「它還有基本運作能力、還是壞到只能砍掉重來」。同一個服務在同一時刻，readiness 可能為否、liveness 卻為是——它活著、只是還沒準備好。

## Readiness：宣告可以安全接流量

Readiness 是服務對平台的宣告：我現在可以安全承接流量了。平台只把流量導向 readiness 通過的實例；一旦某個實例 readiness 轉為否，平台停止送新流量給它，但不動它的進程。這個機制讓服務有辦法在「還活著、但暫時不該接流量」的狀態下把自己隔離起來——正在載入大型快取、下游必要依賴短暫斷線、或正在收束準備關閉。

Readiness 設計的核心決策是「哪些依賴要納入判斷」。這條線劃錯，readiness 不是太緊就是太鬆。依賴大致分三類，各有不同的納入原則：

- **必要依賴**：資料庫、認證服務這種，不可用時服務完全無法處理請求。這類納入 readiness——它們斷了，服務就該停止接流量。
- **可降級依賴**：推薦引擎、非關鍵快取這種，不可用時服務仍能服務核心請求、只是功能打折。這類不該納入 readiness，改用熔斷或 fallback 在應用層處理；把它們納入，等於讓一個可以降級的功能故障拖垮整個服務的接流量能力。
- **觀測依賴**：metrics collector、log shipper 這種。把它們納入 readiness 是常見的誤判——觀測基建掛掉本身不影響服務處理請求的能力，卻會讓整個服務被判成不 ready、被摘光流量。監控自己的健康不該是服務能否服務的前提。

## Liveness：宣告基本運作能力還在

Liveness 是服務宣告自己還有基本運作能力；它失敗時平台的動作是重建實例，因為判斷已經是「這個實例壞到不可恢復」。正因為後果是重啟，liveness 只該用來偵測那些「重啟真的能修好」的失敗。

適合 liveness 偵測的是進程回不了頭的內部壞死。一個典型是死結——把 liveness 端點設在跟主要工作獨立的執行緒上，主工作 deadlock 時這個端點答不出來，平台重建實例確實能解。另一個是記憶體洩漏逼近 OOM 的前兆：服務主動回報 unhealthy、讓平台在還來得及的時候有序重建，好過等平台的 OOM kill 硬砍（OOM kill 不走 graceful shutdown、在途請求直接中斷）。還有一類是關鍵背景任務永久停止——像憑證續期、session 清理這種停了服務會慢慢壞掉的任務，值得反映進 liveness。

不適合 liveness 偵測的是下游的暫時性問題。下游資料庫短暫不可用、外部 API 逾時、快取命中率升高——這些用 liveness 去重建實例毫無幫助，重啟這個服務不會修好它的下游，只會用重啟放大問題：實例重建期間容量更少、下游壓力反而更大。這類屬於 readiness（暫時摘流量）或熔斷（快速失敗）的範疇，不是 liveness。把下游故障接進 liveness，是製造 restart loop 最常見的方式。

## Startup：啟動期是第三種狀態

服務剛起來、還在初始化的那段時間，既不是死、也還不能服務，這是第三種探針要覆蓋的狀態。Startup 探針在啟動期間持續探測，一旦成功就把健康判斷交棒給 liveness 跟 readiness。它存在的理由是啟動期的容忍窗口跟穩定運行期不同——一個冷啟動要拉 image、連依賴、重建索引的服務，可能要幾分鐘才就緒，但這不代表穩定運行時也該容忍幾分鐘不回應。Startup 探針的總容忍時間由探測失敗門檻乘上探測間隔決定（例如門檻 30 次、間隔 10 秒，就是 300 秒窗口），設計時量測最差情境的啟動時間（冷啟動加 image 拉取加依賴連線）再加兩三成 headroom。

這帶出一個反模式：把 startup、readiness、liveness 全設成同一個 `/health` 端點。三種探針問的是不同問題——初始化完成不等於依賴就緒，依賴暫時不可達不等於服務本身壞了。同一個端點無法同時給出三種語意不同的答案，混用的結果是平台在錯的時機做錯的動作。[Health check endpoint 設計](/devops/04-service-health/health-check-endpoint/) 講的檢查深度，在這裡對應到「哪一種探針該探到哪一層」。

## 探針靈敏度是雙向的取捨

Liveness 設太敏感，服務會陷入 restart loop——一點抖動就被判死、重建、重建期間更不穩、又被判死。設太寬鬆，壞掉的實例會長期留在線上、持續吃流量卻服務不了。Readiness 同理，只是後果換成流量抖動而非重啟迴圈。

Liveness 觸發的重啟從來不是零成本，設計靈敏度時要把代價算進去：在途請求被中斷、連線要重建（資料庫連線池、快取、佇列消費者都要重新建立）、實例重建期間出現容量缺口。最危險的是 thundering herd——多個實例因為同一個下游問題同時被判失敗、同時重啟、同時回來搶資源，瞬間把下游壓力放大。這也是為什麼 liveness 不該接下游故障：下游一抖，所有實例一起重啟，比原本的問題更糟。

## 下一步路由

- 在單機 systemd 上，liveness 對應 watchdog、重啟對應 restart policy → [systemd watchdog 與自動重啟](/devops/04-service-health/systemd-watchdog-restart/)
- 探針該探到哪一層、回什麼才算健康 → [Health check endpoint 設計](/devops/04-service-health/health-check-endpoint/)
- 不同平台能不能分開表達這三種探針，是選型的關鍵 → [Process supervisor 選型](/devops/04-service-health/process-supervisor-selection/)
- Readiness 轉為否、先摘流量再收束，是關閉流程的第一步 → [Graceful shutdown](/devops/04-service-health/graceful-shutdown/)
