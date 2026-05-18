# Axis candidate evaluation

> **角色**：本卡是 `migration-playbook-methodology` 的支撐型原則、被 [SKILL.md](../../SKILL.md) Step 7 引用。
>
> **何時讀**：發現 6 維 audit 無法 cover 某種 migration / process content 時、候選新 audit 軸時。

## 候選軸狀態（current）

第三輪 batch 後 3 個 axis 候選、各 1 case 驗證：

| 候選軸          | Dogfood case                                                                | 工作量分佈宣稱  | 狀態                                  |
| --------------- | ---------------------------------------------------------------------------- | --------------- | ------------------------------------- |
| Identity        | Vault → AWS Secrets Manager                                                  | 45% identity    | N=1 候選、未 commit                   |
| Consistency     | DynamoDB strong → eventual                                                   | 85% contract review | N=1 候選、未 commit               |
| Residency       | PostgreSQL multi-region GDPR rollout                                         | 40% compliance  | N=1 候選、未 commit（reviewer D 認為應該是 compliance/evidence axis 涵蓋 HIPAA/SOX/PCI、不是 residency-specific）|

## 候選軸升級條件

| 條件                                                                       | 評估方式                                                       |
| -------------------------------------------------------------------------- | -------------------------------------------------------------- |
| 累積 3-5 case / 軸                                                          | 跨不同 vendor / 不同子情境、不只重複同一個 setup               |
| Case 間工作量分佈一致（軸對應的工作量都 > 30%）                            | 工作量 % 用 hedge 詞或 measurement methodology、不是 post-hoc  |
| 軸跟既有 6 維 *彼此* 之間有清楚邊界                                         | 跑 reviewer D 軸間 overlap 質疑、survive 才算邊界清楚          |
| 軸對應的工作量帶 *獨立 stakeholder*（外部 audit / 法務 / DPO / security review）| 確認不是內部 dev work 偽裝                                     |

## 反例：什麼不該升軸

| 候選                                            | 為何不該升                                                                      |
| ----------------------------------------------- | ------------------------------------------------------------------------------- |
| Encryption key rotation                         | 可以塞 application change / operational、不需要獨立軸                          |
| Connection pool config                          | 純 operational sub-item、不該升                                                |
| Tenant isolation                                | 多數情境是 schema 或 application、不獨立                                       |
| Backup strategy change                          | 屬 operational redesign、不獨立                                                 |
| Cost optimization driver                        | 是 driver、不是 axis；6 type 任一都可能 driven by cost                          |
| Performance optimization driver                 | 同上、是 driver 不是 axis                                                       |
| Single feature enhancement                      | 不在 migration playbook scope、用 deep article methodology                      |

關鍵 heuristic：**獨立性 ≠ 軸性**。Backup encryption key、connection pool config、tenant isolation 都可獨立發生、但沒人開「encryption axis / pool axis / tenant axis」— 這些是 *衍生變量*、不是 *獨立軸*。

## Reviewer D 對 3 個候選軸的質疑（未解）

第三輪 audit 揭露 3 候選軸之間有 overlap：

- **Identity ↔ Consistency**：cached credential 變 stale = consistency 議題、但歸 identity
- **Identity ↔ Residency**：EU PII routing = identity-principle-location 跟 residency 都涉
- **Consistency ↔ Residency**：cross-region replication lag 是 consistency contract、同時是 residency boundary

未來 dogfood 必須 *同時* mapping 同一個 case 跑 6 維 + 3 候選軸、看哪些 cell 同時 High → 證明 overlap 或獨立。

## Residency 特例：constraint vs axis

Reviewer D 指出 residency「reverse-constraint」論證沒成立：任何 driver 都 reverse-constraint 下游維度（performance / cost / SLA driver 都是）；reverse-constraint 不是 residency 獨特性質。

真正獨特的是 *合規 evidence 工作量*（DPIA / DPO sign-off / audit trail）— 這指向需要 **「外部 stakeholder obligation」軸**、不一定是「residency 軸」。HIPAA / SOX / PCI / SOC2 都帶類似 evidence 工作量、不只 residency。

候選改名 / 重新定位：

| 原候選名      | 修訂候選名                              | 涵蓋範圍                                  |
| ------------- | --------------------------------------- | ----------------------------------------- |
| Residency     | Compliance / external evidence burden   | GDPR / HIPAA / SOX / PCI / SOC2 / FedRAMP |

這個重新定位等下一輪 batch 跑 HIPAA / SOX case 後再 commit。

## 升軸後的 framework 變動範圍

如果某候選軸真升、framework 需動：

- audit 從 6 維擴 7-9 維
- 對映 type 加 Type G / H / I（candidate type）
- 主導維度優先序重排
- 既有 dogfood retroactive audit 評估（從 N 升到 7-9 維 audit、某些 case 變 multi-axis）
- 「漏類」段更新

這是 *substantive restructure*（Phase 3b）、不是 *meta-acknowledgment*（Phase 3a）；只在 sample 充足時做。

## 自查清單

評估候選軸時：

1. **N ≥ 3 / 軸嗎**？N=1 留候選、N=3 才考慮 commit
2. **跨 vendor / 跨子情境驗證了嗎**？同 vendor 多 case 不算
3. **工作量 % 用 measurement methodology 還是 post-hoc**？post-hoc 的話 evidence weight 降一階
4. **跟既有 6 維任兩維有 overlap 嗎**？有的話必須先解 overlap 才升
5. **軸對應外部 stakeholder 嗎**？沒外部 stakeholder 通常是 internal driver、不獨立
6. **Reviewer D 對軸獨立性的質疑全 survive 嗎**？沒 survive 就回到 N=1 候選狀態

## 跟其他原則的關係

| 原則                                                                  | 關係                                                          |
| --------------------------------------------------------------------- | ------------------------------------------------------------- |
| [six-dimension-audit-framework](./six-dimension-audit-framework.md)   | 父框架 — 6 維 audit 框架的演化機制                            |
| [self-aware-limitation-pattern](./self-aware-limitation-pattern.md)   | Trigger 來源 — limitation 段列的 trigger 對應本卡的升軸條件   |
