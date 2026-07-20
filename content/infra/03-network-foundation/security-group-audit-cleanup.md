---
title: "Security Group 稽核與清理"
date: 2026-06-26
description: "盤點所有 security group 規則、找出 0.0.0.0/0 全開與未使用的 SG、依賴檢查後安全刪除、自動化治理"
weight: 2
tags: ["infra", "network", "security-group", "audit"]
---

[Security group](/infra/knowledge-cards/security-group/) 的規則會隨時間累積：某次救火加了一條 0.0.0.0/0、某個已下線的服務留下沒人認領的 SG、某條規則的用途只存在建立者的記憶裡。稽核的目標是把這些累積的規則攤開來，逐條回答「這條規則還有在用嗎、來源該這麼寬嗎」，然後安全地清理不需要的部分。

## 匯出所有 security group 與規則

稽核的第一步是把當前所有 SG 和它們的規則拉出來存成可查詢的 JSON。這份 JSON 是後續所有分析的輸入，也是「稽核那天環境長什麼樣」的快照。

```bash
aws ec2 describe-security-groups \
  --query 'SecurityGroups[].{
    GroupId:GroupId,
    GroupName:GroupName,
    VpcId:VpcId,
    Description:Description,
    IngressRules:IpPermissions,
    EgressRules:IpPermissionsEgress,
    Tags:Tags
  }' \
  --output json > sg-inventory-$(date +%Y%m%d).json
```

這份檔案通常幾百 KB 到幾 MB，存進 repo 的 `inventory/` 目錄，方便日後比對變化。如果帳號有多個 region，每個 region 各跑一次並標明 region。

用 jq 快速看有多少 SG 和總規則數：

```bash
jq 'length' sg-inventory-*.json
jq '[.[].IngressRules | length] | add' sg-inventory-*.json
```

## 找出 0.0.0.0/0 全開的入站規則

0.0.0.0/0 入站代表允許整個網際網路連到這個埠。對外 [ALB](/infra/knowledge-cards/alb/) 的 80/443 開 0.0.0.0/0 是設計意圖，但資料庫埠（5432、3306、6379）、SSH（22）或管理埠開 0.0.0.0/0 是需要收斂的目標。

```bash
jq -r '.[] | select(.IngressRules[]?.IpRanges[]?.CidrIp == "0.0.0.0/0") |
  {GroupId, GroupName, OpenPorts: [.IngressRules[] |
    select(.IpRanges[]?.CidrIp == "0.0.0.0/0") |
    "\(.FromPort // "all")-\(.ToPort // "all")/\(.IpProtocol)"
  ]}' sg-inventory-*.json
```

輸出會列出每個有全開規則的 SG 和對應的 port 範圍。對每一條命中，判斷：

| 場景                      | 全開是否合規                            | 處理方式                                   |
| ------------------------- | --------------------------------------- | ------------------------------------------ |
| ALB 的 80/443             | 合規 — 負載平衡器的職責就是接收公開流量 | 保留，標記為已審查                         |
| SSH (22) 或 RDP (3389)    | 需收斂 — 管理埠暴露在持續的暴力掃描下   | 改用 SSM Session Manager 或限縮到辦公室 IP |
| 資料庫埠 (5432/3306/6379) | 需收斂 — 資料庫不應從公網可達           | 改為只允許應用層 SG 來源                   |
| 全埠 (0-65535 / -1)       | 需收斂 — 等於沒有防火牆                 | 拆成具體需要的埠和來源                     |

IPv6 的 `::/0` 也要一併查：

```bash
jq -r '.[] | select(.IngressRules[]?.Ipv6Ranges[]?.CidrIpv6 == "::/0") |
  .GroupId' sg-inventory-*.json
```

## 找出未使用的 security group

未使用的 SG 是沒有任何網路介面（ENI）掛載的 SG。它不影響任何正在運行的資源，但佔用 SG 配額（每個 VPC 預設上限 2500 個），而且它的規則會讓稽核清單更長、更難判讀。

```bash
aws ec2 describe-network-interfaces \
  --query 'NetworkInterfaces[].Groups[].GroupId' \
  --output text | tr '\t' '\n' | sort -u > sg-in-use.txt

jq -r '.[].GroupId' sg-inventory-*.json | sort -u > sg-all.txt

comm -23 sg-all.txt sg-in-use.txt > sg-unused.txt
cat sg-unused.txt
```

`sg-unused.txt` 裡列出的就是當前沒有任何 ENI 引用的 SG。注意幾個例外：

- **default SG**：每個 VPC 都有一個 default SG，即使未使用也無法刪除，可以跳過
- **被其他 SG 引用**：某個 SG 雖然沒有掛在任何 ENI 上，但被另一個 SG 的入站規則引用為 source — 刪除它會讓引用方的規則失效
- **被 launch template 或 auto-scaling group 引用**：新啟動的實例會套用這個 SG，刪了之後新實例啟動會失敗

## 依賴檢查：刪除前確認沒有間接引用

直接刪一個 SG 之前，確認沒有其他資源引用它。AWS 在 SG 被引用時會擋住刪除（報 DependencyViolation），但提前知道引用方可以避免白跑一趟。

