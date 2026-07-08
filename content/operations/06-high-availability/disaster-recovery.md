---
title: "Disaster recovery 策略"
date: 2026-07-03
description: "設計災難復原時，先確認恢復路徑走得通再談 RTO/RPO、用 restore drill 把估值變量值、以及知道恢復不是切回流量就結束"
weight: 4
tags: ["devops", "high-availability", "disaster-recovery", "rto-rpo", "restore-drill"]
---

Disaster recovery 回答「災難發生後，服務能不能回來」。它有一條先於一切的原則：先確認路徑，再談速度。一份 backup 在被 restore 驗證過之前，它只是備份、不是復原能力；一套 failover 的 config 在沒跟 production 對齊之前，它只是文件、不是可執行的操作路由。RTO 跟 RPO 這些速度指標，是在「路徑確實走得通」之後才有意義的——路徑不通，再漂亮的目標數字都是空的。

## RTO 與 RPO：是承諾，不能是猜測

RTO（恢復時間目標）是「多久之內要恢復服務」，RPO（資料遺失目標）是「最多能丟多少資料」。這兩個數字有一個常見的陷阱：它們常常是估值、不是量值。一個寫在文件上「4 小時 RTO」的承諾，如果從沒真的跑過一次完整恢復，那 4 小時只是猜的——實際上 restore 本身可能就要 6 小時，這個承諾是空的。

量 RTO 要量完整的時間，不只是資料還原那一段。真實的 RTO 從「決定啟動恢復」算起，涵蓋判斷、決策、執行、驗證，一路到服務真的恢復——中間任何一段的時間都算數。RPO 則由冗餘的資料同步方式決定：同步副本的 RPO 接近零，非同步跨 region 副本的 RPO 是那個複製延遲的窗口，這條在 [冗餘設計模式](/operations/06-high-availability/redundancy-patterns/) 講過。要讓這兩個數字從猜測變成承諾，只有一條路：用 restore drill 實際量測，拿量到的真實值去更新承諾。

## RTO 由備援的就緒程度決定

要達到某個 RTO，付出的成本取決於備援平時準備到多「熱」，這條光譜有公認的命名。最冷的是純備份還原（backup-restore）——平時只有備份、故障時從零重建環境，最便宜、但 RTO 最長。往上是 pilot-light——核心元件（如資料庫的副本）常態開著、其餘按需啟動，故障時把周邊點亮，中等成本與 RTO。再往上是 warm-standby——一個縮小規格的完整環境常態運轉、故障時放大到全量，RTO 更短。最熱的是 hot-standby（即 [冗餘設計模式](/operations/06-high-availability/redundancy-patterns/) 的 active-passive 熱備）——全規格備援常開、秒級到分鐘級切換，RTO 最短、成本最高。RTO 承諾要往哪一級靠，跟停機的商業代價一起算，見 [高可用的成本](/operations/06-high-availability/ha-cost/)。

## Restore 驗證的三個層次

備份的價值只在還原的那一刻才被證明。一個從沒被 restore 過的 backup，等於一個沒被驗證過的假設。restore 驗證要覆蓋三個層次。第一層是資料完整性——用 row count 比對、checksum、對帳查詢確認資料真的完整，這裡的失敗模式是 backup 的時段跨越了某個批次 job、或增量備份的鏈條中間斷了。第二層是服務可用性——config、secret、schema 版本、連線池這些元件 restore 之後可能失效，要跑 smoke test 加健康檢查確認服務真的起得來，不是只有資料回來了。第三層是恢復時間量測——這次 restore 實際花多久，拿去校準 RTO 承諾。

這三層裡最容易被跳過的是「真的跑一次」。backup 有排程、每天都在備，但 restore 從來沒跑過——而 restore 是唯一能證明備份可用的手段。備份排程做得再勤，沒驗證過還原，就是在累積一堆不知道能不能用的檔案。

## 恢復不是切回流量就結束

一個危險的誤解是把「切回流量」當成恢復完成。真實的恢復往往在切回流量之後還有很長一段。有遊戲平台的一次故障中斷了 73 小時，拉長的原因不在切換本身——是資料一致性要重建、快取要預熱、依賴服務要按正確順序啟動，這些在流量切回來之後才開始、而且各自要花時間。恢復的實際成本包含這些「切回之後」的收尾，把它們算漏，RTO 就會嚴重低估。

恢復還要分批、不能一次全開——這條分批推進、恢復工具不依賴故障控制面的紀律，跟 [Failover 機制](/operations/06-high-availability/failover-mechanism/) 的恢復順序是同一套，在那裡展開。DR 這裡要補的是它跟 RTO 的關係：分批恢復本身要花時間、每批之間的驗證也要花時間，這些全部算進 RTO——把「切回之後」的收尾與分批的時間算漏，RTO 就會嚴重低估。

## 演練節奏：計畫不演練就會漂移

DR 的能力會隨系統演進而悄悄失效——一份寫在 wiki、過去 12 個月沒演練過的 DR plan，基本上不可信，因為這 12 個月裡 production 一直在變、plan 早就跟現實漂移了。維持 DR 能力靠固定節奏的演練，不同類型有不同頻率：桌面推演（走一遍決策路由與角色分工）每季、局部 failover（切一個子系統、驗自動化腳本在 production 真的可執行）每半年、全區 failover（整區從災難回來、輸出 RTO/RPO 與資料一致性檢查）每年、資料還原演練每季。演練暴露的缺口要回寫進技術債追蹤——高優先的下個發布週期前修、次要的排入固定追蹤，不能演練完就散會。

## DR 與 chaos 的分工

DR 演練跟 chaos testing 容易混淆，但驗的是不同的事。chaos 驗「故障持續期間，服務能不能維持」——成功條件是穩態不被破壞、實驗結束系統還在運作；DR 驗「災難發生後，能不能回來」——成功條件是恢復路徑可執行、且符合 RTO/RPO，要經歷一次完整的失效加恢復循環。兩者的交集是 failover drill：chaos 關心切換期間退化多少，DR 關心切換完成後恢復的品質。要驗證高可用，兩者都需要——一個保證撐得住，一個保證回得來。

## 下一步路由

- RPO 的來源——同步 vs 非同步副本 → [冗餘設計模式](/operations/06-high-availability/redundancy-patterns/)
- 恢復順序的循環等待與分批恢復 → [Failover 機制](/operations/06-high-availability/failover-mechanism/)
- 這一切要付多少、值不值得 → [高可用的成本](/operations/06-high-availability/ha-cost/)
- DR 與 rollback 演練的完整方法 → [backend DR 與 rollback 演練](/backend/06-reliability/dr-rollback-rehearsal/)
