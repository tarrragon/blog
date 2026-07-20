---
title: "CDP"
date: 2026-05-19
description: "辨識一個工具是不是客戶資料平台、或判讀它在賽道分類軸上的位置時，用來區分跨行業單一功能層與垂直 SaaS 的差異"
weight: 4
tags: ["business", "knowledge-cards", "business-model"]
---

CDP 的核心概念是「Customer Data Platform，客戶資料平台」—把分散在各系統的客戶資料（網站、App、電商、客服、廣告）集中起來，建立統一客戶檔案，給行銷、銷售、客服使用。代表公司是 Segment（已被 Twilio 收購）、mParticle、Tealium。CDP 位於資料庫與行銷工具之間的整合層，屬於賺工作流程錢的應用層 [SaaS](/business/knowledge-cards/saas/)，常被拿來跟賺底層資源錢的基礎設施（如 AWS）做對比。

## 概念位置

在 SaaS 的分類軸上，CDP 是[跨行業通用（Horizontal SaaS）](/business/knowledge-cards/horizontal-saas/)的[單一功能層（Niche）](/business/knowledge-cards/niche-market/)——任何有客戶的行業都需要整合客戶資料（行業廣度上是 horizontal），但它只做「資料整合與啟用」這一個功能層、不是一整套行銷套件（功能廣度上落在 niche）。這個位置容易跟[垂直 SaaS（Vertical SaaS）](/business/knowledge-cards/vertical-saas/)混淆：垂直 SaaS 把單一行業的隱性知識編碼進產品、綁定一個行業，CDP 恰好相反—跨所有行業但只切一層功能。分類清楚才看得出它的結構壓力：跨行業的單一功能層會被兩邊夾，上方被全功能套件 bundling、側面被垂直方案分食。

## 可觀察訊號與例子

CDP 客戶通常是有多個資料來源、又想做精準行銷的中大型企業。判斷某個工具是不是 CDP，看它是否同時做三件事：跨來源資料整合、統一客戶身份識別（identity resolution）、把整合後的資料推送給下游行銷工具。

## 判讀方式

讀到「CDP」時，先確認它在文章裡的角色—它常被當成「應用層 SaaS vs 基礎設施」的對比例子，不一定是文章主題。要完整判讀 CDP 這個賽道值不值得投、值不值得進，[賽道與商業模式判讀框架](/business/reading-frameworks/track-business-model-reading/)用它當 worked example 走過一遍：跨行業單一功能層的兩邊夾、資料重力護城河的可拆解性、以及「整合客戶資料是剛需、但用獨立 CDP 產品來做不是剛需」這組決定成敗的訊號。