```bash
SG_ID="sg-0abc123"

# 哪些 SG 的入站規則引用了這個 SG 作為來源
jq -r --arg sg "$SG_ID" '.[] |
  select(.IngressRules[]?.UserIdGroupPairs[]?.GroupId == $sg) |
  "\(.GroupId) (\(.GroupName)) 的入站規則引用了 \($sg)"' sg-inventory-*.json

# 哪些 ENI 掛了這個 SG
aws ec2 describe-network-interfaces \
  --filters Name=group-id,Values=$SG_ID \
  --query 'NetworkInterfaces[].{Id:NetworkInterfaceId,Desc:Description,Status:Status}' \
  --output table

# 哪些 RDS instance 使用這個 SG
aws rds describe-db-instances \
  --query "DBInstances[?VpcSecurityGroups[?VpcSecurityGroupId=='$SG_ID']].[DBInstanceIdentifier]" \
  --output text

# 哪些 ELB 使用這個 SG
aws elbv2 describe-load-balancers \
  --query "LoadBalancers[?SecurityGroups[?contains(@,'$SG_ID')]].[LoadBalancerName]" \
  --output text
```

如果所有查詢都回傳空，這個 SG 可以安全刪除。

## 清理流程：標記 → 通知 → 等待 → 刪除

批量清理不是一次 `delete-security-group` 的事。安全的流程有四步：

### 標記候選

對每個要清理的 SG 加一個 tag 標明狀態和預定刪除日期：

```bash
aws ec2 create-tags \
  --resources sg-0abc123 sg-0def456 \
  --tags Key=cleanup-status,Value=pending-deletion \
         Key=cleanup-date,Value=2026-07-10 \
         Key=cleanup-reason,Value="unused-no-eni-no-reference"
```

### 通知

如果 SG 有 `owner` tag，通知該 owner：「這個 SG 預計在 cleanup-date 刪除，如果仍在使用請回報」。如果沒有 owner tag（多數需要清理的 SG 都沒有），在團隊頻道公告清理清單。

### 等待

給 7-14 天的寬限期。期間如果有人回報某個 SG 仍在使用，把 cleanup-status 改成 `retained` 並補上正確的 owner tag。

### 刪除

寬限期過後，對仍是 `pending-deletion` 的 SG 執行刪除：

```bash
for sg in $(aws ec2 describe-security-groups \
  --filters Name=tag:cleanup-status,Values=pending-deletion \
  --query 'SecurityGroups[].GroupId' --output text); do
  echo "Deleting $sg"
  aws ec2 delete-security-group --group-id $sg 2>&1
done
```

DependencyViolation 代表有遺漏的引用，跳過該 SG 並重新調查。

## 自動化持續治理

手動稽核適合第一次清理，持續治理靠自動化：

### AWS Config 規則

`restricted-ssh` 和 `restricted-common-ports` 是 AWS Config 的 managed rule，啟用後會持續監控 SG 規則，新增的 0.0.0.0/0 規則會在幾分鐘內被標記為 non-compliant。

### Prowler 定期掃描

在 CI 排程中定期跑 Prowler，掃描結果存進 repo 作為趨勢追蹤：

```bash
prowler aws --services ec2 --checks ec2_securitygroup_allow_ingress_from_internet_to_any_port \
  -M json-ocsf -o inventory/prowler/
```

### PR 流程攔截

[模組七的 checkov/tfsec 護欄](/infra/07-infra-as-pr/plan-review-apply-guardrails/)在 PR 階段攔截新增的 0.0.0.0/0 規則。這是把治理從「事後稽核」推到「事前攔截」的關鍵一步：稽核能發現已存在的問題，PR 護欄能阻止新問題被引入。

AWS Security Hub 啟用 Foundational Security Best Practices 標準後，會自動聚合 SG 相關的合規 finding 並提供統一 dashboard，適合作為管理層報告的來源。Security Hub 整合了 Config rules 和 Prowler 各自能發現的問題，提供單一窗口追蹤合規趨勢。

## 稽核節奏

第一次稽核最花時間（半天到一天，取決於 SG 數量）。之後的節奏取決於環境變動速度：

| 環境類型                    | 建議節奏         | 理由                                 |
| --------------------------- | ---------------- | ------------------------------------ |
| 有 PR 流程 + checkov 的環境 | 每季             | 新規則已被 PR 攔截，稽核主要看 drift |
| 有 IaC 但沒有 PR 護欄       | 每月             | 手動 apply 可能繞過審查              |
| 全手動環境                  | 每月或每次事故後 | 沒有任何自動攔截機制                 |

稽核產出一份報告：SG 總數、0.0.0.0/0 規則數、未使用 SG 數、上次稽核以來的變化。這份報告可以作為治理進度的量化指標，納入月報。

## 跨分類引用

- → [網路地基 — security group 設計](/infra/03-network-foundation/vpc-subnet-security-group/)：SG 的設計原則（最小開放、group 互相引用）
- → [infra 走 PR 流程](/infra/07-infra-as-pr/plan-review-apply-guardrails/)：checkov/tfsec 在 PR 階段攔截 0.0.0.0/0
- → [治理好習慣 — tagging](/infra/08-governance-habits/tagging-secrets/)：tag 是識別 SG owner 和清理候選的依據
