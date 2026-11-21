#!/usr/bin/env python3
"""rule_read_guard：寫入、提交、推送與 ssh 之前，確認這個 agent 讀過對應的規則分冊。

分冊不在 session 啟動時載入，「動手之前先讀」只靠文字要求時，漏讀的 agent 不會留下任何訊號。這支
hook 查 transcript，對應的分冊裡有還沒讀的，就拒絕這次工具呼叫，理由列出要讀的檔案。

對應的分冊：
- Write、Edit、MultiEdit、NotebookEdit：`bin/rule-route` 對目標路徑列出的分冊。
- Bash 指令在命令的位置呼叫 `bin/commit-files`、`bin/push-main`：`commit-push.md`；呼叫 `ssh`：
  `remote.md`。

算「讀過」的條件：
- 這個 agent 自己的 transcript 裡有一次成功的 Read。主 session 與 subagent 各算各的；fork 繼承了
  父層的 context，這支 hook 看不到，所以 fork 也要自己讀一次。
- 讀的是這個 repo 或目標所在 worktree 的 `docs/rules/`，其他位置的副本不算。
- 沒有帶 limit，offset 不大於 1：只讀一段不算讀過整份。Read 對超過字數上限的檔案回傳截斷的內容
  而不報錯，所以分冊的大小由 `bin/tests/test_rule_route.py` 限制。
- 發生在最後一次 context 壓縮之後：壓縮會把讀進來的內容摘要掉。

讀不到 transcript 或路由工具、路由表指到不存在的分冊，或這支 hook 自己出錯時放行，並提醒 agent
自己跑 `bin/rule-route`；輸入不是 JSON 時直接放行。故障放行，才不會變成每一次寫入都被拒絕，連修復
路由表的寫入也被擋下。

涵蓋範圍：經由 Bash 寫檔（sed、heredoc）與 repo 內的生成工具不經過路徑檢查；這類改動在提交時由
`bin/session-edits-check` 印 `[ASK-USER]`。Bash 動作只比對命令位置：前面接環境變數、直譯器或
`timeout`、`env`、`bash -c` 的呼叫與完整路徑的 `/usr/bin/ssh` 不會觸發；引號裡的文字接在 `;`、`|`
之後時可能誤觸發，代價是多讀一份分冊。這支 hook 確認分冊讀過，確認不了內容照分冊寫了。

測試：python3 -m unittest discover -s bin/tests
"""

import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
WRITE_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}
COMPACTIONS = {"compact_boundary", "microcompact_boundary"}
COMMAND_START = r"(?:^|[;&|(\n])\s*"
BASH_ACTIONS = (
    (re.compile(COMMAND_START + r"(?:\S*/)?bin/(?:commit-files|push-main)(?:\s|$)"), "docs/rules/commit-push.md"),
    (re.compile(COMMAND_START + r"ssh(?:\s|$)"), "docs/rules/remote.md"),
)


def emit(**fields):
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", **fields}}, ensure_ascii=False))


def warn(why):
    emit(additionalContext=(
        f"rule_read_guard 無法確認規則分冊有沒有讀過（{why}）。"
        "照 AGENTS.md〈怎麼讀分冊〉讀對應的分冊（改檔時可跑 bin/rule-route <路徑>）。"
    ))


def required_files(path):
    r = subprocess.run(
        [sys.executable, "-I", os.path.join(ROOT, "bin", "rule-route"), "--json", path],
        capture_output=True, text=True, timeout=10,
    )
    if r.returncode != 0:
        raise RuntimeError(r.stderr.strip())
    return json.loads(r.stdout)


def target_root(path):
    """目標所在的 worktree 根目錄；查不到時回傳 ROOT。"""
    d = os.path.realpath(path)
    while not os.path.isdir(d) and d != os.path.dirname(d):
        d = os.path.dirname(d)
    r = subprocess.run(["git", "-C", d, "rev-parse", "--show-toplevel"], capture_output=True, text=True, timeout=10)
    return os.path.realpath(r.stdout.strip()) if r.returncode == 0 else ROOT


