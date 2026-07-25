---
title: "Cohort（分組子集）"
date: 2026-07-20
description: "把整體流量或使用者依共享屬性拆成子群、用來限縮實驗範圍或分開量測負載型態"
weight: 408
---

Cohort 的核心概念是依共享屬性把整體切成子集——屬性可以是 tenant、plan、traffic percentage，也可以是操作型態（讀 / 寫 / 混合 / 背景任務）。它的作用有兩層：在可靠性實驗裡限縮 [Blast Radius](/backend/knowledge-cards/blast-radius/)（先打 internal-only cohort 再擴大到全量），在壓測設計裡分開量測不同負載型態（讀寫比例不同、資源消耗模式就不同）。

## 概念位置

Cohort 是「先分組再限定範圍」這個判斷動作的通用名詞，出現在兩條相鄰但責任不同的推理鏈：一條是實驗安全邊界——stop condition 觸發時的降級路徑常是「終止或降到 internal cohort」，把影響面從全量收斂到已知安全的子集；另一條是 [Workload Model](/backend/knowledge-cards/workload-model/) 設計——混合負載若不拆 cohort 分開量測，瓶頸位置會被平均掉、看不出來是哪個路徑先撐不住。

## 可觀察訊號與例子

Blast radius 條款寫「internal-only cohort」時，代表這個子集有明確邊界（員工帳號、白名單 tenant），實驗擴大前要先驗證這個邊界沒有洩漏到真實客戶流量。壓測設計上，API gateway 層可能整體讀主導，但 checkout 或 order-create 路徑的寫入比例明顯偏高——不拆開量測，混合流量的壓測結果會讓 checkout 路徑的瓶頸被讀路徑的餘裕稀釋掉。

## 判讀方式

看到「範圍該多大」或「這批負載跟那批負載能不能混著量」時，先問這批對象共享哪個屬性、這個屬性是否是影響失敗機率或資源消耗的關鍵維度。若答案是肯定的，先拆 cohort 再往下設計；直接打全量或混合量測，看到的訊號會是被平均稀釋過的假象；cohort 邊界怎麼跟 stop condition 與回退設計組合成完整的實驗安全邊界、見 [6.20 實驗安全邊界](/backend/06-reliability/experiment-safety-boundary/)。
