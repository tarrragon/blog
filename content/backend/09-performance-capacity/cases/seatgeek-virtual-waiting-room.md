---
title: "9.C16 SeatGeek：DynamoDB + Lambda 打造的虛擬等候室"
date: 2026-05-12
description: "SeatGeek 用 DynamoDB 4 張表 + Lambda Bouncer 實作 flash-sale 的准入控制（等候室）、取代第三方 waiting room 服務"
weight: 16
tags: ["backend", "performance", "capacity", "case-study", "compute", "aws", "flash-sale-spike"]
---

這個案例的核心責任是說明「flash-sale 場景下、准入控制（等候室）如何明確設計」；這裡的明確排隊指決定誰、何時進入受保護區的准入控制，依呼叫者分配配額的限流是另一層。跟 [Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/) 的「DynamoDB 隱性緩衝」是姊妹案 — Tixcraft 依架構圖推論是用 DynamoDB 作為寫入緩衝吸收洪峰、SeatGeek 走更上游一層、在用戶到達系統前就明確排隊。兩種架構並存於票務業界、適合不同業務場景。

## 觀察

SeatGeek Virtual Waiting Room 架構（引自 [AWS Architecture Blog](https://aws.amazon.com/blogs/architecture/build-a-virtual-waiting-room-with-amazon-dynamodb-and-aws-lambda-at-seatgeek/)）：

| 元件                  | 角色                                                         |
| --------------------- | ------------------------------------------------------------ |
| Protected Zone table  | 紀錄受保護資源的 metadata（哪個 event 受 waiting room 保護） |
| Counters table        | 紀錄「每分鐘發出多少 access token」                          |
| User Connection table | 紀錄訪客 token 與 connection ID（原文沒寫連線協定）          |
| Queue table           | 把訪客 token 對映到 access token（排隊序號）                 |
| Bouncer Lambda        | 配發與失效 access token 的「守門員」                         |
| API Gateway           | 接受外部請求、轉發 Bouncer                                   |

業務動機：取代「第三方 waiting room 服務」、原因是缺乏設定與客製化能力、可同時設定的活動數受限於人工流程，以及拿不到自訂指標（例如顧客在佇列裡等多久才放棄）。

原文另外寫了幾件事：守門判斷（gate keeper）的第一版跑在 Fastly Compute@Edge，也就是在 CDN 邊緣決定請求進受保護區還是導去等候室；等候室有兩種模式（也可以先後組合），Waiting Room 模式在開賣前把請求導到另一頁、到時間依預設的吞吐量放行，Queueing 模式讓受保護區只容納預設的並發人數、其餘依 FIFO 排隊；受保護區的上限同時是為了防止超賣；等候室本身會遭受 DDoS，建議前面放 AWS Shield 與 WAF；等候室也能在「a load spike, while more resources (EC2 instances) are being launched」時使用。

關鍵機制：

1. **Token = 庫存單位**：access token 總數 = 可售票數量。沒拿到 token 的用戶被導到 waiting room 頁面（等候頁顯示什麼，原文沒寫）。
2. **FIFO 或 priority queue**：可以按進入順序、也可以對 VIP 客戶優先發 token。
3. **Token 失效機制**：原文寫 token「expire when tickets are purchased or when the customer exits」；失效之後是否釋放給下一位，原文沒寫。

## 判讀

SeatGeek 案例揭露三個准入控制（等候室）的設計重點。

1. **隱性緩衝 vs 明確排隊是兩種架構取捨**：[Tixcraft 模式](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)「全部塞進 DynamoDB」、用戶以為下單成功、實際處理排隊。SeatGeek 模式「明確告訴你排隊位置」、用戶看得到等待時間。前者犧牲透明度換流量吸收、後者犧牲流量吸收換體驗。對應 [9.10 Production-Side 驗證](/backend/09-performance-capacity/) 的用戶體驗 vs 系統行為取捨。
2. **等候中的連線是 stateful 容量單位**：原文的 User Connection table 為每個連上 API Gateway 的訪客記一筆 visitor token 與 connection ID，所以等候人數本身就是要規劃的容量；同時等候人數有多大、連線怎麼維持，原文沒有寫，要自己壓測。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的 stateful service 容量規劃。
3. **限流粒度 = 業務粒度**：「每分鐘發 N 個 token」這個參數直接決定「每分鐘成交 N 張票」。N 太小、賣不完；N 太大、後端撐不住。N 不是技術參數、是業務 × 後端容量的協商結果。對應 [9.6 容量規劃模型](/backend/09-performance-capacity/) 把容量規劃跟業務 KPI 對接。

需要警惕的判讀盲點：

- AWS Architecture Blog 沒提具體流量數字（concurrent users、queue depth、throughput）。讀者無法直接套用到自家容量規劃、必須自己壓測。
- DynamoDB 4 張表的設計 *看似簡單*、實際上每張表的 partition key / sort key 設計都要仔細想。複製這個架構不等於拿到 SeatGeek 的吞吐能力。
- 「token expiration」機制如果設計不好（例如用戶關閉瀏覽器、token 沒回收）、會導致「排隊很長但實際空著」、影響轉換率。

## 策略

可重用的工程做法：

1. **明確 vs 隱性限流的選擇**：高價值門票（演唱會、限量周邊）適合明確排隊（用戶願意等）；高頻低價值商品（FCFS 折扣）適合隱性緩衝（讓用戶快速完成）。
2. **Virtual Waiting Room 是 stateful service、要規劃連線容量**：不是 stateless Lambda 一招到底、需要維持連線的 gateway 與 DynamoDB state store（WebSocket 是推論，原文只寫 connection ID）。對應 [05 部署平台模組](/backend/05-deployment-platform/) 的混合架構。
3. **token 過期策略要寫進設計初稿**：用戶離開、付款超時、瀏覽器當掉 — 三種狀況的 token 回收邏輯都不一樣、要明確設計。
4. **可觀測性是「自建 waiting room」勝過「第三方」的關鍵**：SeatGeek 換掉第三方的理由之一是拿不到自訂指標，原文舉的例子是顧客在佇列裡等多久才放棄；其餘指標（token issue rate、queue depth distribution、conversion funnel）是推論。對應 [04 可觀測性模組](/backend/04-observability/)。

跨平台等效：GCP Cloud Functions + Firestore + Pub/Sub；Azure Functions + Cosmos DB + SignalR；自建 Redis（INCR / TTL）+ WebSocket gateway（Soketi / Socket.IO + Redis adapter）都可以實作對等架構。AWS 還推出官方 [Virtual Waiting Room on AWS](https://aws.amazon.com/solutions/implementations/virtual-waiting-room-on-aws/) Solutions、是 SeatGeek 模式的可重用版本。

## 下一步路由

- 想設計等候室與准入控制 → [9.15 無預警瞬時大流量：流量來源辨識、擴展緩衝、請求優先等級、准入控制、體積型攻擊與退路](/backend/09-performance-capacity/unplanned-traffic-surge/) 的〈准入控制：虛擬等候室（virtual waiting room）、waitlist 與事前註冊〉
- 對照隱性緩衝模式 → [Tixcraft](/backend/09-performance-capacity/cases/tixcraft-ticketing-flash-sale-spike/)
- 想做 conversion funnel 可觀測性 → [04 可觀測性模組](/backend/04-observability/) + [04.16 SLI / SLO 訊號](/backend/04-observability/sli-slo-signal/)
- 想了解 stateful service 容量規劃 → [05 部署平台模組](/backend/05-deployment-platform/) + [9.5 瓶頸定位流程](/backend/09-performance-capacity/)

## 引用源

- [Build a Virtual Waiting Room with Amazon DynamoDB and AWS Lambda at SeatGeek](https://aws.amazon.com/blogs/architecture/build-a-virtual-waiting-room-with-amazon-dynamodb-and-aws-lambda-at-seatgeek/)
- [Virtual Waiting Room on AWS (Solutions)](https://aws.amazon.com/solutions/implementations/virtual-waiting-room-on-aws/)
- [How to manage peak traffic on AWS using Queue-it's virtual waiting room](https://aws.amazon.com/blogs/apn/how-to-manage-peak-traffic-on-aws-using-queue-its-virtual-waiting-room/)
