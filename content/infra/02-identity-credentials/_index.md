---
title: "模組二：身分與憑證地基 — IAM 與 OIDC"
date: 2026-06-26
description: "IAM role / policy 設計、最小權限，以及用 OIDC 短期憑證取代長期 access key"
weight: 2
tags: ["infra", "iam", "oidc", "security"]
---

權限一旦散落，後面每一層都建在沙上。網路收斂得再好，只要一把權限過大的長期憑證流出，攻擊者就能繞過所有邊界直接動到核心資源；環境分得再乾淨，只要 production 跟 staging 共用同一組身分，一次誤操作就跨環境炸開。身分與憑證是地基層最先該收斂的能力，因為它決定了「誰能動什麼」這個問題有沒有可信的答案。這一章把這個地基設計好，讓後面的網路、環境分離、服務上線都有一個明確的權限模型可以掛靠。

## IAM 的心智模型

IAM（Identity and Access Management）是雲端平台用來回答「某個身分能不能對某個資源做某件事」的授權系統。它把授權拆成三個獨立的零件：identity（身分，發起動作的主體）、policy（政策，描述「允許/拒絕對哪些資源做哪些動作」的規則）、role（角色，一組可以被臨時取得的權限集合）。理解這三者的分工，是後面所有憑證決策的前提。

identity 分兩類，這個區分在後面設計權限邊界時會反覆用到。一類是 user，代表一個長期存在的主體，通常對應到一個真人或一個固定的服務帳號，本身可以持有長期憑證。另一類是 role，代表一組權限的暫時授予 — 沒有自己的長期密碼，而是讓某個被信任的身分「假扮（assume）」成它、換取一段有時效的臨時憑證。policy 則是貼在 user 或 role 上的規則文件，列出 `Action`（能做什麼，如 `s3:GetObject`）、`Resource`（對哪個資源）、`Effect`（允許或拒絕）。

最小權限（least privilege）是貫穿這套系統的設計原則：一個身分只應該拿到完成它本職工作所需的最小權限集合，多一個 action、多一個 resource 都是攻擊面。最小權限是持續收斂的過程，而非一次設定就結束的靜態狀態 — 服務初期常為了快速上線給寬鬆權限，之後要靠 access analyzer 這類工具觀察「實際用到哪些 action」，再把沒用到的權限收掉。判讀訊號很直接：如果一個 CI role 的 policy 裡有 `*:*` 或 `AdministratorAccess`，它就是下一個 incident 的入口。

```hcl
# 最小權限：CI 只能讀寫特定 bucket、不給整個 S3
data "aws_iam_policy_document" "ci_artifacts" {
  statement {
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["arn:aws:s3:::myapp-artifacts/*"]
  }
}
```

## 長期 access key 的風險

長期 access key 是一組沒有到期時間的靜態憑證（access key ID + secret），任何持有它的人或程式都能以對應身分的全部權限呼叫 API，直到有人手動撤銷為止。它最大的問題是「沒有時效」這個性質本身，會在三個方向上累積風險，而且風險隨團隊規模與時間單調上升。

第一是散落。長期 key 為了被程式使用，會被複製進 `.env` 檔、CI 設定、本機 `~/.aws/credentials`、Slack 訊息、甚至誤推進 git 歷史。每多一個副本就多一個外洩點，而你很難盤點清楚一把 key 到底被貼進了多少地方。第二是權限過大。因為輪替麻煩，團隊傾向給一把 key 配足夠寬的權限「一次搞定」，於是一把本來只該讀 artifact 的 key 同時握有刪除 production 資料庫的能力。第三是難以輪替。輪替一把長期 key 意味著找出所有副本、同步替換、確認沒有遺漏，這個成本高到讓多數團隊選擇拖延，於是 key 的有效期變成「無限」，外洩後的曝險窗口也跟著變成無限。

判讀訊號是：如果你無法在五分鐘內回答「這把 key 被用在哪些地方、上次輪替是什麼時候」，它就已經是技術債。早期新創特別容易踩這個坑 — 一個工程師為了讓部署腳本跑起來，在筆電上建了一把 admin key，半年後這把 key 還在 CI 環境變數裡，建立它的人已經離職。這類事故的代價不在於「key 外洩」這個事件本身，而在於外洩之後你沒有任何手段限制爆炸半徑。

## OIDC：給 CI/CD 的短期憑證

OIDC（OpenID Connect）聯合讓 CI/CD 平台用一段每次執行才簽發、幾分鐘後就失效的短期憑證取代長期 key，從根本上消掉「靜態密鑰散落」這個問題。它的運作方式是建立信任關係：雲端帳號信任某個外部 identity provider（如 GitHub Actions、GitLab CI 的 OIDC issuer），當管線執行時，CI 平台簽發一個帶有可驗證 claim 的 token（描述「這是哪個 repo、哪個 branch、哪個 workflow 在跑」），雲端用這個 token 換出一段臨時憑證。沒有任何長期 secret 需要被儲存在 CI 設定裡。

關鍵設計在 role 的 trust policy（信任政策）上 — 它規定「哪個外部身分被允許假扮成這個 role」。trust policy 要用 token 的 claim 把假扮條件收到最緊：限定 issuer、限定 audience、限定特定 repo 與 branch。收得太鬆（例如只驗 issuer、不驗 repo）等於任何掛在同一個 CI 平台的專案都能假扮你的 role，這是常見的設定陷阱。

