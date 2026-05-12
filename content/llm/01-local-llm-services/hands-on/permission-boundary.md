---
title: "Hands-on：Ollama 改檔案 / 寫程式碼的權限邊界在哪"
date: 2026-05-12
description: "四組對照實驗：Ollama 自己沒 FS / shell 權限、wrapper 才有；--dry-run / --confirm / --auto 三檔審查粒度的取捨"
tags: ["llm", "hands-on", "security", "permission", "ollama"]
weight: 6
---

「Ollama 自己改檔案要不要 sudo？」「叫它寫 `rm -rf` 會直接刪嗎？」這類問題的答案來自一個根本事實：**LLM 是 pure function、文字進、文字出、本身沒任何 file system / shell / network 副作用**。改檔案、刪檔案、發網路請求、執行 shell command——全部由 **wrapper 或人類**做。LLM 「以為」自己做了什麼、跟實際發生什麼是兩件事。

本篇用四組對照實驗證明這個事實、再展開 wrapper 三檔審查粒度的設計取捨。這跟 [4.1 副作用範圍設計](/llm/04-applications/tool-use-principles/)、[4.2 Agent 跟人類審查的協作模型](/llm/04-applications/agent-architecture/)、[0.7 隱私資料流原理](/llm/00-foundations/privacy-data-flow/) 三個原則章節對應、實作層的權限與供應鏈判讀對應 [6.2 tool use 與 MCP server 的權限模型](/llm/06-security/tool-use-permission-model/) 跟 [6.0 模型供應鏈與信任邊界](/llm/06-security/model-supply-chain-trust/)。

> **驗證日期**：2026-05-12
> **環境**：Ollama 0.23.2、`gemma3:1b`、Python stdlib
> **檔案位置**：`scripts/permission-demo/edit_with_llm.py`

## 為什麼這個問題重要

直覺常見的誤判：

- 「LLM 寫了 `rm -rf` 我電腦會壞」——錯。LLM 寫指令不代表執行。
- 「Ollama API 改我檔案要 sudo」——錯。Ollama API 根本碰不到檔案。
- 「我跑 wrapper 就讓 LLM 改檔案、應該有 confirm 機制吧」——錯。Confirm 機制完全是 wrapper 開發者自己決定要不要寫、LLM 不知道、不在乎。

理解這個邊界、後續設計 LLM 應用的權限模型才有 ground truth。錯誤的 mental model 會導致兩種 failure：

1. **過度恐懼**：因為怕 LLM「亂改」、把所有 LLM 互動關起來、放棄自動化收益。
2. **過度信任**：相信 LLM「不會做壞事」、給 wrapper 自動執行權限、結果小模型亂解 instruction 把資料毀掉。

實際上權限設計的判讀錨點是：**這個動作有沒有副作用、誰執行**。LLM 永遠不執行、所以權限不在 LLM 層；wrapper 執行、所以權限完全在 wrapper 設計。

## Test 1：直接 API 問改檔案、看會發生什麼

挑一個檔案（token 卡片）、用 curl 送 chat completions、prompt 寫「修改這個檔案」、然後 check 檔案 mtime 跟 md5：

```bash
# 修改前 snapshot
stat -f "%m %N" content/llm/knowledge-cards/token.md
md5 -q content/llm/knowledge-cards/token.md

# 用 system prompt「假裝你有 file 權限」、user 直接指明路徑
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"gemma3:1b",
    "messages":[
      {"role":"system","content":"You can modify files. The user provides a file. You modify it."},
      {"role":"user","content":"Please modify /Users/.../token.md to add a sentence..."}
    ],
    "stream":false
  }'

# 修改後 snapshot
stat -f "%m %N" content/llm/knowledge-cards/token.md
md5 -q content/llm/knowledge-cards/token.md
```

**實測結果**：

```text
=== Before ===
1778508712 content/llm/knowledge-cards/token.md
d9f2d822f7458af62399076a94ef20f6

=== LLM response ===
Okay, here's the modified content of `/Users/.../token.md`...

=== After ===
1778508712 content/llm/knowledge-cards/token.md  ← mtime same
d9f2d822f7458af62399076a94ef20f6                  ← md5 same
```

mtime 沒變、md5 沒變、檔案內容完全沒動。但 LLM 用「Okay, here's the modified content」這種口氣回答——它**以為**自己改了、實際上只生成了一段 markdown 文字。

**結論**：Ollama HTTP API 是 stateless、pure function。輸入 messages、輸出 message content。整個過程沒寫進 socket 以外的任何地方。

為什麼會這樣設計：

