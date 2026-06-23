---
title: "5.10 Outbound Tunnel 入口與生命週期"
date: 2026-06-16
description: "整理 cloudflared / Tailscale 等反向隧道的入口形態、生命週期合約與故障模式"
weight: 10
tags: ["backend", "deployment", "tunnel"]
---

家用主機沒有固定 IP、路由器不想開 port，但手機要能連進來操作 — outbound tunnel 用反向連線解這個入口問題。它跟 load balancer 入口是兩種不同的入口形態：LB 假設 instance 有對外可達位址、流量從外網路由進來;tunnel 由本機進程主動外連到邊緣、把流量沿反向隧道帶回來、路由器零開 port、對公網零入站面。家用服務、個人自架工具、無固定 IP 的環境常用這種入口。

## 適用判斷

選 outbound tunnel 的前提是「要被外部觸及、但不想暴露公網入口」。典型場景：手機遠端操作自有主機、家庭網路內的服務對外、開發環境臨時對外驗證。服務本身值不值得自建、見 [0.21 交付形態選型](/backend/00-service-selection/delivery-mode-selection/) 的個人自架工具段;這裡只處理「入口形態選了 tunnel 之後」的部署合約。

cloudflared（綁 Cloudflare 邊緣與網域）、Tailscale（綁私有網路 / Funnel 對外）、Boundary 各有定位差異，但入口生命週期的判讀框架相同。

## tunnel contract 組成

tunnel 入口合約跟 [load balancer contract](/backend/05-deployment-platform/load-balancer-contract/) 對照、差異集中在連線方向與就緒語意：

1. connection contract：本機進程主動對邊緣建立並維持反向隧道、無入站 port;隧道斷線的重連策略決定外部可達性的恢復速度。
2. readiness contract：對外可達 = 隧道已建立 **且** 後端服務已可服務。兩個條件任一不成立、外部請求就拿到 502 / 連線中斷。
3. ordering contract：啟動順序是後端服務先就緒、tunnel 再宣告 ready;關閉順序相反、tunnel 先收斂停止帶入新流量、後端再退出。
4. auth contract：tunnel 只負責把流量帶回來、本身不是認證。隧道網址是位址、不是密碼 — 任何拿到網址的人都可達後端、所以認證必須疊在 tunnel 之後（見下）。

## 生命週期與 readiness 對齊

tunnel 入口的就緒判讀比 LB 多一層。LB 的 health check 打後端 instance、通過代表可接流量;tunnel 場景下、「後端 health check 通過」不等於「外部可達」 — 還要隧道本身連上邊緣。readiness 要同時涵蓋兩者、否則會出現「服務自己覺得健康、外面卻連不進來」的盲區。

啟動順序錯位的後果具體：tunnel 比後端早 ready、邊緣開始導流量進來、後端還沒起、外部看到一批 502。所以 startup 階段 tunnel 的 ready 訊號要 gate 在後端 [readiness](/backend/knowledge-cards/readiness/) 之後。關閉時序則相反、先讓 tunnel 停止帶入新連線、給在途請求收斂窗口、後端再 [graceful shutdown](/backend/knowledge-cards/graceful-shutdown/);這層責任跟 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/) 的 startup / readiness / drain 一致、只是 drain 的對象從 LB 摘流量換成 tunnel 收斂。

## 穩態維持與重連策略

隧道建立後進入穩態：tunnel 進程與邊緣之間維持長連線，邊緣用心跳（keepalive）偵測連線是否存活。心跳間隔與超時由供應商決定（cloudflared 預設每 5 秒心跳、連續失敗觸發重連；Tailscale 由 WireGuard 層的 persistent keepalive 維持 NAT 映射）。穩態下不需要額外操作，但要理解一個語意：邊緣側判定「連線已斷」到本機進程偵測到斷線之間有延遲，這段時間外部請求會 timeout 而非立即拿到錯誤。

連線中斷後 tunnel 進程自動重連，重連策略的關鍵是 backoff：首次斷線立即重試、連續失敗拉長間隔、避免在邊緣側故障時打滿重連請求。重連成功後 readiness 要重新驗證——隧道恢復不等於後端仍然健康，特別是斷線期間後端可能已經被別的事件影響。

### 隧道多連線與冗餘

cloudflared 預設對每個 tunnel 建立 4 條連線到不同邊緣節點（Cloudflare 在不同 data center 的 edge server）。單條連線斷線時，流量自動切到其餘連線，外部使用者感受不到中斷。4 條連線全部斷開才會觸發完全不可達。

Tailscale 的冗餘模型不同：WireGuard tunnel 是點對點連線，沒有多邊緣節點分散。Tailscale 的高可用靠 DERP relay server 做中繼——直連失敗時退到 relay，延遲增加但可達性維持。

這個差異在穩定性預期上很重要：cloudflared 的可達性依賴 Cloudflare 邊緣網路的多點冗餘，Tailscale 的可達性依賴直連品質與 DERP 中繼。選擇時要問「我的網路環境是否穩定到不需要多連線冗餘」。

## 故障模式：network 層與 application 層的分離

tunnel 斷線跟 LB health check 失敗是不同層的故障。LB health check 失敗多半是 application 層（後端掛了、依賴不通）；tunnel 斷線常是 network 層（邊緣連線中斷、本機外連受阻、供應商側問題）、而後端服務本身完全健康。事故判讀要先分清這兩層：後端 log 一切正常、但外部全部連不進來、第一個要看的是 tunnel 進程的連線狀態、不是後端。