```hcl
# OIDC trust policy：只允許特定 repo 的 main branch 假扮此 role
data "aws_iam_policy_document" "ci_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [aws_iam_openid_connect_provider.github.arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:my-org/my-app:ref:refs/heads/main"]
    }
  }
}
```

這一章只把 role 與 trust policy 設計好，OIDC 的實際回報要到[模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)建管線時才兌現 — 屆時管線用這裡定義好的 role 取得短期權限執行 `plan` 與 `apply`，CI 環境裡不需要存任何 access key。下一步路由很明確：role 與最小權限的 policy 屬於這裡的地基，管線怎麼觸發、怎麼卡 review 屬於模組七。

## 權限邊界設計

權限邊界是把不同類型的身分與不同環境之間的權限刻意隔開，讓任何一個身分被攻破時，爆炸半徑都被限制在它本職的範圍內。邊界設計有兩條軸線需要分別處理：人 vs 機器，以及環境之間。

人 vs 機器的邊界，源自兩者的存取模式根本不同。人類身分需要互動式登入、應該強制 MFA、權限隨職責變動，且通常透過 SSO 集中管理而非各自持有 key。機器身分（CI、跑在運算資源上的服務）需要的是程式化、無人值守的存取，應該用 role 假扮取得短期憑證，永遠不該配長期 key。機器身分還要再分跑在哪裡：跑在雲上的 workload（運算實例、容器任務）由平台直接把 role 綁在執行環境上 — AWS 用 instance profile 把 role 掛在 EC2 instance、用 ECS task role 把 role 掛在容器任務，workload 從實例 metadata 自動取得輪替的短期憑證，這是早於 OIDC 就存在的標準解；只有跑在雲外的 CI/CD（如 GitHub Actions）拿不到實例 metadata，才需要前面那套 OIDC 信任關係換憑證。把這兩類混在同一個身分上，會讓你既無法對人強制 MFA，也無法對機器收斂權限。一個常見陷阱是工程師用自己的個人 key 跑自動化腳本 — 這把人的廣泛權限直接送進了無人值守的執行環境。

環境之間的邊界，目的是讓 production 的權限與 staging、dev 完全不交叉，避免一次誤操作或一個被攻破的低敏感環境波及到核心資產。實作上常見的做法是每個環境用獨立的帳號（account）或獨立的 role，部署到 production 的身分拿不到 staging 的資源、反之亦然。這條邊界在 AWS 上有兩層具體機制可以落地：帳號級的護欄用 Organizations 把環境拆成獨立帳號，再用 SCP（Service Control Policy）對整個帳號或組織單位設定權限天花板，連帳號內的管理員都越不過去；role 級的護欄用 Permissions Boundary 這個 IAM 字面功能，給單一 role 設一個權限上限，限制它「最多能拿到什麼」，即使有人後來給它貼了過寬的 policy 也會被天花板擋住。前者收的是帳號與組織的整體範圍，後者收的是單一身分的上限，兩者疊起來才讓「權限邊界」從概念變成擋得住誤設的具體工具。判讀訊號是：如果一個 dev 環境的 CI role 能列出或刪除 production 的資源，邊界就沒有真正建立。環境隔離的更完整實作（帳號結構、模組化參數）會在[模組四：環境分離與模組化](/infra/04-environment-separation/)展開，這裡先確保身分層的權限不跨環境。

這一章談的是身分與憑證 — 誰是誰、怎麼證明、能動什麼。憑證背後引用的應用層 secret（資料庫密碼、第三方 API key）怎麼安全儲存與注入，屬於[模組八：治理好習慣](/infra/08-governance-habits/)的 secret management 範圍，不在這裡處理。兩者的交集是：身分層決定「誰能讀到 secret store」，secret 層決定「secret 怎麼存與輪替」。

## 章節文章

| 文章                                                                                                                  | 主題                                                                                                                                 |
| --------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| [身分與憑證地基 — IAM 模型、OIDC 短期憑證與權限邊界設計](/infra/02-identity-credentials/iam-oidc-privilege-boundary/) | IAM 的 identity / policy / role 三元件、最小權限的持續收斂、用 OIDC 取代長期 access key，以及 SCP 與 Permissions Boundary 的環境隔離 |
| [跨帳號策略 — Organizations、SCP 與帳號工廠](/infra/02-identity-credentials/multi-account-strategy/)                  | 用 Organizations 把環境拆成獨立帳號、用 SCP 設定帳號級護欄、用帳號工廠自動化新帳號的建立流程                                         |
| [團隊權限分級與存取管理](/infra/02-identity-credentials/team-access-management/)                                      | 三級權限模型（admin / operator / viewer）、臨時提權、定期 access review、contractor 存取                                             |

## 跨分類引用

- → [模組三：網路地基](/infra/03-network-foundation/)：身分備妥後，劃清服務之間的網路邊界
- → [backend 模組七：資安與資料保護](/backend/07-security-data-protection/)：Secret Management 與這裡的憑證管理交集
- → [模組七：infra 走 PR 流程](/infra/07-infra-as-pr/)：CI/CD 用 OIDC 取得短期權限
- → [接手維運](/infra/takeover/)：接手時的 credential 盤點與輪替
