---
title: "9.6 Pre-commit hook 與 CI 整合"
date: 2026-04-24
description: "工具寫完只是起點；接到 pre-commit hook 跟 CI 才真正守住品質。Re-staging、dry-run vs apply、不能繞過的邊界"
weight: 6
---

工具落地的核心責任是**讓檢查在對的時機自動執行**，把紀律從「勤勞的人手動跑」轉移到「每次 commit / push 都跑」的基礎設施。Pre-commit hook 守本機開發、CI 守共享 branch；兩者互補、一起把規則失敗成本壓到秒級可回饋，避免 bug 漏到 production。

工具一旦從 CLI 進入 hook / CI，就有幾個容易踩雷的邊界：**哪些 check 該放 hook**（快、本地可執行）、**哪些該放 CI**（慢、需要乾淨環境）、**hook 改了檔怎麼 re-stage**、**--no-verify 的邊界**怎麼約定、**CI strict mode 跟 local dev 的差異**怎麼處理。本章展開這些問題，並以 `.githooks/pre-commit` + `.github/workflows/md-check.yml` 作為 concrete instance。

## Pre-commit hook 能做什麼、不該做什麼

**能做**：

- 讀 staged 檔案，跑 lint / fmt
- 自動修正格式違規、`git add` re-stage
- 擋下 lint error 的 commit
- 跑跨檔分析（cards）
- 執行 build（確保程式碼能編譯）

**不該做**：

- 執行完整 test suite（太慢，交給 CI）
- 執行 e2e 或需要網路的操作（脆弱，commit 不該依賴外部）
- 修改未 stage 的檔案（會造成 working tree 混亂）
- 執行超過幾秒的任務（心流殺手）

**原則**：pre-commit 是**快速守門員**，不是**完整驗證器**。該做的 checks 要在秒級完成；更慢的驗證交給 CI。

## Makefile 作為 hook 與 CI 的共同介面

有個常被忽略的 pattern：**hook 跟 CI 都透過 Makefile 呼叫工具**，不直接呼叫 binary。這讓三方共用同一套指令。

```makefile
# Makefile
MDTOOLS_SRC := $(shell find scripts/mdtools -type f -name '*.go' 2>/dev/null)
MDTOOLS_MOD := scripts/mdtools/go.mod scripts/mdtools/go.sum
MDTOOLS_BIN := bin/mdtools

.PHONY: build check fix lint cards install-hooks

build: $(MDTOOLS_BIN)

$(MDTOOLS_BIN): $(MDTOOLS_SRC) $(MDTOOLS_MOD)
	@mkdir -p bin
	@cd scripts/mdtools && go build -o ../../$(MDTOOLS_BIN) .

check: build
	@./$(MDTOOLS_BIN) fmt --check content/
	@./$(MDTOOLS_BIN) lint content/
	@./$(MDTOOLS_BIN) cards content/

install-hooks:
	@git config core.hooksPath .githooks
```

這樣：

- 開發者本機：`make check` 手動驗一次
- Pre-commit：hook 呼叫 `./bin/mdtools ...`（或透過 Makefile target）
- CI：workflow 跑 `make check`
- 所有人看到的失敗訊息格式一致

Make 的依賴 timestamp 機制也剛好解決「binary 什麼時候重 build」— `MDTOOLS_BIN` 依賴 `MDTOOLS_SRC`，source 新於 binary 才重 build。

## Pre-commit hook 實作

