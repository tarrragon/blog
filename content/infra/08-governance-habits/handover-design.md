---
title: "職務交接與存取撤銷設計"
date: 2026-06-26
description: "人員異動時的存取撤銷順序、credential rotation、最小交接清單，以及讓交接成本結構性降低的 infra 設計原則"
weight: 3
tags: ["infra", "governance", "handover", "access-revocation"]
---

人員異動（離職、轉調、承包合約結束）是常態營運事件。基礎設施的設計決定了這件事的成本：如果環境的建立方式寫在程式碼裡、存取路徑收斂在 SSO、變更歷史留在 PR，交接是一兩天的帳號操作加上 repo 權限移交。如果環境靠個人記憶維護、存取散落在多組長期 key、變更歷史只在當事人的 shell history 裡，交接是數週的考古加上「不確定有沒有漏掉什麼」的持續焦慮。這篇文章處理兩件事：人走的時候怎麼安全撤銷存取，以及怎麼設計 infra 讓未來的交接成本結構性降低。

## 離職或轉調的存取撤銷清單

存取撤銷的目標是在人員離開的同一天（最晚 24 小時內）關閉所有該身分能存取雲端資源的路徑。撤銷的順序按影響範圍從大到小排：先關能連鎖失效的上游入口，再逐一清理下游殘留。

### 第一步：停用 SSO / IdP 帳號

如果雲端存取統一走 SSO（如 AWS IAM Identity Center、Okta、Google Workspace），停用 IdP 帳號會連鎖撤銷所有透過 SSO 取得的雲端權限 — 這是單一操作影響最大的一步。停用後，該人無法再透過 SSO 登入任何已接 SSO 的 AWS 帳號、CI 平台或內部工具。

這一步能覆蓋多少取決於 SSO 的覆蓋率。如果某些雲端帳號還沒接 SSO（用獨立 IAM user 登入），停用 IdP 帳號不會影響那些路徑，需要額外處理。

### 第二步：處理長期 access key

從 credential report 找出該人名下的所有長期 access key：

```bash
aws iam generate-credential-report
aws iam get-credential-report --output text --query Content | base64 -d \
  | grep "departed-user"
```

每把 key 判斷處理方式：

| key 狀態         | 處理方式                                                |
| ---------------- | ------------------------------------------------------- |
| 只有該人在用     | 直接 deactivate，觀察 24 小時無異常後刪除               |
| 被自動化腳本引用 | 先建新 key 並更新引用處，再 deactivate 舊 key           |
| 用途不明         | 先 deactivate（不刪），監控 CloudTrail 看有沒有存取失敗 |

deactivate 而非直接刪除是因為刪除不可逆 — 如果某個沒記錄在案的自動化正在用這把 key，deactivate 會讓它報權限錯誤，CloudTrail 會記錄失敗的 API 呼叫，方便追蹤；直接刪除後這把 key 的 ID 就消失了，追蹤更困難。

### 第三步：刪除個人 IAM user

確認沒有自動化依賴這個 user 後刪除。刪除前先檢查該 user 是否有 inline policy 或 group membership 被其他流程引用：

```bash
aws iam list-user-policies --user-name departed-user
aws iam list-groups-for-user --user-name departed-user
aws iam list-attached-user-policies --user-name departed-user
```

### 第四步：第三方服務帳號

雲端以外的存取路徑同樣需要撤銷：

- **版本控制**（GitHub / GitLab）：移除組織 membership 或降為 read-only
- **CI 平台**（GitHub Actions secrets、GitLab CI variables）：如果該人曾設定過 CI secret，確認那些 secret 是否需要輪替
- **監控與告警**（Grafana、PagerDuty、Datadog）：移除帳號或降權
- **基礎設施管理平台**（Terraform Cloud、Spacelift）：移除 team membership

### 第五步：MFA 裝置解除註冊

如果該人的 MFA 裝置仍然綁在帳號上（例如 root account 的 MFA），需要管理員介入解除並重新綁定。root account 的 MFA 裝置異動屬於高敏感操作，需要有第二人確認。

### 時程與回報

| 項目          | 時限      | 回報內容                                              |
| ------------- | --------- | ----------------------------------------------------- |
| SSO 停用      | 離職當天  | 確認 IdP 帳號已停用                                   |
| 長期 key 處理 | 24 小時內 | key 數量、各 key 處理方式（deactivate / 替換 / 刪除） |
| IAM user 刪除 | 48 小時內 | 確認無殘留 user                                       |
| 第三方服務    | 48 小時內 | 各平台的處理狀態                                      |
| 管理層回報    | 48 小時內 | 一份清單確認所有存取路徑已關閉                        |

這份回報不是形式 — 它是對管理層證明「離職者已無法存取任何系統」的書面紀錄，合規稽核時會被要求出示。

## 離職時的 credential rotation

存取撤銷處理的是「這個人自己的 key 和帳號」。如果離職者曾有 admin 級別的存取權，還需要處理他可能接觸過的共用 secret。

rotation 的範圍取決於該人的權限等級：

| 權限等級               | rotation 範圍                                 |
| ---------------------- | --------------------------------------------- |
| 只有特定服務的讀取     | 不需額外 rotation                             |
| 特定服務的讀寫         | 該服務的 API key 和連線密碼                   |
| 跨服務或帳號的管理權限 | 所有 Secrets Manager 裡該人可讀的 secret      |
| root 或 admin 等級     | 全面 rotation + CloudTrail 審計最近 30 天活動 |

admin 級別離職時的 CloudTrail 審計：

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=departed-user \
  --start-time $(date -v-30d +%Y-%m-%dT%H:%M:%SZ) \
  --max-items 100 \
  --query 'Events[].[EventTime,EventName,Resources[0].ResourceName]' \
  --output table