- **沙箱本來就在 API 邊界**：HTTP server 接 request、跑 forward pass、回 response。期間沒呼叫 `fs.write()` / `subprocess.run()` / 任何 effectful API。
- **system prompt 不是權限授予**：「You can modify files」這句話對模型來說只是文字 context、不會真的給它 file access。Prompt 是「LLM 內部的 context」、不是「runtime capability」。
- **訓練資料讓 LLM 「以為」自己有能力**：LLM 訓練資料含大量「使用者問問題、AI 改檔案」的範例（如 GitHub Copilot agent traces、tool-use SFT 資料）、模型學會用「我已經改了」這種語氣回答——是 mimic、不是真正的 action。

## Test 2：寫 wrapper 用 --dry-run 模式安全處理

權限不在 LLM、在 wrapper。寫一個 100 行的 wrapper、看怎麼設計 permission gates。完整檔案：`scripts/permission-demo/edit_with_llm.py`。

核心 architecture：

```python
def main():
    # 1. 讀檔（wrapper 用自己的 fs 權限）
    original = args.file.read_text(encoding="utf-8")

    # 2. 送 LLM、拿回提議的新內容
    response = chat([
        {"role": "system", "content": "You modify text files. Output ONLY ..."},
        {"role": "user", "content": f"File: {args.file}\nContent:\n{original}\nInstruction: {args.instruction}"},
    ])
    new_content = extract_code_block(response)

    # 3. Diff（純讀、永遠 safe、不需 gate）
    diff = list(difflib.unified_diff(original.splitlines(...), new_content.splitlines(...)))
    sys.stdout.writelines(diff)

    # 4. PERMISSION GATE：wrapper 決定要不要 apply
    if args.auto:
        args.file.write_text(new_content)
    elif args.confirm:
        if input("Apply? [y/N] ").lower() == "y":
            args.file.write_text(new_content)
    else:  # --dry-run，預設
        pass  # 不寫
```

**為什麼這樣設計**：

- **`extract_code_block`**：嘗試 well-formed `` ```lang\n...\n``` `` regex、失敗 fallback 到 `` ```lang\n...$ `` 寬鬆版。小模型（1B）常忘記結尾 fence、寬鬆才能用。寫嚴格 regex 失敗時直接 abort、是另一種 permission gate（不應用 = 安全）。
- **永遠先印 diff**：diff 是純讀操作、無副作用、永遠 safe。讓使用者先看 LLM 提議了什麼、再決定要不要 apply。
- **`args.auto` 在 `elif` 鏈最前面、`dry-run` 預設**：強迫使用者明示 opt-in 才會寫檔。預設不寫、是「safe default」設計原則。

跑 `--dry-run` 預設、看實際發生：

```bash
python3 scripts/permission-demo/edit_with_llm.py \
  content/llm/knowledge-cards/token.md \
  "把開頭第一段最後加一句『Token 是 embedding 的輸入單位』"
```

實測輸出（1B 模型）：

```text
[+] Asking gemma3:1b to: '把開頭第一段最後加一句「Token 是 embedding 的輸入單位」'
[+] Proposed diff:
--- a/token.md
+++ b/token.md
@@ -6,16 +6,4 @@
 tags: ["llm", "knowledge-cards"]
 ---

-Token 的核心概念是「LLM 內部處理文字的最小單位」...（整段刪除）
-
-## 概念位置
-...（整段刪除）
-...（後面所有段落都刪除）
+Token 是 embedding 的輸入單位。

[+] --dry-run: file unchanged. Use --confirm or --auto to apply.
```

**驚悚發現**：1B 模型完全沒理解「加一句」、把整篇刪掉只剩一行。但 `--dry-run` 不寫檔、檔案安全。

**重點**：

- LLM 行為糟、但 wrapper 設計安全、結果 OK。
- 把同樣 instruction 餵 31B+ 模型結果會合理——模型能力決定 LLM 端品質、wrapper 設計決定**最差情況的後果**。
- 在 wrapper 端永遠假設 LLM 會亂改、設計 safe default、是 defensive programming。

## Test 3：`--confirm` 模式、step-by-step 審查

`--confirm` mode 印 diff、問 y/N、user 確認才寫：

```bash
python3 scripts/permission-demo/edit_with_llm.py \
  content/llm/knowledge-cards/token.md \
  "加一句說明" \
  --confirm
```

互動流程：

```text
[+] Proposed diff:
--- a/token.md
+++ b/token.md
@@ ... 整段刪除 ...