```bash
#!/usr/bin/env bash
# .githooks/pre-commit
set -euo pipefail

MDTOOLS_BIN="bin/mdtools"
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# 沒 staged .md 快速退出
staged_md=$(git diff --cached --name-only --diff-filter=ACMR | grep -E '\.md$' || true)
if [[ -z "$staged_md" ]]; then
    exit 0
fi

# Rebuild if source newer than binary
if [[ ! -x "$MDTOOLS_BIN" ]] || [[ -n "$(find scripts/mdtools -type f -name '*.go' -newer "$MDTOOLS_BIN" 2>/dev/null || true)" ]]; then
    echo "[pre-commit] rebuilding mdtools..."
    (cd scripts/mdtools && go build -o "$REPO_ROOT/$MDTOOLS_BIN" .) || {
        echo "[pre-commit] mdtools build failed" >&2
        exit 1
    }
fi

# fmt --fix on staged，re-stage 變動的檔案
echo "[pre-commit] mdtools fmt --fix"
while IFS= read -r f; do
    [[ -z "$f" ]] && continue
    before=$(git hash-object "$f")
    "$MDTOOLS_BIN" fmt --fix "$f" >/dev/null
    after=$(git hash-object "$f")
    if [[ "$before" != "$after" ]]; then
        git add "$f"
    fi
done <<< "$staged_md"

# lint on staged (擋錯)
echo "[pre-commit] mdtools lint"
"$MDTOOLS_BIN" lint $staged_md || exit 1

# cards on full content (擋錯)
echo "[pre-commit] mdtools cards"
"$MDTOOLS_BIN" cards content/ || exit 1

exit 0
```

幾個**關鍵 pattern**：

### Fast exit when no markdown staged

沒 md 改動時 hook 在 10ms 內退出。Go 工程師改 `.go` 檔時不會被 markdown hook 擋。這是使用者體驗的生死線。

### `git diff --cached --diff-filter=ACMR`

- `A` (added), `C` (copied), `M` (modified), `R` (renamed) — 該檢查的變動類型
- 排除 `D` (deleted) — 刪除的檔案不用 lint

### `git hash-object` 偵測實際變動

```bash
before=$(git hash-object "$f")
./bin/mdtools fmt --fix "$f"
after=$(git hash-object "$f")
[[ "$before" != "$after" ]] && git add "$f"
```

只在檔案**內容實際改變**時 re-stage。如果 `fmt --fix` 跑完沒改東西（檔案已經 compliant），不觸發多餘 `git add`。

避免用 `stat` 或 mtime — 那些會誤判（file touched 但內容相同）。

### 分層 exit code

- Fast exit (`exit 0`)：沒事要做
- Lint error (`exit 1`)：違規，擋 commit
- Build failure (`exit 1`)：工具壞了，擋 commit（比讓人用壞工具好）

Git 看 non-zero 就會阻止 commit，訊息會印到 terminal，作者能看到原因。

## CI workflow

CI 跑得比 hook 更嚴格：

```yaml
# .github/workflows/md-check.yml
name: md-check

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  md-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-go@v5
        with:
          go-version-file: scripts/mdtools/go.mod
          cache-dependency-path: scripts/mdtools/go.sum
      - name: Build mdtools
        run: |
          mkdir -p bin
          (cd scripts/mdtools && go build -o ../../bin/mdtools .)
      - name: fmt --check
        run: ./bin/mdtools fmt --check content/
      - name: lint
        run: ./bin/mdtools lint content/
      - name: cards
        run: ./bin/mdtools cards content/
```

**設計決策**：

### `go-version-file: scripts/mdtools/go.mod`

不寫死 Go 版本字串。`go.mod` 裡寫 `go 1.25.1`，CI 自動用匹配的版本。本機升 Go 時不用再改 workflow。

### CI 用 `--check`，不是 `--fix`

CI 的角色是**偵測**，不是修復。`--check` 發現問題就 fail，讓作者在本機修完再 push。若 CI 自動 `--fix` 然後 commit，會造成「CI 偷改作者 PR」的混亂。

### 不寫 try-catch 吞錯

CI 步驟失敗就 fail — 不要寫 `continue-on-error: true` 藏錯誤。早期接工具時覺得「讓 CI 通過先」很誘人，但藏錯誤等於工具沒生效。寧可 CI 紅，也要誠實。

## 安裝 hook 的 UX

`.githooks/pre-commit` 放進 repo，但 git 預設看 `.git/hooks/`，不會自動啟用。要跑：

