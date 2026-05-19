---
title: "Jenkins → GitHub Actions：Pipeline 5 段 lifecycle 的對位 + 翻譯"
date: 2026-05-19
description: "Jenkins → GHA 是 Type A 高 schema 差 migration、主軸是 Groovy DSL → YAML workflow 翻譯；本文按 pipeline 5 段 lifecycle（source → build → test → scan → deploy）逐段對位、5 個 production 踩雷（shared library equivalence / ephemeral workspace / plugin gap / self-hosted runner / matrix build 表達差）"
weight: 12
tags: ["backend", "reliability", "jenkins", "github-actions", "ci", "migration", "type-a"]
---

> 本文是跨 vendor migration playbook、cross-link [Jenkins](https://www.jenkins.io/) 跟 [GitHub Actions](/backend/06-reliability/vendors/github-actions/)。跑 [migration-playbook-methodology 6 維 audit](/posts/migration-playbook-methodology/) 後對映 *Schema = High（Groovy DSL ↔ YAML workflow）→ Type A phased translation*。

## Pipeline 5 段 lifecycle 的對位 + 翻譯

本文按 *pipeline lifecycle 5 段* 組織內容（variant E）— 不是「為什麼遷」driver 開頭，是 *Jenkins vs GHA 對 5 段各自的處理*：

| Lifecycle 段          | Jenkins 機制                          | GHA 機制                                      |
| --------------------- | ------------------------------------- | --------------------------------------------- |
| 1. Source / SCM       | SCM polling / webhook trigger         | `on: [push, pull_request]` event              |
| 2. Build / Package    | `stage('Build') { sh 'mvn package' }` | `jobs.build.steps[].run: mvn package`         |
| 3. Test / 並行 matrix | `parallel { ... }` + agents           | `jobs.test.strategy.matrix: ...`              |
| 4. Security scan      | Plugin（Snyk / SonarQube / Aqua）     | Action（snyk/actions / sonarsource-actions）  |
| 5. Deploy / promote   | Deploy plugin + approval gate         | `environment: production` + reviewer approval |

跑 [6 維 diff dimension audit](/posts/migration-playbook-methodology/)：

| 維度               | 評估                                                 | 等級     |
| ------------------ | ---------------------------------------------------- | -------- |
| Schema / API       | Groovy DSL ↔ YAML、syntax 完全不同                   | **High** |
| Operational model  | Self-hosted Jenkins → GHA SaaS / self-hosted runners | Medium   |
| Paradigm           | Imperative pipeline → declarative workflow + events  | Medium   |
| Components         | Jenkins + plugins → GHA + actions marketplace        | Low      |
| Application change | Build script 多數不改、CI integration 端要改         | Low      |
| Data topology      | 同單一 build state                                   | Low      |

Schema = High（其他 Medium-Low）→ **Type A phased translation** 為主、加 paradigm + operational 獨立段。

## 為什麼遷：cost / vendor / cloud-native 三條 driver

- **Cost**：Jenkins self-hosted 是「免費 software + 高 ops cost」、GHA 按 minute 計費對中小團隊更便宜
- **Vendor consolidation**：repository 已在 GitHub、整合進 GHA 省一個外部系統
- **Cloud-native**：GHA matrix build + reusable workflow 對 cloud-native deploy（K8s / serverless）有 first-class action

## Phase 0：Audit + classify

```bash
# Jenkins workspace 盤點
find . -name "Jenkinsfile" -o -name "*.groovy"
# 列所有 pipeline file

# 統計 plugin 使用
# Jenkinsfile 內 import / @Library / sh "tool plugin..."
grep -rE "@Library|import|tools\s*\{" Jenkinsfile*

# 每 pipeline 評估 complexity
# - Simple linear pipeline: 1-3 stage、無 shared library
# - Medium: parallel stage + 2-5 shared library
# - Complex: 條件分支 + 動態 stage + 10+ plugin / 5+ shared library
```

Audit output：

- 列「100 個 pipeline、35 simple / 50 medium / 15 complex」
- 每 complexity level 估翻譯時間（simple 0.5 day / medium 2 day / complex 5-10 day）
- Plugin 依賴清單對應 GHA action 替代品

## Phase 1：Schema 對位（Groovy DSL ↔ YAML）

```groovy
// Jenkins Declarative Pipeline
pipeline {
  agent { label 'docker-build' }
  stages {
    stage('Test') {
      parallel {
        stage('Unit') { steps { sh 'mvn test' } }
        stage('Integration') { steps { sh 'mvn verify' } }
      }
    }
  }
  post {
    failure { mail to: 'devops@', subject: 'Build failed' }
  }
}
```

```yaml
# GHA Workflow 對等
name: CI
on: [push]
jobs:
  test:
    runs-on: [self-hosted, docker-build]
    strategy:
      matrix:
        suite: [unit, integration]
    steps:
      - uses: actions/checkout@v4
      - name: Run ${{ matrix.suite }}
        run: |
          case "${{ matrix.suite }}" in
            unit) mvn test ;;
            integration) mvn verify ;;
          esac
  notify-failure:
    needs: test
    if: failure()
    runs-on: ubuntu-latest
    steps:
      - uses: dawidd6/action-send-mail@v3
        with:
          to: devops@
          subject: Build failed
```

對位差異：

- `parallel { ... }` → `strategy.matrix`（粒度不同、matrix 是「同 step 不同參數」、parallel 是「不同 step」）
- `post.failure` → 獨立 job + `if: failure()`
- `@Library` shared library → reusable workflow（`uses: ./.github/workflows/reusable.yml`）
- Jenkins `tools { jdk 'java17' }` → setup-java action（手動配 toolchain）

## Phase 2：Translation pipeline（3-tier hybrid）

對應 [Splunk → Elastic translation](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/) 同 3-tier：

- **Tier 1**：community tool（jenkins-to-actions converter、cover 簡單 pipeline 30-50%）
- **Tier 2**：LLM-assisted（Claude / GPT 翻 medium complexity、人工 verify）
- **Tier 3**：manual（shared library 改 reusable workflow / conditional 動態 stage 重寫）

## Phase 3：Parallel run（雙 CI 跑 4-8 週）

```text
Repository ──┬─→ Jenkins webhook ──→ Jenkinsfile pipeline
             └─→ GitHub Action ────→ .github/workflows/ci.yml

Compare:
- 同 commit 兩端結果一致
- Latency / cost / artifact location 對齊
```

Diff dashboard 列「test pass rate / build time / failure mode」三 metric、跑到 95%+ 一致才進 cutover。

## Phase 4：Cutover + cleanup

- Disable Jenkins webhook
- GHA 成 primary CI
- Jenkins 留 standby 2 週 fallback
- Decommission Jenkins controller + agents

## Production 故障演練

### Case 1：Shared library equivalence、reusable workflow 表達不足

**徵兆**：複雜 Jenkins shared library（含 Groovy class / closure / 動態變數）翻成 reusable workflow 後失準、某些動態邏輯無法表達。

**根因**：Jenkins Groovy 是 imperative + 完整 programming language；GHA reusable workflow 是 declarative YAML、limited expressiveness。

**修法**：

1. **複雜邏輯外包到 script**：reusable workflow 只當 *orchestrator*、複雜邏輯放 `.github/scripts/*.sh` 或 `actions/javascript-action`
2. **自定 composite action**：multi-step logic 包進 composite action、reuse 程度比 reusable workflow 高
3. **退役過度設計的 shared library**：trans 過程暴露 90% library code 其實只用 10%

### Case 2：Ephemeral workspace、build cache 失敗

**徵兆**：cutover 後 build time 從 5 分鐘漲到 20 分鐘；Maven / Gradle / node_modules / Docker layer 每次都重抓。

**根因**：Jenkins agent workspace persistent、build cache 跨 build 保留；GHA ephemeral runner 每次新 VM、cache 預設沒帶。

**修法**：

1. **`actions/cache@v4`**：cache key 用 `hashFiles('**/pom.xml')` 等 lock file、cross-build 復用
2. **Self-hosted runner with cache**：critical pipeline 跑 self-hosted runner、persistent volume
3. **Docker layer cache**：用 `docker/build-push-action` 配 BuildKit cache、不 rebuild full image

### Case 3：Plugin 不對等、CI feature 退化

**徵兆**：Jenkins 用 50+ plugin、GHA action marketplace 找不到對應；team 對 SonarQube quality gate / Jira integration / custom report 等失去 first-class 支援。

**根因**：Jenkins plugin ecosystem 20+ 年累積、GHA marketplace 5 年；某些 niche plugin 在 GHA 沒對等 action。

**修法**：

1. **API-based integration**：用 `curl` 對 vendor API 直接 call、不依賴 plugin / action
2. **自寫 action**：critical feature 自寫 composite / JavaScript action、publish 到 marketplace
3. **退役舊 plugin**：trans 期間 audit plugin 真實使用、80% 可退役

### Case 4：Self-hosted runner setup + scaling

**徵兆**：production workload 需要 GPU / large memory runner；GHA hosted runner spec 不夠、想用 self-hosted runner、發現 scaling / security / monitoring 比 Jenkins agent 複雜。

**根因**：GHA self-hosted runner 是 ephemeral、scaling 需要 *runner controller*（actions-runner-controller on K8s）；跟 Jenkins agent / Kubernetes plugin 對應但 setup 不同。

**修法**：

1. **actions-runner-controller (ARC)**：K8s-native runner scaling、跟 Jenkins K8s plugin 對應
2. **Runner labels**：用 label 路由 job（`runs-on: [self-hosted, gpu, linux]`）
3. **Security**：ephemeral runner 用 short-lived token、不跨 job persist secret

### Case 5：Matrix build vs parallel stage 表達差

**徵兆**：Jenkins 有 *動態 parallel*（runtime 決定要跑哪些 stage、按 input 變動）；GHA matrix 是 *static at workflow load time*、表達不到。

**根因**：GHA matrix 是 declarative、workflow parse 時 expand；runtime 動態決定 stage 需要用 `if:` condition + 多 job。

**修法**：

1. **動態 matrix**：用 `jobs.set-matrix` 先跑一個 job 算 matrix、輸出 JSON、後續 job `strategy.matrix: ${{ needs.set-matrix.outputs.matrix }}`
2. **conditional job**：每個 dynamic stage 寫獨立 job + `if:` 控制觸發
3. **重設計**：90% 動態邏輯其實可改 static matrix + condition、純 runtime 動態通常是 over-engineering

## Capacity / cost

| 維度                      | Self-managed Jenkins      | GitHub Actions                             |
| ------------------------- | ------------------------- | ------------------------------------------ |
| Compute cost              | EC2 + agent licenses      | per-minute billing（free tier + over-cap） |
| Operational FTE           | 0.5-1.5 FTE               | 0.1-0.3 FTE                                |
| Plugin / action ecosystem | 20+ 年成熟                | 5 年快速成長                               |
| Cold start                | Agent ready < 1 min       | Hosted runner 30-60s spin-up               |
| Self-hosted scaling       | Jenkins K8s plugin        | ARC（actions-runner-controller）           |
| Security                  | Self-managed VPC + secret | OIDC + repository secret + environment     |
| Migration cost            | -                         | 1-3 FTE × 1-3 個月                         |

**判讀**：100+ pipeline organization 切 GHA 通常 6-12 月 ROI 持平、之後省 ops cost；< 30 pipeline 早就該切。

## 整合 / 下一步

### 跟 [GitLab CI](https://docs.gitlab.com/ee/ci/) 對位

GitLab CI YAML 語法跟 GHA 接近、shared library 對應 `include:`、self-hosted runner 對等；Jenkins → GitLab CI migration 流程跟本文鏡像對稱、3-tier translation pipeline 通用。

### 跟 [Circle CI](/backend/06-reliability/vendors/circleci/) 對位

CircleCI orb 對等 GHA composite action；跨 SaaS CI 切換比 Jenkins → GHA 簡單（都 YAML-based）。

### 反向 migration（GHA → Jenkins）

少數 enterprise（金融 / 政府）合規要求 self-hosted CI / on-prem；GHA → Jenkins 鏡像對稱、注意 Jenkins shared library 表達力更強、reusable workflow 內 dynamic 邏輯可不必拆。

### 下一步議題

- **Reusable workflow + composite action 混用**：reusable workflow 適合 *跨 repo orchestration*、composite action 適合 *單 repo logic encapsulation*
- **OIDC + cloud deploy**：用 OIDC token 取代 long-lived cloud credential、是 GHA migration 順便升級的機會
- **Cost optimization**：minute-based billing 對 high-volume CI 需要 monitoring + budget alert

## 相關連結

- Target vendor：[GitHub Actions](/backend/06-reliability/vendors/github-actions/)
- 平行 vendor：[CircleCI](/backend/06-reliability/vendors/circleci/)
- 平行 migration playbook（Type A）：[Splunk → Elastic Security](/backend/07-security-data-protection/vendors/splunk/migrate-to-elastic-security/) / [MySQL → PostgreSQL](/backend/01-database/vendors/mysql/migrate-to-postgresql/)
- Methodology：[Migration playbook methodology](/posts/migration-playbook-methodology/)