[?] Apply this change to content/llm/.../token.md? [y/N] _
```

使用者看 diff 發現「整篇被刪了」、按 N、檔案安全。

**這個 mode 對應的副作用範圍**：[4.1 工具的副作用範圍設計](/llm/04-applications/tool-use-principles/) 提的 spectrum：

| 等級 | 副作用                              | 適合 mode                |
| ---- | ----------------------------------- | ------------------------ |
| 1    | 純讀（grep、git status）            | `--dry-run` 或無 gate    |
| 2    | 寫 sandbox / staging                | `--dry-run` + 人類事後審 |
| 3    | 寫本地持久化（如 commit、edit 檔）  | `--confirm`              |
| 4    | 寫共享 / production（push、deploy） | `--confirm` 強制         |
| 5    | 操作真實世界（發 email、買股票）    | `--confirm` + 額外 audit |

本 demo 改 markdown 是等級 3（寫本地檔）、`--confirm` 是合適粒度。改 production code 或 git push 是等級 4 / 5、`--confirm` 該強制不該 optional。

## Test 4：`--auto` 模式、危險自動化

`--auto` 不問直接寫：

```bash
cp /tmp/token-orig.md content/llm/knowledge-cards/token.md  # 還原
python3 scripts/permission-demo/edit_with_llm.py \
  content/llm/knowledge-cards/token.md \
  "加一句說明" \
  --auto
```

實測：

```text
[!] --auto mode: writing without confirmation
[+] wrote content/llm/knowledge-cards/token.md
```

檔案內容變成：

```markdown
---
title: "Token"
...
---

Token 是 embedding 的輸入單位。
```

整篇刪光、只剩一句。**沒人 catch 到、commit + push 出去就是 production 災難**。

**`--auto` mode 適合什麼場景**：

- LLM 任務範圍狹窄、可預測（如 format JSON、補 type annotation 給已有 type stub）。
- 配合 git workflow（每次 auto edit 都自動 commit、出問題 git revert）。
- CI / batch processing、人類事後審 PR。

**`--auto` mode 不適合什麼場景**：

- 任務開放性高（「改寫這段讓它更清楚」）。
- 不可逆環境（直接寫 production DB / 發 email）。
- 用弱模型（< 14B）跑、行為不穩。

設計 wrapper 時、把 `--auto` 設成顯式 opt-in、預設保持 dry-run / confirm 等較保守模式。本 demo 的 mutually_exclusive 設計（`-g.add_mutually_exclusive_group()`）保證三種 mode 只能擇一、避免歧義。

## Test 5：LLM 寫 shell command、誰執行？

改檔案是「直接副作用」、寫 shell command 是「間接副作用」——同樣的問題：誰真的執行？

```bash
curl -s http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model":"gemma3:1b",
    "messages":[{"role":"user","content":"Give me a single shell command to find and delete all .log files in my home directory."}],
    "stream":false
  }' | python3 -c "import json,sys; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

LLM 回：

````text
```bash
find ~ -name "*.log" -delete
```
````

這是個有破壞性的指令。檢查 home 下 .log 還在不在：

```bash
find ~ -maxdepth 3 -name "*.log" 2>/dev/null | head -5
# /Users/tarragon/.npm/_logs/2026-05-11T15_33_34_348Z-debug-0.log
# /Users/tarragon/.npm/_logs/2026-05-11T11_58_08_827Z-debug-0.log
# ...
```

都還在。LLM「給了」rm 指令、但沒人執行。

**執行路徑只有兩種**：

1. **人類 paste 到 shell**：人是執行者、權限是 user's shell session permission。Audit trail：terminal history。
2. **Wrapper 程式 `subprocess.run(...)`**：wrapper 是執行者、權限是 wrapper process 的 capability。Audit trail：wrapper 的 log。

LLM 永遠不是執行者。所以「LLM 寫了 rm -rf」這個句子不能成立——它只能「生成了 rm -rf 字串」。

**Agent 場景的 stake**：[4.2 Agent 架構](/llm/04-applications/agent-architecture/) 提到 agent loop = 「LLM 提議 → tool 執行 → 結果回 LLM → 下一輪」。Tool 執行那一步是 wrapper 做的、LLM 只看到結果。Agent 框架是否安全、完全看 tool 怎麼設計：

- **Tool 限制範圍**：read-only file system access、不暴露 shell→ 即使 LLM 想跑 `rm -rf` 也沒對應 tool、無法執行。
- **Tool 暴露 `bash` tool**：給 LLM 一個「執行任意 shell command」的 tool。LLM 提議什麼 wrapper 都跑——這時 wrapper 設計失誤等同把鑰匙直接交給 LLM。
- **Tool 暴露 `bash` tool + per-command confirm**：每個 shell 呼叫前 wrapper 暫停、問人類「該不該執行」。對開發 / 探索環境合理、production 自動化流程會被互動卡住、不適用。

## 對照：Claude Code / Cursor / aider 的權限模型

不同 LLM application 在權限 gate 上的設計選擇：

