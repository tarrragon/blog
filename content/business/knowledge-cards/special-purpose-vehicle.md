---
title: "Special Purpose Vehicle（特殊目的實體，SPV）"
date: 2026-11-12
description: "讀到資產由新成立的融資實體持有並出租、債務不在發起公司報表上時，判斷風險實際由誰承擔"
weight: 121
tags: ["business", "knowledge-cards", "financing"]
---

特殊目的實體（special purpose vehicle，SPV）是為單一交易設立的法律實體：它持有特定的資產、為這批資產借錢，債權人只能拿這批資產與實體本身的現金流求償。設立的目的是隔離：資產與債務放在 SPV，不放在發起交易的公司（設備賣方、承租方或投資人）的資產負債表上，發起公司的其他債權人也碰不到 SPV 的資產。隔離只決定帳放在哪裡；風險是否回到發起公司，要看它對 SPV 提供了哪些[殘值擔保](/business/knowledge-cards/residual-value-guarantee/)、保證或承租承諾。

## 跟其他概念的關係

SPV 與[合併報表](/business/knowledge-cards/consolidated-financial-statements/)的範圍直接相關：發起公司若實質控制 SPV，會計準則要求把它併進合併報表，隔離效果就消失；所以 SPV 的股權與決策權通常安排在發起公司以外的融資夥伴手上。

在算力融資裡，SPV 是出租方：它向設備賣方買進機櫃，以[融資租賃](/business/knowledge-cards/finance-lease/)的方式租給承租方，用承租方的租金償還銀行貸款。承租方記使用權資產與租賃負債，賣方記營收，SPV 記設備與債務，三方的報表各自只看到交易的一段。

## 可觀察訊號與例子

Broadcom 為一位未點名的客戶安排的 AI 機櫃租約，是 SPV 接手出租方的實例。這位客戶在銀行團新聞稿與媒體報導裡是 Anthropic，Broadcom 10-Q 揭露的 420 億美元可轉換本票條款也跟 Anthropic S-1/A-2 的協議相同。Anthropic 2026-11-10 提交的 S-1/A-2 寫，五年期主設備租約的出租方原本是 Broadcom，「及轉讓後的特定融資實體」：2026 年第二季 Broadcom 把其中一份主租約的部分權利轉讓給另一個第三方，2026 年 10 月再把 2026 Lease Arrangement 一部分設備的權利義務轉讓給新成立的 SPV，兩次轉讓都沒有增加 Anthropic 的租金總額。Broadcom 2026-10-27 的 8-K 寫，融資夥伴承接一部分機櫃採購合約與租約，Broadcom 對新成立的 SPV 提供殘值支持；依時間推論，這就是 S-1 寫的 10 月那一次轉讓（S-1：Broadcom 把 2026 Lease Arrangement 一部分設備的權利義務轉給新成立的特殊目的融資實體）。依 SPV 的一般結構推論，這個 SPV 持有那一部分的機櫃與購買機櫃的債務，兩份申報都沒有直接寫出 SPV 的資產負債。第二季那一次轉讓的出資方，Broadcom 10-Q 只寫一家融資夥伴（a financial partner）。沒有轉讓的部分，出租方仍是 Broadcom。Anthropic 把這批租約以[融資租賃](/business/knowledge-cards/finance-lease/)認列，帳上記的是使用權資產與租賃負債，不是機櫃與購買機櫃的借款。Broadcom 對承接租約的實體提供的兩份擔保讓它保留了機櫃價值下跌的風險，兩份的責任公式與金額寫在[殘值擔保](/business/knowledge-cards/residual-value-guarantee/)卡。

同一份 S-1/A-2 也寫出合併範圍的實際劃分，可以當成「實質控制就併表」的實例：Anthropic 合併了「為融資與部署算力而成立的某些 VIE」。VIE 是變動利益實體（variable interest entity），US GAAP 對這類實體不看表決權，改看誰主導它的主要活動並承擔它的損益來決定由誰併表。2026-09-30 這些 VIE 的資產約 27 億美元、負債約 28 億，Anthropic 保證其中部分債務；另外有它不合併的出租方 VIE。10 月承接的那一部分，依 Reuters 報導由銀行團與 Blackstone 出錢讓 SPV 買機櫃（[Anthropic 的算力融資結構](/business/ai-infrastructure/anthropic-compute-financing/)依 Reuters 報導整理了這筆交易的參與者與錢流），而 S-1 沒有寫這個 SPV 屬於合併的還是不合併的那一種，所以單從承租方的報表判斷不出這個 SPV 的債務是否已經進了 Anthropic 的合併報表。

## 判斷條件與後果

- **發起公司對 SPV 沒有任何擔保或回購承諾**：資產與債務的風險確實由 SPV 的股東與債權人承擔，發起公司的報表反映的就是它實際的曝險。
- **發起公司提供殘值擔保、保證或在違約時承接租約的選擇權**：資產負債表上沒有債務，風險卻在違約時回到發起公司；擔保以[公允價值](/business/knowledge-cards/fair-value/)認列，Broadcom 在 10-Q 判定它的擔保公允價值不重大，其他擔保方怎麼評價，要看各自的附註；讀附註裡的最大責任金額，才估得出隔離實際隔掉了多少。
- **SPV 的唯一收入來源是一家承租方的租金**：SPV 的債務品質等於那家承租方的信用，SPV 的設立隔離了帳務，沒有分散信用風險。
- **SPV 的資產是技術汰換快的設備**：處分價值隨新世代產品推出而下降，債權人與擔保方面對的損失會比以不動產為資產的 SPV 大，理由是承租方違約多半發生在需求轉弱的期間，而二手設備的價格在同一段期間也偏低；這是依機制的推論，AI 機櫃目前沒有公開的二手成交資料可以驗證。
