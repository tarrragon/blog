---
title: "Secure Context（安全來源）"
date: 2026-11-21
description: "網頁在本機開發時好好的、換到內網位址或 http 網址之後 passkey、相機、剪貼簿或 Service Worker 用不了，或要判斷內網服務需不需要 HTTPS 時，查瀏覽器怎麼判定安全來源與哪些功能只在安全來源開放"
weight: 507
tags: ["backend", "knowledge-card", "security", "web"]
---

Secure Context（安全來源，其他中文資料也寫作「安全上下文」）是瀏覽器對一個頁面的判定：頁面網址用的是 HTTPS 這類加密的協定，或主機是本機（`localhost` 與 `*.localhost`、`127.0.0.0/8` 這段 loopback 位址、`::1`），或頁面是本機檔案（`file:`），而且嵌著它的外層頁面也都成立時，瀏覽器把它當成安全來源，並只對安全來源開放一批不能讓連線途中的第三方竄改或竊聽的功能。頁面裡的程式用 `window.isSecureContext` 讀得到這個判定。判定的單位是頁面；[Same-Origin Policy](/backend/knowledge-cards/same-origin-policy/) 的單位是來源（協定、主機名與埠），兩者管的是不同的事。

## 跟其他概念的關係

Same-Origin Policy 限制一個來源的程式讀取另一個來源的回應；Secure Context 決定一個頁面本身能不能用某些瀏覽器功能。兩者各自判定：同一個來源的頁面之間互相讀得到回應，但只要那些頁面的網址是 `http://` 的內網名稱，它們全部用不了只開放給安全來源的功能。

只開放給安全來源的功能，包括 [Passkey](/backend/knowledge-cards/passkey/) 底層的 WebAuthn、Service Worker（PWA 的離線與推播都靠它）、存取相機與麥克風的 `getUserMedia`、非同步的剪貼簿 API、Web Crypto API（`crypto.subtle`），以及 `crypto.randomUUID`。完整清單依瀏覽器與版本而不同，以 MDN 的〈Features restricted to secure contexts〉為準。

瀏覽器只依網址的協定與主機判定，不知道也不檢查底下的網路有沒有另外加密：mesh VPN 或公司內網裡的流量即使全程加密，頁面網址只要是 `http://<內網名稱>`，瀏覽器就不把它當成安全來源。讓瀏覽器把它當成安全來源的做法，是讓這個網址用 HTTPS 提供，而 HTTPS 要有瀏覽器信任的憑證（[TLS / mTLS](/backend/knowledge-cards/tls-mtls/)）。

## 可觀察訊號與例子

- **本機開發正常，換網址就失效**：開發時用 `http://localhost:3000` 測得到相機與 passkey，部署到內網、改用 `http://<主機名稱>:3000` 之後，`navigator.mediaDevices` 是 `undefined`，或 passkey 的註冊直接拋出錯誤；在主控台執行 `window.isSecureContext` 回 `false`。
- **內網的服務要求 HTTPS**：自架的服務把 HTTPS 寫成必要條件，原因之一是它的網頁版要在瀏覽器裡用 Web Crypto 加解密，或要用 Service Worker；個別服務的實際原因看它自己的文件。
- **iframe 裡的頁面**：一個用 HTTPS 載入的頁面，嵌在 `http://` 頁面的 iframe 裡時，瀏覽器不把它當成安全來源，因為判定要連同外層的頁面一起成立。

## 判斷條件與後果

- **服務只在本機用**：本機的網址本身就是安全來源，不必為了這批功能另外取得憑證。passkey 是例外：要用 `http://localhost` 測，不能用 `http://127.0.0.1`，原因是 WebAuthn 規格只允許用網域名稱當 relying party ID（passkey 綁定的網站識別），不接受 IP 位址；規格寫的理由是用 IP 位址識別網站跟它依賴的公開金鑰基礎設施（PKI）的安全模型搭不上。
- **服務經由內網名稱或 VPN 給其他裝置用，而且要用只開放給安全來源的功能**：用 `http://` 網址時，這些功能在別的裝置上用不了，服務要改用 HTTPS 提供，代價是要取得瀏覽器信任的憑證；passkey 同樣要用網域名稱開，用 IP 位址開的頁面即使有 HTTPS 也註冊不了。在 tailnet（同一個 Tailscale 帳號底下互連的裝置，見 [Mesh VPN](/devops/infra/knowledge-cards/mesh-vpn/) 卡）裡，可以用 `tailscale serve` 的 HTTPS 模式取得憑證。這樣做的代價是機器名稱會寫進公開的 Certificate Transparency 紀錄，取捨見 [5.10 Outbound Tunnel 入口與生命週期](/backend/05-deployment-platform/outbound-tunnel-entry/) 的〈用 tailscale serve 讓只聽本機的 HTTP 服務給 tailnet 連：實測、限制與 HTTPS 模式的代價〉。
- **服務經由內網名稱給其他裝置用，但用不到這批功能**：一般的表單、讀資料、管理介面在 `http://` 下照常運作，安全來源的判定對它沒有影響；這時要不要上 HTTPS，取決於這一段連線有沒有別的加密（VPN）以及瀏覽器的「不安全」提示能不能接受，跟這張卡的判定無關。
- **開發時暫時把某個 `http://` 來源當成安全來源**：Chrome 有「Insecure origins treated as secure」這個實驗性設定（`chrome://flags/#unsafely-treat-insecure-origin-as-secure`），可以逐一指定來源。它只改這一台瀏覽器的判定，其他使用者的瀏覽器照樣不開放那批功能，所以只適合開發時測試；Chromium 的討論串回報過相機、WebRTC 這類功能在設定之後仍然失敗，實際能不能用要在那個瀏覽器版本上測。