def transcript_for(data):
    path = data.get("transcript_path") or ""
    agent = data.get("agent_id")
    if agent:
        if not path.endswith(".jsonl"):
            raise OSError("transcript 路徑的格式對不上")
        own = os.path.join(path[: -len(".jsonl")], "subagents", f"agent-{agent}.jsonl")
        if not os.path.exists(own):
            raise OSError(f"找不到 subagent 的 transcript：{own}")
        return own
    return path


def rule_name(path, roots):
    """path 是 roots 其中一個的 docs/rules/<檔名> 時，回傳 docs/rules/<檔名>。"""
    full = os.path.realpath(path or "")
    for root in roots:
        prefix = os.path.join(root, "docs", "rules") + os.sep
        if full.startswith(prefix) and os.sep not in full[len(prefix):]:
            return "docs/rules/" + full[len(prefix):]
    return None


def files_read(transcript, roots):
    done, pending = set(), {}
    with open(transcript, encoding="utf-8", errors="replace") as f:
        for line in f:
            if "compact_boundary" in line:
                try:
                    if json.loads(line).get("subtype") in COMPACTIONS:
                        done, pending = set(), {}
                        continue
                except ValueError:
                    pass
            wanted = ('"Read"' in line and "docs/rules/" in line) or any(i in line for i in pending)
            if not wanted:
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            content = (entry.get("message") or {}).get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use" and block.get("name") == "Read":
                    args = block.get("input") or {}
                    name = rule_name(args.get("file_path"), roots)
                    if name and args.get("limit") is None and (args.get("offset") or 0) <= 1:
                        pending[block.get("id")] = name
                elif block.get("type") == "tool_result" and block.get("tool_use_id") in pending:
                    name = pending.pop(block["tool_use_id"])
                    if not block.get("is_error"):
                        done.add(name)
    return done


def requirement(data):
    """回傳 (要讀的分冊, 目標的 worktree 根目錄, 讀完之後要做的事)；這次呼叫不需要檢查時回傳 None。"""
    tool, args = data.get("tool_name"), data.get("tool_input") or {}
    if tool in WRITE_TOOLS:
        path = args.get("file_path") or args.get("notebook_path")
        if not path:
            return None
        return required_files(path), target_root(path), "照分冊檢查並改寫這次的內容，再重送這次寫入"
    if tool == "Bash":
        command = args.get("command") or ""
        files = [f for pattern, f in BASH_ACTIONS if pattern.search(command)]
        if files:
            return files, target_root(data.get("cwd") or ROOT), "照分冊確認這次的動作，再重試"
    return None


def main():
    try:
        data = json.load(sys.stdin)
    except ValueError:
        return
    try:
        found = requirement(data)
        if not found or not found[0]:
            return
        required, root, next_step = found
        seen = files_read(transcript_for(data), {ROOT, root})
    except Exception as e:  # 這支 hook 出錯時放行並提醒，不能擋住所有工具呼叫
        warn(str(e))
        return
    readable = [f for f in required if any(os.path.exists(os.path.join(r, f)) for r in (root, ROOT))]
    missing = [f for f in readable if f not in seen]
    if not missing and len(readable) < len(required):
        absent = "、".join(f for f in required if f not in readable)
        warn(f"路由表指到不存在的分冊：{absent}，改 bin/rule-route 的 ROUTES 或補上分冊")
    if missing:
        # 舊分支的 worktree 可能還沒有新分冊，這時列主 repo 那一份（讀它也算數）
        listing = "\n".join(
            f"- {os.path.join(root if os.path.exists(os.path.join(root, f)) else ROOT, f)}" for f in missing
        )
        emit(
            permissionDecision="deny",
            permissionDecisionReason=(
                "這次動作要先讀的規則分冊，這個 agent 還沒讀，或讀過之後 context 被壓縮了：\n"
                f"{listing}\n用 Read 整份讀完（不帶 offset 與 limit），{next_step}。"
            ),
        )


if __name__ == "__main__":
    main()
