---
title: "測試憑證管理"
date: 2026-07-17
description: "測試環境的帳號密碼放在哪裡、CI 怎麼拿到、怎麼防止對生產環境執行 — 存放策略的適用前提與失效偵測"
weight: 7
tags: ["testing", "credential", "ci", "security", "integration-test"]
---

自動化測試碰到真實後端的第一步是認證。測試帳號存放在哪裡、CI 怎麼拿到它、環境判定怎麼防止對生產執行——三個問題的答案在測試套件建立初期就決定，晚做的代價是每次有人加入團隊、每次環境更新、每次 CI 重建都重複遇到同樣的問題。

本章整理靜態憑證的三種存放策略、以及繞開存放問題的動態憑證體系，各自的適用前提與安全取捨。[真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)已觸及「內建帳號」與「本機 gitignore 檔」的設計選擇，本章從那兩段展開，加上 CI secret 注入與動態憑證的完整映射。

## 三種存放策略

以下三種策略處理的都是**靜態憑證**（一組長期有效的帳密或 token）該放在哪裡。另有一類做法繞開「存放」這個問題本身——見後文的動態憑證段，雲端環境的專案應先評估那條路再回來看這三種。

### 策略一：版本庫內建

憑證直接寫在測試程式碼或設定檔裡，隨 repo 一起散佈。

開發者 clone repo 後直接跑測試、CI 不需要額外設定——這是策略一最大的吸引力，也是[真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)「預設可執行」設計的前提。成立的條件是帳號本身不敏感：測試環境對內網或 VPN 後開放、帳號是開發用的預填帳號、團隊已知情地接受暴露面、整個 repo 是私有的。

承擔的代價在時間軸上：repo 的所有讀取者（包括 fork、CI log、意外公開）都拿到憑證。repo 公開的那一天、或憑證跟生產共用的那一天，暴露面從「可接受」瞬間升級為事故。衡量的問題不是「現在安不安全」，而是「repo 公開或帳號共用時，有沒有人記得回來改」。

**失效形態**：帳號被測試環境管理員重設、密碼過期、或測試環境輪替——測試靜默失敗或降級跳過。內建帳號的更新路徑是改 repo，每次更新都進 git log，這一點是優勢也是限制：更新有紀錄、但更新要走 commit 流程。

### 策略二：本機 gitignore 檔

憑證寫在 repo 內的檔案裡，但該檔案加入 `.gitignore`，每台開發機手動填入一次。

策略一被排除（帳號有存取管制、測試環境面對公網、repo 可能公開）但仍想在本機跑測試時，每台機器各自持有一份 gitignore 的憑證檔。每台機器獨立管理，適合帳號分離（開發者 A 和 B 用不同帳號、CI 用專屬服務帳號），repo 公開後 history 裡不會被挖出來。

代價是入門門檻與洩漏面。`.gitignore` 只防 git add、不防其他路徑的洩漏（備份、同步工具、IDE 外掛的上傳功能）。另一個暴露面是「忘記加 `.gitignore`」——repo 初期沒有憑證檔、某天有人建了檔案，`.gitignore` 的那一行會不會跟著出現？樣板（`.credentials.example`）放在 repo 裡、`.gitignore` 裡寫好對應行，把這個依賴從記憶移到結構。

**入門門檻的處理**：新開發者 clone 後第一次跑測試，「找不到憑證檔」的行為應是明確失敗（紅燈加訊息），而非靜默跳過。跳過會讓新成員以為測試本來就只跑一部分，紅燈逼人補完——這是一次性的環境設定債，補完就消。[真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)在「預設可執行」段描述了這條區分的設計理由。

### 策略三：CI secret 注入

憑證存在 CI 平台的 secret store（GitHub Actions secret、GitLab CI variable、Jenkins credential binding），執行時以環境變數或臨時檔注入。

幾乎所有需要在 CI 跑真實後端驗證的團隊最終都會走到這一步：憑證不適合進 repo（策略一被排除）、CI runner 也沒有預置檔案（策略二在 CI 不適用）。憑證的生命週期移交給 CI 平台——存取稽核、輪替機制、最小權限範圍都是平台功能；repo 完全乾淨，fork 和公開都不受影響。

**最小可用的 CI 設定**（以 GitHub Actions 為例）：

```yaml
# .github/workflows/integration.yml
env:
  TEST_BASE_URL: ${{ secrets.QA_BASE_URL }}
  TEST_USERNAME: ${{ secrets.QA_USERNAME }}
  TEST_PASSWORD: ${{ secrets.QA_PASSWORD }}

steps:
  - run: flutter test test/integration/ --tags real-backend
```

命名慣例：secret 以 `QA_` 或 `TEST_` 前綴區分用途，測試 harness 端以同名環境變數讀取。GitLab CI 用 Settings > CI/CD > Variables 設定、Jenkins 用 Credential Binding 外掛——機制不同但慣例相通：CI 平台存憑證、注入為環境變數、測試 harness 讀環境變數。找不到環境變數時的行為依策略二的設計：紅燈加訊息（「缺少 QA_USERNAME 環境變數，請在 CI secret 或本機 .credentials 設定」），而非靜默跳過。

**暴露面**：CI secret 對 PR 的可見性是一條常被忽略的分界。GitHub Actions 預設不把 secret 注入 fork PR 的 workflow——這意味著外部貢獻者的 PR 跑不了真實後端驗證。處理方式有兩條路：把驗證測試放在 merge 後的 nightly stage（延遲訊號），或在 workflow 裡對 fork PR 顯式跳過並記錄（立即跳過但留 skip 紀錄）。兩條路各有取捨：延遲到 nightly 的 merge 後驗證，漂移在合併當天不會被看到；立即跳過的 fork PR，開發者可能誤以為測試通過代表全面驗證。

