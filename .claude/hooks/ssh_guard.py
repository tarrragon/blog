#!/usr/bin/env python3
"""
ssh_guard — PreToolUse hook for Bash.

Background: settings.local.json 允許 `Bash(ssh *)`,刻意開放給 agent 對受管遠端機器
做唯讀診斷(hyprctl / systemctl status / journalctl / pgrep …)。但 `ssh *` 的語意
遠大於此:ssh 的 ProxyCommand / LocalCommand 選項會在「本機」執行任意命令,等於繞過
sandbox 對這台開發機的保護。

這支 hook 只攔那個逃逸面:當一條 Bash 指令同時「呼叫 ssh」且「帶本機執行選項」時
deny。遠端診斷(ssh <host> <readonly-cmd>)不受影響。

邊界(誠實聲明):
- 只比對指令字串本身;若 ProxyCommand 寫在 ~/.ssh/config 而非命令列,看不到。
- 防的是誤用 / 意外,不是防主動繞過的對手(可把 flag 藏進變數或 wrapper script)。
"""
import json
import re
import sys

# ssh 會在「本機」執行任意命令的選項。命中任一 + 指令有 ssh 呼叫 → deny。
LOCAL_EXEC_OPTS = re.compile(r"(?:proxy|local)command|permitlocalcommand", re.IGNORECASE)

# ssh 作為命令 token(行首、或在 ; & | ( 之後),避免誤判 sshpass / sshfs / 文章內文字。
SSH_INVOCATION = re.compile(r"(?:^|[\s;&|()])ssh(?:\s|$)")


def main():
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        sys.exit(0)  # 讀不到輸入就放行,不擋正常流程

    if data.get("tool_name") != "Bash":
        sys.exit(0)

    cmd = data.get("tool_input", {}).get("command", "")

    if SSH_INVOCATION.search(cmd) and LOCAL_EXEC_OPTS.search(cmd):
        reason = (
            "ssh 的 ProxyCommand / LocalCommand 會在本機執行任意命令、"
            "被 ssh_guard hook 攔截。ssh 權限只開放給遠端唯讀診斷、"
            "不得用來在這台開發機執行本機命令。"
        )
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }))
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