```bash
git config core.hooksPath .githooks
```

包成 Makefile target：

```makefile
install-hooks:
	@git config core.hooksPath .githooks
	@echo "hooks installed"
```

README 或 CONTRIBUTING.md 要寫「新 clone 時執行 `make install-hooks`」。這是一次性動作，但必要。

**考慮過的替代方案**：

- 放 `.git/hooks/pre-commit` — 不能 commit 進 repo，每個 clone 都要重設
- 用 `husky` / `pre-commit` 等工具 — 增加依賴，值得與否看團隊
- 用 direnv `.envrc` 自動設定 — 依賴 direnv，非標準

最乾淨是 Makefile target + 明確的 onboarding 步驟。

## 不能繞過的邊界

Pre-commit hook 可以用 `--no-verify` 跳過。規範要明寫：

> 寫作時遇到 pre-commit 報錯：讀錯誤訊息並修正，**不可用 `--no-verify` 繞過 hook**。

這是**社會規範而非技術強制** — 技術上 git 一定允許 `--no-verify`。但只要規範明列、有人做 code review 抓到違規，就足夠維持紀律。

**有個 nuance**：緊急情況真的需要 `--no-verify` 怎麼辦？例如在服務中斷時要緊急 commit 修復。規範要留這個緊急閥門，但搭配：

- 事後必須補 commit 把違規修掉
- `--no-verify` 的使用要 log 或在 PR 描述標註

大多數 repo 一年可能用不到兩次。關鍵是**預設是不繞過**，而不是「看情況」。

## 常見陷阱

### Hook 執行時間爆炸

常見在 `cards` 這類需要 parse 全 repo 的 check。對 400 檔 < 1 秒可接受；對 10000 檔就要評估。降級手段：

- `cards` 只跑受影響的子圖（根據 staged 檔案 inferrence）
- 複雜 check 搬到 CI
- 本機加 cache（invalidate on file mtime）

### Binary 不 commit 進 repo，但 CI 失敗

`.gitignore` 排除 `bin/`，所以 CI checkout 時沒有 binary。要記得在 CI 加 build step（上面 workflow 的 `Build mdtools` step）。

### fmt --fix 後 commit 有兩個版本

若 hook 的 `fmt --fix` 改了檔但 re-stage 失敗（例如 permission 問題），作者以為 commit 成功但實際 commit 的是舊版本。每次 staged 版本跟 working tree 都要同步 — `git hash-object` 比對能早期發現不一致。

### Hook 不能跨平台

macOS / Linux 的 bash hook 在 Windows（未裝 WSL 或 Git Bash）可能不執行。如果 contributor 有 Windows，把 hook 寫成 Go 程式（例如 `bin/mdtools hook pre-commit`），讓 Go 本身處理跨平台。

## 擴充路徑

- **Hook 只跑 staged 子圖**：根據 staged files 推算需要 parse 的 repo subset，降低 hook 延遲。
- **CI artifact 留 report**：把 lint / cards 的報告 upload 成 GitHub Actions artifact，讓 PR 評論能連結到完整報告。
- **Pre-push hook 做更重檢查**：把 full test suite 放 pre-push（本機 push 前跑），更頻繁的 pre-commit 只做格式與 lint。

## 模組總結

走完九個章節，回到出發點：**Go 除了寫後端服務，還能寫內部工具 / 靜態分析 / CLI / 程式碼生成**。跟後端服務的差異在於生命週期、I/O 模式、錯誤處理慣例，但共用的 Go 技能（型別、interface、package、error）完全可遷移。

本模組介紹的技術 — stdlib flag、goldmark AST、idempotent rewriting、graph analysis、tripwire 決策、pre-commit 整合 — 適用範圍不只 markdown 工具。寫 linter、codegen、migration tool、build tool、dev helper 都是這些技術的組合。

下一步：動手把 `scripts/mdtools` clone 出來，加一條自己的 rule 進去。真正讀懂一個工具的方式是改它一次。
