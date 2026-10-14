---
title: "Knowledge-Centered Service（KCS）"
date: 2026-10-14
description: "客服或工程查完一則回報之後答案沒有留下、同一類問題每次都重查，或要決定知識文章由誰在什麼時候寫時，查 KCS 在處理回報的當下寫入與修正知識的做法"
weight: 484
tags: ["backend", "incident-response", "customer-support"]
---

Knowledge-Centered Service（KCS）是由 Consortium for Service Innovation 維護的知識管理方法，做法是把寫知識文章放進處理回報的工作本身：處理回報時先搜尋既有的文章，找到就用並順便確認它還正確，找不到就在解決之後當場寫一篇，用提問者自己的說法描述問題，讓下一個人搜尋得到。它是 [Tiered Support（分層支援）](/backend/knowledge-cards/tiered-support/) 各層之間累積答案的方式，[Known Error（已知錯誤）](/backend/knowledge-cards/known-error/) 的條目也常經由它寫下。

## 概念位置

KCS 把處理回報的流程稱為 Solve Loop，Practices Guide 列出四個動作：在當下記錄（capture）新的知識、把它整理（structure）成人與機器都能使用的形式、重用（reuse）既有的知識避免重做、在使用時改進（improve）它，讓它保持正確。另有兩個原則：「Reuse is Review」指每一次使用一篇文章就是在檢查它；「Flag It or Fix It」指使用文章時發現要改的地方，有把握而且有修改權限的人當場改掉，否則標記出來交給有權限的人。寫下的文章與 [Known Error（已知錯誤）](/backend/knowledge-cards/known-error/) 清單的差別在範圍：已知錯誤只收還沒永久修正的問題，KCS 的文章也收使用者操作與設定這類本來就不需要修正的問題。它與事後集中寫文件的差別在時機：處理的當下，處理的人還記得細節，提問者的說法也還在手上；事後整理時兩者都已經不在。

## 可觀察訊號與例子

短網址服務的工程查完一則「短網址突然失效」，原因是那一批網址在服務改了有效期限之後到期。依 KCS 的做法，工程在回覆客服的同時寫一篇文章，標題用使用者的說法「短網址突然打不開」，內容寫判斷方式（查到期日）與答覆；下一則同樣的回報，客服搜尋得到這篇，當場答覆。

## 判讀方式

判斷一個組織的知識是否在累積，看同一類回報轉到工程的次數是否下降。次數不降時，先查答案有沒有被寫下（處理流程裡沒有寫文章這一步），再查寫下的文章能否以使用者的說法搜尋到（標題用了內部術語時搜尋不到）。客服與工程之間把查證結果寫回的流程，見 [8.24 客服回報的處理](/backend/08-incident-response/support-escalation-and-engineering-reply/#重複出現的回報查證結果寫回知識文章告警規則與查詢工具) 的〈重複出現的回報：查證結果寫回知識文章、告警規則與查詢工具〉。
