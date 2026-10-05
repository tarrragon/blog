---
title: "Minimum Supported Version（最低支援版本）"
date: 2026-10-05
description: "要讓舊版行動 App 停止使用時：服務方保存的版本下限、客戶端啟動檢查與伺服器端拒絕兩層各自涵蓋哪些版本，以及提高它之前要查的使用者數與作業系統下限"
weight: 448
tags: ["backend", "api-design", "mobile", "versioning", "knowledge-card"]
---

Minimum Supported Version（最低支援版本）的核心概念是「由服務方保存一個版本下限，低於它的客戶端不再被服務，使用者要更新才能繼續使用」。它是服務方讓自家行動 App 舊版退場的手段；桌面客戶端把同一個值放在 [Update Feed](/ci/knowledge-cards/update-feed/) 裡。公開 API 的整合方要自己改程式，服務方對它們只能在退場日拒絕舊呼叫，沒辦法把使用者帶到更新畫面。可先對照 [Deprecation Lifecycle](/backend/knowledge-cards/deprecation-lifecycle/) 與 [Feature Flag](/backend/knowledge-cards/feature-flag/)。

## 概念位置

最低支援版本和 deprecation 都是讓舊行為退場的工具，作用對象不同：[Deprecation Lifecycle](/backend/knowledge-cards/deprecation-lifecycle/) 讓一個 API 退場，對象是所有還在呼叫它的消費者；最低支援版本讓一個客戶端版本退場，對象是裝著那個版本的使用者。兩者常一起用：舊 API 只剩舊版 App 在呼叫時，先提高最低支援版本讓舊版 App 退場，再讓舊 API 退場。它的值通常放在 [Remote Config](/backend/knowledge-cards/remote-config/) 裡（App 向服務方讀取、不必更新就能改的一組設定值），和 [Feature Flag](/backend/knowledge-cards/feature-flag/) 共用同一套讀取機制。消費者依更新能力的分類見 [API Consumer Shape](/backend/knowledge-cards/api-consumer-shape/)。

## 可觀察訊號與例子

需要最低支援版本的訊號是：後端要做不相容的修改、舊版有安全問題、或舊版呼叫的 API 要退場，而依版本統計的使用者數顯示舊版仍有人在用。

實作分兩層。客戶端啟動檢查：App 啟動時讀取最低支援版本並比較，低於就顯示更新畫面；常見做法另有一個「最新版本」值，低於它但高於最低支援版本時只顯示可關閉的提示。伺服器端拒絕：後端依請求帶的版本拒絕過舊的客戶端，回一個專用的「需要更新」錯誤碼，App 從內建了這個錯誤碼處理的那一版起，收到它就顯示更新畫面。客戶端啟動檢查與錯誤碼處理若是後來才加入，加入之前上架的版本被拒之後只會顯示當時寫好的通用錯誤畫面，所以兩者都要從 App 最早上架的版本就內建。完整推導見 [11.15 自家行動 App 與後端的 API 契約：版本回報、最低支援版本、商店審核下的上線順序、分階段發布、熱更新與回退手段](/backend/11-api-design/mobile-client-api-contract/)。

## 設計責任

最低支援版本每個平台一個門檻，客戶端啟動檢查與伺服器端拒絕讀同一份；要個別拒絕某個壞掉的版本，另外由伺服器端維護封鎖清單。修改要有權限控管，並檢查新門檻不得高於該平台已經全量上架的最新版本，以及要保留的舊系統使用者能裝的最後一版——這個值改錯一次，所有使用者都會被硬阻擋。

提高之前，先分出拿不到新版的使用者，他們不能被硬阻擋：新版還沒在商店全量上架（Google Play 分階段推出未到 100%）、裝置的作業系統低於新版的下限、以及加入版本回報之前的舊版（請求不帶版本、彼此分不開，只能整群處理）。剩下的才是這次提高的代價，人數從依版本的活躍使用者數估計。比較版本時把版本字串拆成整數逐段比較，相同再比建置號；iOS 的建置號換版本字串時可以重新計數，所以只在版本字串相同時比較它。直接比字串時 `"1.10.0"` 會排在 `"1.2.0"` 前面。客戶端內建的預設最低支援版本設成不會擋下任何已上架版本的值，讀不到遠端設定時就不擋。
