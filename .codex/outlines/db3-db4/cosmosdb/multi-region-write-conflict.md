# Cosmos DB Multi-Region Write：active-active、LWW、custom merge、conflict feed

> **Status**: L5 outline skeleton（planning artifact、非 published article）。寫作參照 [vendor-article-spec](/backend/01-database/vendor-article-spec/) 與 [vendor deep article methodology](/posts/vendor-deep-article-methodology/)。

## 問題情境（Production pressure）

- 啟動壓力：產品要 global active-active（每個 region 都能寫、低延遲）、Cosmos DB 是 AP 系統不像 Spanner 用 quorum 強一致、跨 region 寫同一筆 document 必然有 conflict；團隊不知道「conflict 真的發生時、誰贏 / 怎麼處理 / 業務語義保不保得住」
- 讀者徵兆：「multi-region write 開了、user 在 A region 寫『加入購物車』、B region 寫『移除購物車』、最後哪個贏」「LWW 是用 timestamp 決定、那 client clock skew 不就破壞了嗎」「conflict feed 是什麼、要不要消費」「multi-region write 開了之後 consistency level 還能設 Strong 嗎」
- 真實壓力：購物車跨 region 寫入丟失、遊戲玩家狀態跨 region 衝突回滾、IoT device 跨 region 寫 telemetry 後消失
- Case anchor: [9.C11 Minecraft Earth](/backend/09-performance-capacity/cases/minecraft-earth-cosmos-db-global/) — AR 遊戲跨 region 寫入、session consistency + multi-region；[9.C21 ASOS](/backend/09-performance-capacity/cases/asos-cosmos-db-black-friday/) Black Friday 全球零售

## 核心機制（Vendor-specific mechanism）

- Cosmos DB 是 AP 系統（CAP 三選二）、放棄跨 region linearizability 換取 multi-region write 可用性
- Multi-region write 的兩個前置條件：
  - account 開啟 `enableMultipleWriteLocations`
  - consistency level 不能設 Strong（multi-region write 跟 Strong 互斥、時間敏感 claim、查最新文件）
- Conflict 偵測：同一 document（partition key + id）在多 region 並發寫入、Cosmos DB 偵測為 conflict
- 三種 conflict resolution policy：
  - **Last-Writer-Wins (LWW)**（預設）：用 `_ts` 或自訂 numeric property、value 大的贏；副作用是 clock skew 直接影響「誰贏」
  - **Custom merge with stored procedure**：寫一個 JavaScript stored proc、conflict 時 Cosmos DB 呼叫、proc 回傳 merge 結果（如：購物車 merge = union 兩邊 items）
  - **Conflict feed (manual)**：Cosmos DB 把 conflict 寫入 conflict feed、不自動解決、app 自行消費並 reconcile
- 跟 DynamoDB Global Tables 對比：DynamoDB 也是 LWW、無 custom merge、無 conflict feed
- 跟 Spanner 對比：Spanner 用 Paxos quorum、不會有 conflict（CP 系統、可用性換一致性）
- 對應 knowledge card：[stale-read](/backend/knowledge-cards/stale-read/)、[rpo](/backend/knowledge-cards/rpo/)、[rto](/backend/knowledge-cards/rto/)

## 操作流程（Operations）

- 開啟 multi-region write：

  ```bash
  az cosmosdb update --enable-multiple-write-locations true \
    --locations regionName=eastus failoverPriority=0 \
    --locations regionName=westeurope failoverPriority=1
  ```

- 設定 LWW policy（container 層）：

  ```json
  "conflictResolutionPolicy": {
    "mode": "LastWriterWins",
    "conflictResolutionPath": "/customTimestamp"
  }
  ```

- 設定 custom merge：

  ```json
  "conflictResolutionPolicy": {
    "mode": "Custom",
    "conflictResolutionProcedure": "dbs/mydb/colls/mycoll/sprocs/resolveCart"
  }
  ```

- 設定 conflict feed only：

  ```json
  "conflictResolutionPolicy": { "mode": "Custom" }
  ```

  （沒指 procedure、conflict 全進 feed、app 自己消費）
- 消費 conflict feed：SDK `ReadConflictsAsync()` / 用 Change Feed Processor pattern
- 驗證點：跨 region 並發寫測試、觀察 conflict count / resolution result；conflict feed 不積壓

## 失敗模式（Failure modes）

- 全用 LWW + 用 server timestamp：clock skew 在 ms 級可能讓「先寫的反而贏」、業務邏輯破洞
- 業務語義不適合 LWW：購物車（要 union）、計數器（要 sum）、status 機器（要狀態圖）全用 LWW = 資料丟失
- Custom merge stored proc 沒測 edge case：proc throw exception、Cosmos DB 行為退回？conflict 留 feed？不同行為不同 recovery
- 不消費 conflict feed：選 manual mode 後忘記 feed consumer、conflict 累積、後續分析失準
- 期待 multi-region write 還有 Strong consistency：兩者互斥、開啟 multi-region write 後 Strong 自動 downgrade（或拒絕設定、時間敏感）
- 跨 region 寫入後立即同 session read 看不到：session token 沒跨 region 傳遞、看似 inconsistency 其實是 session 沒對齊
- Region 故障時 failover：multi-region write 已是 active-active、不需要 manual failover；但若用了 priority、failover 邏輯要審

## 容量與觀測（Capacity & observability）

- 必看 metric：`ConflictCount`、`ReplicationLatency` per region pair、conflict feed lag
- Conflict rate 監控：正常 < 0.01%、突增代表 hot key 或 region 同步異常
- Cost 影響：multi-region write 開啟後、寫入成本 × region 數（每個 region 都 replicate）
- 回到 [4.20 Observability Evidence Package](/backend/04-observability/observability-evidence-package/) 把 conflict rate 當 reliability evidence
- 回 [9.6 容量規劃模型](/backend/09-performance-capacity/capacity-planning/) 把 multi-region write cost multiplier 進 sizing
- Alert：conflict rate > 0.1%、conflict feed lag > 5 min、cross-region replication lag > SLA

## 邊界與整合（Boundary & next steps）

- Sibling deep articles：[consistency-levels-engineering](./consistency-levels-engineering.md)（multi-region write 跟 Strong 互斥）、[partition-key-design](./partition-key-design.md)（hot partition 會放大 conflict）、[ru-cost-model-sizing](./ru-cost-model-sizing.md)（multi-region cost × region 數）
- 跟 [Spanner multi-region](/backend/01-database/vendors/spanner/) 對比：CP vs AP 選擇、無 conflict vs LWW/custom
- 跟 DynamoDB Global Tables 對比：兩者都 LWW、Cosmos DB 多 custom merge + conflict feed
- 跟 1.x 章節：[1.11 全球分散式 OLTP](/backend/01-database/global-distributed-oltp/) 把 multi-region write 模式並陳
- Anti-recommendation：single-region write + cross-region read replica 在大多數情況更便宜、更易推理；只有 *write residency* 是產品契約時才升 multi-region write

## 寫作前置 checklist

- [ ] case anchor 確認：9.C11 Minecraft Earth（active-active write）+ 9.C21 ASOS 補季節壓力
- [ ] knowledge card 雙引用：stale-read、rpo、rto
- [ ] sibling 對比：Spanner（CP 無 conflict）、DynamoDB Global Tables（LWW only）
- [ ] 預估寫作長度：300-360 行（3 種 resolution policy + 7 失敗模式 + 跨 vendor 對比）