這也改變監控訊號的設計。LB 場景看後端 5xx 與 latency 就能覆蓋多數入口問題；tunnel 場景要額外監控隧道本身的連線狀態與重連次數——隧道靜默斷掉時、後端指標一片祥和、唯一的訊號在 tunnel 進程那邊。

### 故障分類與判讀順序

tunnel 環境下的故障可按層級分類，判讀順序從外到內：

| 層級        | 症狀                               | 判讀第一步                         |
| ----------- | ---------------------------------- | ---------------------------------- |
| 供應商邊緣  | 所有 tunnel 用戶同時受影響         | 查供應商 status page               |
| 本機外連    | 單一 tunnel 斷線、其他外連也有問題 | 查本機網路、NAT、防火牆            |
| tunnel 進程 | tunnel 進程 crash 或 hang          | 查 tunnel 進程 log 與 restart 狀態 |
| 後端服務    | tunnel 正常但外部拿到 502          | 查後端服務 readiness               |
| 認證閘道    | tunnel + 後端正常但外部拿到 403    | 查認證設定（token / ACL 過期）     |

判讀順序的重點是「先確認 tunnel 層是否正常、再往內看」。如果跳過 tunnel 層直接排查後端，會在後端 log 一切正常的情況下浪費時間。

## 認證必須疊在 tunnel 之後

tunnel 把後端的可達性開到了外部、但它不認證。隧道網址可能從瀏覽器紀錄、分享連結、Referer 外洩、不該被當成安全機制。所以 tunnel 之後必須疊認證閘道、且預設拒絕 — 未通過認證的流量不該觸及後端。

常見的疊法是邊緣與本機各一層：邊緣層（cloudflared 配 Cloudflare Access service token、Tailscale 配 ACL）讓未授權流量在邊緣就被擋、根本到不了本機;本機層（反向代理驗共享密鑰 / basic auth）作為邊緣萬一失效的縱深。入口威脅建模見 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/);單人自用工具的裝置綁定認證見 [7.2 單人裝置認證模型](/backend/07-security-data-protection/identity-access-boundary/#單人裝置認證模型)。

## 判讀訊號

| 訊號                            | 判讀重點                              | 對應動作                                                              |
| ------------------------------- | ------------------------------------- | --------------------------------------------------------------------- |
| 外部全部連不進來、後端 log 正常 | 故障在 network 層、隧道斷線           | 先查 tunnel 進程連線狀態、不是後端                                    |
| 啟動後短時間外部拿到一批 502    | tunnel 比後端早 ready、導流量進空服務 | 把 tunnel ready gate 在後端 readiness 後                              |
| 隧道頻繁重連、外部間歇中斷      | 本機外連不穩或邊緣側抖動              | 查 cloudflared / tailscaled 的重連 log、確認 backoff 間隔是否正常拉長 |
| 拿到網址的人直接連到後端        | 認證沒疊在 tunnel 之後、網址被當密碼  | 補邊緣 / 本機認證閘道、預設拒絕                                       |
| 部署切換隧道時對外中斷拉長      | 關閉順序錯位、tunnel 未先收斂         | 先停 tunnel 帶入新連線、再退後端                                      |

## 常見誤區

把 tunnel 網址當密碼、是最常見也最危險的誤判。網址不好猜不代表是祕密、它會從各種地方外洩、認證要靠 tunnel 之後的閘道、不是靠網址難猜。

把「後端健康」當成「外部可達」、忽略隧道本身是獨立的失效點。tunnel 場景的可達性是後端健康與隧道連線的交集、監控要覆蓋兩者。

把 tunnel 當「永久掛著」的常駐入口、放大暴露窗。自用場景常更適合用時起、用完關 — 暴露窗壓到最小;要常駐時、認證閘道與監控的投資等級要隨之上調。

把 tunnel 供應商視為零停機、不設本機降級預案。tunnel 依賴外部供應商的邊緣網路與協調伺服器，供應商事故期間本機服務完全健康但外部無法觸及。有降級需求的場景要準備替代入口路徑（如臨時開 port + 反向代理），或接受供應商 SLA 決定自身可用性。

## 跨模組路由

1. 與 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/) 的交接：tunnel 的 startup / readiness / drain 對齊生命週期合約、只是 drain 對象換成隧道收斂。
2. 與 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/) 的交接：tunnel 作為對外入口的威脅建模與認證疊法。
3. 與 [7.6 秘密管理與機器憑證治理](/backend/07-security-data-protection/secrets-and-machine-credential-governance/) 的交接：tunnel 憑證與認證閘道密鑰的保管與輪替。
4. 與 [4 觀測](/backend/04-observability/) 的交接：隧道連線狀態與重連次數要進監控、否則 network 層故障無訊號。

## 下一步路由

要把 tunnel 入口放進整體生命週期、接著讀 [5.6 Platform Lifecycle Contract](/backend/05-deployment-platform/platform-lifecycle-contract/)。要把 tunnel 之後的認證做紮實、接著讀 [7.3 入口治理與伺服器防護](/backend/07-security-data-protection/entrypoint-and-server-protection/) 與 [7.2 身分與授權邊界](/backend/07-security-data-protection/identity-access-boundary/)。判斷服務是否屬於個人自架工具形態、回 [0.21 交付形態選型](/backend/00-service-selection/delivery-mode-selection/)。