```

審計的目的是確認離職前 30 天內有沒有異常操作（大量資料下載、權限變更、新 key 建立），而非預設離職者有惡意。這是標準的安全衛生程序。

如果團隊已經全面採用 OIDC 短期憑證（見[模組二：身分與憑證地基](/infra/02-identity-credentials/)），離職時的 credential rotation 範圍會大幅縮小 — 沒有長期 key 就沒有需要輪替的靜態憑證，SSO 停用後短期 token 自然失效。

## IaC 與 PR 歷史怎麼降低交接成本

存取撤銷是離職當天的緊急操作。交接成本的高低則取決於新接手的人能多快理解環境的結構與歷史。

環境結構寫在 IaC 裡時，新人讀 repo 就能回答「我們有幾個 VPC、subnet 怎麼切、哪些服務在哪個 private subnet」。PR 歷史回答「為什麼 NAT 從共享改成 per-AZ」（因為上個月 ap-northeast-1a 故障時全部出站斷了）。這些資訊不依賴任何個人的記憶，新人第一天就能取得。

程式碼和 PR 歷史能涵蓋的是環境的結構與變更理由。以下資訊不在程式碼裡，需要額外文件或交接：

- **營運脈絡**：哪些服務是流量敏感的、哪個時段不能做變更、哪些客戶有特殊 SLA
- **事故歷史**：過去發生過什麼事故、當時怎麼處理的、有沒有遺留的 workaround
- **vendor 關係**：support contract 的聯絡方式、升級路徑、合約到期時間
- **進行中的工作**：正在做的遷移、已知但未處理的技術債、已規劃但未執行的變更

時程參考：環境完全在 IaC 裡的團隊，infra 角色交接通常 1-2 天能讓新人開始獨立操作（讀 code + 第一次 PR）。沒有 IaC 的環境，交接需要 1-2 週的口頭傳授加上新人自行摸索。

## 最小交接清單

任何 infra 角色變更（不只是離職，包括長假、轉組、新人 onboarding）都應該走過一次這份清單：

### 帳號與存取盤點

- 所有雲端帳號的列表（帳號 ID、用途、環境對應）
- CI/CD 平台的組織與 repo 存取
- 監控與告警平台的帳號
- DNS 管理（域名註冊商、Route 53 hosted zone）
- SSL 憑證管理（ACM、Let's Encrypt）

### 憑證盤點

- 長期 access key 清單（從 credential report 取得）
- Secrets Manager / SSM Parameter Store 裡的 secret 清單
- 第三方服務的 API key（付費服務、SaaS 整合）

### 聯絡與升級路徑

- 雲端 vendor 的 support 聯絡方式與 support plan 等級
- 資安事件的通報對象與流程
- on-call chain 與升級規則

### 進行中的工作

- 正在執行的遷移或重構（目前到哪一步、下一步是什麼）
- 已知的技術債與風險（哪些資源還沒納管、哪些 key 該輪替但還沒輪替）
- 已排程但未開始的變更

這份清單的維護成本很低 — 多數項目在日常工作中已經存在（credential report、repo 結構、ticket board），交接時只需要把散落的資訊收斂到一份文件。如果每次交接都要花時間「找資訊在哪裡」，代表日常的資訊組織有改善空間。

## 讓交接成本結構性降低的設計

上面的清單處理的是每次交接的操作成本。以下設計原則處理的是讓這個成本隨時間趨近固定值、而非隨環境複雜度增長：

**SSO 作為單一存取撤銷點**：所有雲端存取走 SSO，離職時停用一個帳號就關閉所有路徑。沒有 SSO 時，每多一個平台就多一個需要手動撤銷的路徑，漏撤任何一個都是安全缺口。SSO 的覆蓋率越高，撤銷操作越接近 O(1)。

**消除個人長期 key**：用 OIDC + role assumption 取代長期 access key（見[模組二：身分與憑證地基](/infra/02-identity-credentials/)）。沒有長期 key，離職時就沒有需要逐一追蹤和輪替的靜態憑證。credential rotation 的範圍從「所有 key」縮小到「共用 secret」。

**環境描述在程式碼裡**：IaC 讓環境結構對任何有 repo 存取的人可讀。交接的知識成本從「口頭傳授整個環境長什麼樣」降到「讀 code + PR 歷史」。見[模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)。

**PR 描述記錄「為什麼」**：程式碼記錄「什麼」，PR 描述記錄「為什麼」。三個月後翻 git log，看到「把 NAT 從共享改成 per-AZ」知道改了什麼；看到 PR 描述裡的「因為上週 ap-northeast-1a 故障時全部出站斷了」才知道為什麼。這段脈絡在交接時的價值最高 — 新人最常問的問題就是「為什麼這樣設定」。

**on-call 輪替分散操作知識**：讓不同人輪流負責 infra 的 review、apply 和事故處理，用操作經驗分散知識。判斷知識是否過度集中的方式：如果團隊裡只有一個人敢對 production 做 apply，那個人就是交接的瓶頸。見[模組九：怎麼把 infra 推動起來](/infra/09-driving-adoption/)。

這些設計的共同效果是讓交接的固定成本保持在「停用帳號 + 移交 repo 權限 + 走一次交接清單」，不隨環境複雜度或人員流動頻率等比增長。

## 跨分類引用

- → [模組二：身分與憑證地基](/infra/02-identity-credentials/)：IAM 設計、OIDC 短期憑證、權限邊界
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：PR 作為知識載體、變更可追溯
- → [模組九：怎麼把 infra 推動起來](/infra/09-driving-adoption/)：知識共享與 on-call 輪替
- → [backend 模組七：資安與資料保護](/backend/07-security-data-protection/)：Secret 輪替策略