**失效形態**：secret 過期、被刪除、或 CI 平台遷移後忘記搬——測試在 CI 恆紅或恆 skip。恆紅在 CI 裡是有噪音的訊號、會被看到；恆 skip 是靜默訊號、容易被忽略。把 skip 計數的行動閾值設計寫進 CI 設定，是這個策略的持有成本之一。

## 靜態憑證的選擇映射

選策略的判準是兩個問題的交叉：

| 憑證能進版本庫嗎？ | CI 需要跑驗證嗎？ | 策略                                                   |
| ------------------ | ----------------- | ------------------------------------------------------ |
| 能                 | 需要              | 策略一（內建）——CI 自動取得，零設定                    |
| 能                 | 不需要            | 策略一（內建）——本機跑就夠                             |
| 不能               | 需要              | 策略二（本機）＋ 策略三（CI secret）——本機跟 CI 各一套 |
| 不能               | 不需要            | 策略二（本機）——CI 跳過、本機手動驗證                  |

多數專案的演進路徑：初期 repo 私有、測試環境無管制 → 策略一；repo 準備公開或測試環境加上管制 → 遷移到策略二＋三。遷移時需要把內建憑證從 git history 清除（`git filter-repo` 或 BFG），單純刪除檔案不夠——history 裡的憑證仍然可被取出。

## 動態憑證：不存放長期憑證

上述三種策略共用一個前提：存在一組需要被保管的長期憑證。動態憑證體系取消這個前提——執行當下才簽發、用完即失效，因此沒有「放在哪裡」的問題，也沒有輪替流程。

- **OIDC 聯合身分**：CI 平台以工作流程的身分向雲端換取短期 token（GitHub Actions 對 AWS/GCP/Azure 的 keyless 認證是這一類）。雲端側信任的是「哪個 repo 的哪個 workflow」，不是一串密鑰。
- **工作負載身分**：測試跑在雲端運算資源上時，直接掛載 IAM role 或 workload identity，憑證由平台注入且自動輪替。
- **secret 管理服務**：Vault 這類服務在請求當下簽發短期憑證（例如一組 15 分鐘有效的資料庫帳密），存取有稽核紀錄。

適用前提是被存取的目標支援這些機制——雲端服務多半支援，自架的測試後端通常只認帳密，那就回到前三種策略。取捨的軸線因此不是「哪個比較安全」，而是「目標認不認」：認得動態憑證就用它（省掉輪替與洩漏面），不認就在前三種裡按版本庫與 CI 的兩個問題選。

## 環境判定：誤擊防護的前提

三種策略都有一個共同的上游依賴：**程式能判定自己連的是哪個環境**（[測試環境判定](/testing/knowledge-cards/environment-identification/)）。驗證測試會對測試環境建立與刪除真實資料——對生產環境執行等於事故。環境判定是這條防線的前提。

判定的實作選項：

- **URL allowlist**：測試 harness 維護一份可執行的 host 清單，請求目標不在清單上就拒絕。清單隨 repo 版本化，新增測試環境是有紀錄的 commit。
- **環境變數旗標**：測試環境部署時設一個旗標（如 `TEST_ENV=staging`），測試開始前檢查。風險在於旗標可以被手動覆寫——旗標被設成 `production` 的那天、防線失效。
- **Host 比對**：從 URL 中解析 host 並比對已知的生產 host 清單（黑名單而非白名單）。覆蓋面比 allowlist 寬（未知 host 放行），適合測試環境頻繁更換的團隊。

三者的預設行為在判定失敗時都應該是拒絕：「判定不了歸屬的環境」比照「可能是生產環境」處理。偏好的順序：URL allowlist（最窄、最安全）→ host 比對（較寬、較靈活）→ 環境變數旗標（可被覆寫、最後手段）。環境可判定性的完整討論見 [infra 模組四：環境分離與模組化](/infra/04-environment-separation/)，供給側的環境設計契約見 [6.26 共用測試環境的設計契約](/backend/06-reliability/qa-environment-design/)。

## 失效偵測

憑證是有壽命的資產。帳號被停用、密碼過期、token 輪替——測試套件的防線會在不發出噪音的情況下關閉。偵測的設計目標是讓腐化的憑證產生噪音，而不是靜默降級。

**紅燈不跳過**：憑證存在但無法登入（HTTP 401 / 403）→ 明確失敗，不降級為跳過。跳過與失敗的成因分類與處置路徑見 [Skip vs Fail Semantics](/testing/knowledge-cards/skip-vs-fail-semantics/)。

**定期驗證**：即使整合測試每天都在跑，仍然需要一條專門的「帳號健康檢查」——單純登入、拿到 token、立刻登出。這條測試的職責只有一件事：帳號還活著。放在 CI nightly 或 weekly stage，失敗時產生告警而非只記 log。

**輪替流程的設計**：憑證更新時需要改幾個地方？策略一改 repo 一處；策略二改每台開發機（靠訊息通知、無法強制）加 CI secret 一處；策略三只改 CI secret。更新的散布面是持有成本的一部分——策略二的散布面最大、遺漏機率最高。輪替後跑一次完整的驗證套件確認，而不是只確認登入——有些 API 的權限綁定在帳號層級，帳號換了、登入成功但特定 API 回 403。

## 下一步路由

- 憑證存放決策的實際應用 → [真實後端驗證測試](/testing/03-protocol-integration-test/real-backend-verification/)
- 環境判定的基礎設施面 → [環境分離與模組化](/infra/04-environment-separation/)
- 測試環境的供給側契約 → [共用測試環境的設計契約](/backend/06-reliability/qa-environment-design/)
- CI stage 設計與 skip 計數的治理 → [CI 中的服務 fixture 管理](/testing/03-protocol-integration-test/service-fixture-management/)
