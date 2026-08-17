---
title: "Security Control Domain（資安控制面）"
tags: ["backend", "knowledge-card", "security", "governance"]
date: 2026-08-18
description: "說明一條資安風險的防守責任歸給哪一類控制，以及這個「控制面」與基礎設施的 control plane 同名不同義"
weight: 441
---

Security control domain 的核心概念是「一條風險的防守責任歸給哪一類控制」。它把風險分派到身分、入口、資料、供應鏈、偵測或治理其中一面，讓「誰該處理這件事」有一個先於人選的答案——先判歸屬、再指派角色。資安章節裡的「控制面」指的是這個東西。 可先對照 [Defense in Depth](/backend/knowledge-cards/defense-in-depth/)。

**這個詞與基礎設施的 [control plane](/backend/knowledge-cards/control-plane/) 同名而不同義**，而兩義在同一批內容裡並存：control plane 問的是「策略與配置由哪一層下發」（service mesh、Kubernetes、API gateway 的決策層），是系統的分層；control domain 問的是「這條風險由哪一類防守承接」，是責任的分類。vendor 頁寫「單一 secret 控制面」用的是前者，防守章節寫「入口控制面」用的是後者。判別看句子在問分層還是問歸屬。

## 概念位置

控制面位在 [threat model](/backend/knowledge-cards/threat-model/) 與具體控制之間：威脅模型列舉風險的位置，控制面決定每個位置的責任歸屬，而 [authentication](/backend/knowledge-cards/authentication/)、[authorization](/backend/knowledge-cards/authorization/)、[data classification](/backend/knowledge-cards/data-classification/) 這些是各面底下的具體手段。它與 [defense in depth](/backend/knowledge-cards/defense-in-depth/) 的關係是同一組控制的兩種讀法——縱深問「同一條路徑上疊了幾層」，控制面問「這一層歸誰維護」。

分派要區分主責與協作：主責控制面負責第一輪收斂，協作控制面負責擴散管理與回寫。一條風險同時落在兩面以上時（憑證外洩同時是身分問題與偵測問題），沒有指定主責的後果是兩邊都以為對方在處理。六個面各自的責任與承接位置在 [7.B1 防守控制面地圖](/backend/07-security-data-protection/blue-team/defense-control-map/) 展開。

## 可觀察訊號與例子

需要控制面分類的訊號是風險描述完整而 owner 分工鬆散——事件寫得清楚、影響面也算得出來，但「誰要動手」的答案是一個團隊名而不是一個角色，或者每次都落到同一批人身上。另一個訊號是同類風險反覆由不同的人處理，因為歸屬從未被寫下來，每次都靠當下誰有空。

分類本身不解決風險，它解決的是分派。憑證輪替沒做完這件事，判成身分控制面與判成入口控制面會得到不同的主責團隊與不同的驗證方式，而兩種判法都能自圓其說——所以分類的價值在於它被寫下來一次，而不在於它天然正確。

## 設計責任

控制面要交出的是一張對照：每條風險節點歸哪一面、那一面的主責角色是誰、協作角色有哪些。歸屬與角色是兩層，先有歸屬才有角色——順序顛倒的話會先挑到手邊有空的人、再回頭把控制面套上去，而那樣分出來的責任在下一次人員異動時就失效了。分派的結果接 [7.8 的交接模板](/backend/07-security-data-protection/security-routing-from-case-to-service/)：控制面填「承接範圍」那一項，角色填「主責與協作角色」那一項。