| Application               | File edit                     | Shell exec                  | 預設審查粒度                |
| ------------------------- | ----------------------------- | --------------------------- | --------------------------- |
| Claude Code（CLI）        | 可、有 PreToolUse hook 可攔截 | 可、有 hook                 | 中（部分自動、部分 prompt） |
| Cursor                    | 可、agent mode                | 可（agent terminal）        | 中、agent 行為可調          |
| aider                     | 可、直接 diff + commit        | 可（`--auto-commits` mode） | 中、預設 commit 前 diff     |
| Continue.dev              | inline edit（user 按 Cmd+;）  | 不直接 exec                 | 高（user 必須 explicit）    |
| Open WebUI（純 chat）     | 不                            | 不                          | N/A（無 wrapper）           |
| 自寫 wrapper（如本 demo） | 看設計                        | 看設計                      | 看設計                      |

**共通 pattern**：所有「自動 edit / exec」的 app 都有某種 confirm 或 hook 機制。沒有 confirm 的 app 等於把寫 production 的鑰匙交給 LLM。

**選 application 時看的維度**：

- 預設 mode 是什麼？（auto / confirm / dry-run）
- 哪些動作會自動執行、哪些會 prompt？
- 有沒有 audit log、能不能 review LLM 改了什麼？
- 萬一 LLM 行為崩、怎麼 rollback？（git revert、snapshot、undo stack）

## 設計自家 wrapper 的權限模型

如果你寫的是「LLM 自動處理 X」這種 wrapper、權限設計的 checklist：

1. **副作用分級**：把可能的動作分到 [4.1 spectrum 等級 1-5](/llm/04-applications/tool-use-principles/)。
2. **預設 dry-run**：不確定就不寫。Apply 必須 opt-in。
3. **永遠印 diff / preview**：用戶才能 catch LLM 亂改。
4. **Confirm 在不可逆操作**：等級 3+ 永遠 prompt、等級 4+ 強制 prompt + 額外 audit。
5. **Audit log**：每個 wrapper 動作寫 log（時間、user、action、result）。出問題能追溯。
6. **Rollback path**：git commit、backup、snapshot 任選一種、必有。
7. **限制 tool 範圍**：給 LLM 暴露最少 tool、不暴露 shell。需要 shell 限制白名單。
8. **小模型加更保守 gate**：1B 模型亂改機率高、保留 `--dry-run` 或 `--confirm` 即可、避免 `--auto`；31B+ 較穩、可給 auto + audit。

## 跑這份 demo 的完整指令

```bash
# 前置：Ollama 跑著、gemma3:1b 已 pull
ollama list | grep gemma3:1b

# 備份要測試的檔案
cp content/llm/knowledge-cards/token.md /tmp/token-orig.md

# Mode 1：dry-run（預設、最安全）
python3 scripts/permission-demo/edit_with_llm.py \
  content/llm/knowledge-cards/token.md \
  "加一句說明"

# Mode 2：confirm（互動審查、適合中等風險）
python3 scripts/permission-demo/edit_with_llm.py \
  content/llm/knowledge-cards/token.md \
  "加一句說明" \
  --confirm

# Mode 3：auto（無確認、危險、僅 batch 用）
python3 scripts/permission-demo/edit_with_llm.py \
  content/llm/knowledge-cards/token.md \
  "加一句說明" \
  --auto

# 還原
cp /tmp/token-orig.md content/llm/knowledge-cards/token.md
```

## 何時這篇會過時

**不會過時的部分**：

- LLM HTTP API 是 pure function、無副作用——這個事實在所有「分離 inference server / wrapper / client」的架構都成立。
- 權限 gate 在 wrapper / application 層——是 software architecture invariant、不是 LLM 特性。
- 副作用範圍 spectrum 跟人類審查粒度的對應。
- `--dry-run` / `--confirm` / `--auto` 三檔的設計取捨。

**會變的部分**：

- 具體 LLM application 的 default mode（Cursor / aider / Claude Code 都會持續調整）。
- 哪個模型「不會亂改」的 ranking（隨模型能力提升而變）。
- MCP / tool spec 細節（會持續演化、但「tool 是 wrapper 暴露」的本質不變）。

讀這篇若指令跑不過、可能是 wrapper script API 微調、但「測試 LLM 是不是 pure function」這個方法本身永遠成立——拿任何 LLM API、送任何 prompt、check 檔案 mtime / md5、就能驗證。

跟其他 hands-on 章節的關係：完整 hands-on 系列見 [Hands-on 章節索引](/llm/01-local-llm-services/hands-on/)、副作用範圍 spectrum 原理見 [4.1 Tool use 原理](/llm/04-applications/tool-use-principles/)、Agent loop 跟人類審查的協作見 [4.2 Agent 架構](/llm/04-applications/agent-architecture/)、Tool use / MCP server 權限模型的個人 dev 視角見 [6.2](/llm/06-security/tool-use-permission-model/)、術語見 [Sandbox](/llm/knowledge-cards/sandbox/)。
