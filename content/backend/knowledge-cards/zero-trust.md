---
title: "Zero Trust（零信任）"
date: 2026-10-14
description: "判斷內網或 VPN 裡的服務能不能因為連線來自內部就省掉認證、或要評估一條連線該放行到什麼範圍時，查「每一次連線各自通過身分與授權」這個原則的內容與導入代價"
weight: 478
tags: ["backend", "security", "network", "zero-trust"]
---

零信任（zero trust）是一種存取控制的原則：每一次連線都要各自確認是誰發起、這個身分可以用哪個服務，網路上的位置（在內網、在 VPN 裡）不構成信任的理由。它對照的是邊界模型（perimeter security）：在網路邊界設防，進到邊界以內的連線彼此信任，VPN 接進來就算在內網。美國國家標準與技術研究院的 NIST SP 800-207〈Zero Trust Architecture〉是這個原則常被引用的定義文件。邊界模型失效的方式見 [Lateral Movement（橫向移動）](/backend/knowledge-cards/lateral-movement/)：邊界內任何一台被拿下，攻擊者就繼承了它在邊界內的信任。

## 概念位置

零信任把 [Trust Boundary](/backend/knowledge-cards/trust-boundary/) 從網路邊界移到每一個服務前面：信任在每一次連線重新建立，不沿用「封包來自內網」這個前提。它與 [Least Privilege](/backend/knowledge-cards/least-privilege/) 回答同一個存取決定裡的兩個問題：零信任問每一次連線有沒有被驗證，最小權限問驗證通過之後給了多少。VPN 在這個框架裡仍有用處，它負責加密與確認對方持有金鑰，只是它的結果不再直接等於授權。

## 可觀察訊號與例子

整套導入的形態是每個服務前面都有一個依身分與裝置狀態決定放不放行的代理（[身分感知代理](/devops/infra/knowledge-cards/identity-aware-proxy/)），Google 公開過的 BeyondCorp 是常被引用的例子；這需要身分提供者（identity provider）、裝置管理與代理層，建置與維運的成本對兩三台主機的小型服務高於它擋下的風險。小規模取用的是它的問法：exporter、心跳監看程式、Prometheus 的介面在 VPN 裡預設沒有認證，零信任的問法是「VPN 裡任何一台被入侵時，擋在這個服務前面的是什麼」，答案是「沒有」時，就要在服務前面加認證，或把 VPN 裡連得到它的機器收到只剩需要的那一台。

## 判讀方式

零信任常與 assume breach（假設已被入侵）一起使用：評估時每一台（包括管理者日常使用的裝置）各假設一次已經被拿下，問它發出的連線會被放行到哪裡。對每一條連線問三件事：發起的是哪一台機器、以什麼身分、連到哪一個服務。三件事都說得出來、而且都是工作需要的，這條連線符合原則；只說得出「因為它在 VPN 裡」，信任是由位置給的。導入程度依代價判斷：在服務前面加認證、收窄可達範圍的成本低，先做；身分感知代理（identity-aware proxy）、裝置狀態檢查的成本高，等連線的數量與參與的人多到逐條管理的成本超過導入代理層時再評估。Tailscale 這類 mesh VPN 常被描述成零信任網路，而它預設全部互通時的行為接近邊界模型，以存取規則收窄到需要的連線之後才符合本卡的三件事。兩個網路之間的連線怎麼套用這三件事，見 [7.43 兩個網路之間的連線安全](/backend/07-security-data-protection/cross-network-connection-security/)。
