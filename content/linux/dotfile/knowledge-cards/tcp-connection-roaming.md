---
title: "TCP 連線與漫遊"
date: 2026-07-08
description: "遠端連線一換網路（Wi-Fi 切行動網路、休眠喚醒、換 IP）就斷、想知道為什麼 SSH 扛不住而 mosh 撐得住時回來讀"
weight: 50
tags: ["linux", "remote", "network", "ssh", "mosh", "knowledge-cards"]
---

一條 TCP 連線由 4-tuple 唯一識別：來源 IP、來源 port、目的 IP、目的 port。這四個值任一改變，這條連線對作業系統核心而言就是另一條——原連線收到的封包對應不回去、直接被丟棄。這決定了一個硬限制：建在 TCP 之上的協定無法漫遊，客戶端換了網路（換 IP）就等於換了 4-tuple，連線斷掉。SSH 繼承這個限制、mosh 用另一種傳輸繞過它，是遠端連線工具選型的底層分野。

## 連線由 4-tuple 識別

TCP 是有狀態的：兩端各自維護一份連線狀態（序號、視窗、緩衝），核心靠封包表頭的來源 / 目的 IP 與 port 把進來的封包對應回某條已建立的連線。筆電從家裡 Wi-Fi 換到行動網路、手機走出 Wi-Fi 範圍、休眠喚醒重新撥號——這些都會換掉客戶端的來源 IP，於是後續封包帶著新的來源 IP 進來、核心找不到對應的連線、原連線名存實亡。這不是 bug，是 TCP 的識別方式決定的。

## 為什麼 SSH 繼承這個限制

SSH 是跑在 TCP 上的應用層協定，它的加密狀態與 session 都綁在那條 TCP 連線上。TCP 一斷、SSH session 隨之結束，掛在它前景的程序收到 `SIGHUP` 被終止。所以「換網路就掉線、而且要手動重連」是 SSH 的典型症狀，根源不在 SSH 本身、在它底下的 TCP。

## mosh 怎麼繞過

mosh 改用 UDP，並在應用層自己維護一個跟客戶端 IP 無關的 session：每個 session 有一個獨立的識別碼與金鑰，端點 IP 變了，客戶端用同一把 session 金鑰把封包送到伺服器、伺服器認得這個 session 就接續下去，不需要一條「不變的 TCP 連線」。這就是 mosh 能漫遊的根本原因——它把「連線識別」從核心的 4-tuple 搬到應用層自管的 session ID。代價與手感另見 [mosh 本地回顯預測](/linux/dotfile/knowledge-cards/mosh-local-echo-prediction/)。

## 判讀訊號

換網路後終端凍住、要手動重連、前景任務跟著死——這組症狀指向 TCP 綁定，而不是伺服器出問題。判斷「工作有沒有因此中斷」要看任務跑在哪：直接掛在 SSH 前景的會隨連線死，跑在多工器 session 裡的（見 [tmux 基礎](/linux/tools/cli/tmux-persistence-and-basics/)）則活在伺服器端、重連 attach 就接回。

## 邊界

TCP 的「斷」分兩種程度。**沒換 IP、只是短暫丟包**（隧道抖動、幾秒斷網）時，TCP 靠重傳能撐過去、連線不必重建。**真正換了來源 IP** 才必斷。這帶出一個實用的中間解：mesh VPN（Tailscale 這類）給裝置一個穩定的私網 IP、實體網路變了由它在底層重建路徑、對上層的 TCP 連線來說來源 IP 沒變——所以走 tailnet 的 SSH 有機會撐過一次實體換網（只要 overlay 重建的空窗夠短、TCP 沒逾時）。要真正無感、不受空窗長短影響的漫遊，才需要 mosh 的 UDP session 模型。
