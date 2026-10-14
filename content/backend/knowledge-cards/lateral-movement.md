---
title: "Lateral Movement（橫向移動）"
date: 2026-10-14
description: "評估一台主機被入侵之後攻擊者還連得到哪些機器、內網或 VPN 裡的可達範圍要收到多窄時，查攻擊者以已經拿下的機器當跳板往內擴散的方式"
weight: 477
tags: ["backend", "security", "network"]
---

橫向移動（lateral movement）是攻擊者拿下一台機器之後，以它為跳板連到原本從外面連不到的其他機器。跳板能用的材料有兩種：網路上的可達性（這台機器在內網或 VPN 裡連得到哪些位址與連接埠），以及存放在這台機器上的憑證（SSH 金鑰、資料庫密碼、雲端存取金鑰、設定檔裡的權杖）。所以一次入侵的影響除了第一台機器上的資料，還由它連得到什麼、手上有哪些憑證決定。同一種擴散在故障上的估法見 [Blast Radius](/backend/knowledge-cards/blast-radius/)，入侵的估法見本卡的〈判讀方式〉。

## 概念位置

橫向移動發生在 [Trust Boundary](/backend/knowledge-cards/trust-boundary/) 沒有被重新驗證的地方：內網或 VPN 裡的服務假設「連得到我的都是自己人」，跳板一旦在裡面，這個假設讓服務對跳板發來的連線一律放行。對應的設計原則是 [Zero Trust（零信任）](/backend/knowledge-cards/zero-trust/)：每一次連線各自通過身分與授權，以及 [Least Privilege](/backend/knowledge-cards/least-privilege/)：每台機器只拿得到它工作需要的可達範圍與憑證。

## 可觀察訊號與例子

雲端主機對網際網路提供服務，經由 VPN 與家裡的監控主機相連。VPN 預設雙向互通時，攻擊者經由應用程式的漏洞拿下雲端主機，下一步就能經由隧道連到監控主機；監控主機若在家用網路裡，再下一步是同一個網路裡的筆電與 NAS，它們從來沒有按面對攻擊者的標準設定過。憑證的形態也一樣：雲端主機上存著寫入異地備份的存取金鑰，攻擊者拿到它就連得到備份，而那把金鑰若有刪除權限，備份跟著消失。兩種擴散怎麼收窄見 [7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/)。

## 判讀方式

逐台主機列出兩份清單：它經由內網或 VPN 能主動連到的位址與連接埠，以及存放在它上面的憑證各自能做什麼。清單上超過工作需要的部分，就是這台被拿下時攻擊者多拿到的部分。收窄時要分清楚限制設定在哪裡：存放在被拿下那台機器上的防火牆規則與設定檔，攻擊者拿到 root 就改得掉；存放在另一端或控制平面上的限制，他改不到，只有這一種在入侵發生之後仍然成立。擴散有沒有發生要看連線紀錄：一台主機向它平常不連的位址發起連線，是橫向移動最直接的訊號，訊號的治理見 [7.13 偵測覆蓋率與訊號治理](/backend/07-security-data-protection/detection-coverage-and-signal-governance/)。
