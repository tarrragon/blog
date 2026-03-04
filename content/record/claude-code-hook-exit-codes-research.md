---
title: "Claude Code Hook 系統 Exit Code 實驗"
date: 2025-09-26
draft: false
archived: true
archive_reason: "歷史記錄，專案方法論已演進或無對應方法論"
description: "建立 Claude 內建自檢、Hook 系統驗證、修復模式補救的完整防護體系，從根本預防逃避行為"
tags: ["Hook", "AI協作心得", "自檢機制"]
---

## 研究背景

在開發 Book Overview App 的過程中，我設計了一套完整的 Hook 系統防護體系，目的是**防止開發過程中的逃避行為和確保AI的工作品質**。

### 🔸 Hook 防護體系設計起因

AI會有逃避行為，以完成任務指標為優先而捨棄程式品質或者直接修改測試。

我設計了以下幾種防止停止和強制繼續的 Hook 機制：

#### **🔹 check-todos.py - TodoWrite 完成度檢查**

```python
# 防止未完成工作的會話結束
if todos_pending or todos_in_progress:
    output = {"continue": True, "stopReason": "Incomplete todos detected"}
```

- 🔹 **目的**: 防止有未完成 TodoWrite 任務時意外停止
- 🔹 **機制**: 檢查 transcript 中的 TodoWrite 工具狀態
- 🔹 **效果**: 強制繼續工作直到所有對話任務完成

#### **🔹 check-work-log.sh - 工作日誌完成度檢查**

```bash
# 當工作狀態為進行中時，exit 2 阻止停止
exit 2  # 阻止會話結束，要求繼續工作
```

- 🔹 **目的**: 確保當前版本的工作確實完成才允許停止
- 🔹 **機制**: 分析工作日誌的完成指標和技術債務狀況
- 🔹 **效果**: 避免「假性完成」，確保工作品質

#### **🔹 check-next-objectives.sh - 版本系列目標檢查**

```bash
# 當版本系列仍在進行中時，exit 2 阻止停止
exit 2  # 防止版本系列中途放棄
```

- 🔹 **目的**: 防止版本系列開發中途放棄
- 🔹 **機制**: 檢查 todolist.md 中的版本系列完成度
- 🔹 **效果**: 確保版本系列目標達成才允許推進

#### **🔹 check-5w1h-compliance.py - 決策品質檢查**

```python
# 當 5W1H 分析不合規時，阻止 TodoWrite
{"decision": "block", "reason": "5W1H analysis required"}
```

- 🔹 **目的**: 防止逃避性思考和粗糙決策
- 🔹 **機制**: PreToolUse 階段攔截並檢查 5W1H 完整性
- 🔹 **效果**: 強制深度思考，杜絕逃避行為

### 🔸 遇到的邏輯衝突問題

在開發過程中，發現了奇怪的狀況：

**原問題**:

- `check-todos.py` 顯示 "All todos completed successfully."
- 同時系統又顯示 "Stop hook prevented continuation" 訊息
- 我的問題是：已完成所有 todos 為何還阻止停止？這訊息是誰吐出來的？

**根本原因**:

- 不同 Hook 腳本檢查不同的 todo 來源（會話 vs 專案）
- 會話的任務已結束，但是有其他hook觸發了避免停止的機制

### 設計思路

**防護體系的核心理念**：

- **多層防護**：從對話層、工作層、版本層、決策層建立完整防護
- **零逃避容忍**：任何逃避行為都會被自動檢測和阻止
- **品質強制**：不符合品質標準的工作不允許繼續
- **使用者指引**：被阻止時提供明確的修正指引和下一步行動

### Exit Code 官方定義

根據 Claude Code 官方文件，Hook 腳本的 Exit Code 具有特定含義：

#### **Exit 0** - 成功執行

```bash
exit 0
```

- 🔸 **正常成功執行**
- 🔸 **允許 Claude Code 繼續操作**
- 🔸 **不會產生任何阻止行為**
- 🔸 **用途**: 檢查通過、條件滿足、正常完成

#### **Exit 1** - 一般錯誤

```bash
exit 1
```

- 🔸 **非阻塞性錯誤**
- 🔸 **操作仍可繼續**
- 🔸 **表示**: 有問題但不嚴重
- 🔸 **用途**: 輕微問題、建議性警告

#### **Exit 2** - 阻止停止 (關鍵!)

```bash
exit 2
```

- 🔸 **阻止 Claude Code 停止會話**
- 🔸 **顯示 stderr 內容給 Claude**
- 🔸 **強制要求繼續工作**
- 🔸 **用途**: 工作未完成、需要繼續開發
- 🔸 **注意**: 這是「阻止停止」而非「阻止繼續」

#### **Exit 3+** - 嚴重錯誤

```bash
exit 3
```

- 🔸 **嚴重錯誤狀態**
- 🔸 **通常阻止繼續**
- 🔸 **自定義錯誤類型**
- 🔸 **用途**: 需要立即處理的問題

## Exit 2 的真正定義

### 語意澄清

**🔸 錯誤理解**:

- "Stop hook prevented continuation" = 阻止繼續工作

**🔸 正確理解**:

- "Stop hook prevented continuation" = 阻止了「停止會話」這個行為
- 實際效果在我腳本觸發的原因：當前會話還有todo清單未完成，強制繼續工作，不允許停止會話

### 實際應用場景

專案中的 Exit 2 使用案例：

#### **check-work-log.sh**

```bash
# 當工作狀態為 "IN_PROGRESS" 時
if [[ $WORK_STATUS == "IN_PROGRESS" ]]; then
    echo "工作進行中，建議完成後再推進"

    # 輸出詳細說明到 stderr
    cat >&2 <<EOF
🔸 版本推進暫停 - 當前工作尚未完成

🔸 停止原因：
• 工作日誌顯示工作仍在進行中
• 完成度指標不足
• todolist.md 中有待辦任務

🔸 建議的 TodoWrite 任務：
請執行以下工作項目...
EOF

    exit 2  # 阻止停止，要求繼續工作
fi
```

#### **check-next-objectives.sh**

```bash
# 當版本系列狀態為 "IN_PROGRESS" 時
case "$SERIES_STATUS" in
    "IN_PROGRESS")
        echo "版本系列仍在進行中"

        # 提供具體的待辦任務資訊
        cat >&2 <<EOF
🔸 版本推進暫停 - 當前版本系列仍在進行中

🔸 部分待完成任務範例：
• 修復UI測試中的類型問題
• 更新ViewModel層錯誤處理適配

🔸 建議的 TodoWrite 任務：
繼續版本系列開發...
EOF

        exit 2  # 阻止停止，要求繼續版本開發
        ;;
esac
```

## 🔸 Hook 系統邏輯衝突解決方案

### 問題診斷

**衝突場景**:

- `check-todos.py` 檢查 TodoWrite 工具（會話級別）
- 其他 Hook 腳本檢查 `todolist.md`（專案級別）
- 結果：TodoWrite 完成但 todolist.md 仍有待辦事項

### 解決策略

#### **方案一：Hook 腳本提供 TodoWrite 建議**

在返回 `exit 2` 的 Hook 腳本中：

```bash
# 檢查 todolist.md 中的未完成任務
PENDING_TODOS=$(grep -c "\[ \]" "$PROJECT_ROOT/docs/todolist.md" 2>/dev/null || echo "0")

# 在 stderr 中提供 TodoWrite 建議
cat >&2 <<EOF
🔸 建議的 TodoWrite 任務：
請執行以下 TodoWrite 來管理具體工作項目：

TodoWrite([
  {"content": "完成當前版本核心開發工作", "status": "pending", "activeForm": "完成當前版本核心開發工作"},
  {"content": "執行完整測試確保100%通過率", "status": "pending", "activeForm": "執行完整測試確保100%通過率"}
])
EOF
```

#### **方案二：統一狀態檢查邏輯**

確保所有 Hook 腳本檢查相同的狀態來源，或者建立狀態同步機制。

## 實際演練

### Exit Code 選擇原則

- 🔸 **Exit 0**: 一切正常，可以繼續
- 🔸 **Exit 1**: 有小問題，但可以繼續
- 🔸 **Exit 2**: 工作未完成，**禁止停止**，必須繼續
- 🔸 **Exit 3+**: 嚴重問題，需要立即處理

### Hook 腳本設計模式

```bash
#!/bin/bash

# 🔸 檢查狀態
check_work_status() {
    # 實作狀態檢查邏輯
}

# 🔸 根據狀態決定 exit code
case "$WORK_STATUS" in
    "COMPLETED")
        echo "工作已完成，可推進版本"
        exit 0
        ;;
    "MOSTLY_COMPLETED")
        echo "基本完成，建議檢查後推進"
        exit 1
        ;;
    "IN_PROGRESS")
        echo "工作進行中，建議完成後再推進"

        # 🔸 提供詳細的使用者指引
        cat >&2 <<EOF
🔸 停止原因說明
🔸 需要採取的行動
🔸 建議的 TodoWrite 任務
EOF

        exit 2  # 阻止停止
        ;;
    *)
        echo "工作未完成，需要繼續開發"
        exit 3
        ;;
esac
```

### 使用者體驗優化

- **清楚的錯誤訊息**: 使用 stderr 輸出詳細說明
- **具體的行動指引**: 告訴使用者需要做什麼
- **TodoWrite 整合**: 提供可執行的任務建議
- **狀態一致性**: 確保不同檢查機制的邏輯一致

## 🔸 實際測試結果

### 測試案例 : check-work-log.sh

```bash
$ ./.claude/scripts/check-work-log.sh
# 返回 exit 3，stderr 顯示：
🔸 版本推進暫停 - 工作未開始或缺乏完成指標
🔸 停止原因：
• 工作日誌缺乏完成指標 (0 = 0)
• todolist.md 中有 240 個待辦任務

🔸 建議的 TodoWrite 任務：
請執行以下 TodoWrite 開始系統化工作...
```

### 測試案例 🔸: check-next-objectives.sh

```bash
$ ./.claude/scripts/check-next-objectives.sh
# 返回 exit 2，stderr 顯示：
🔸 版本推進暫停 - 當前版本系列仍在進行中
🔸 部分待完成任務範例：
• 修復UI測試中的類型問題
• 更新ViewModel層錯誤處理適配

🔸 建議的 TodoWrite 任務：
請執行以下 TodoWrite 繼續版本系列開發...
```

## 🔸 效果評估

### 問題解決成果

- 🔸 **邏輯一致性**: Hook 系統不再產生矛盾訊息
- 🔸 **使用者體驗**: 清楚知道為什麼被阻止和需要做什麼
- 🔸 **工作流程**: TodoWrite 與 todolist.md 狀態同步

### 關鍵學習

🔸 **Exit 2 的真實含義**: 阻止停止，要求繼續工作
🔸 **stderr 的重要性**: Claude Code 會顯示 stderr 給使用者
🔸 **狀態檢查一致性**: 不同檢查機制需要協調
🔸 **使用者指引**: 提供可執行的具體建議比抽象說明更有效

## 後續改善方向

- **Hook 腳本標準化**: 建立統一的錯誤處理和訊息格式
- **狀態同步機制**: 建立 TodoWrite 與 todolist.md 的雙向同步
- **使用者體驗測試**: 收集真實使用場景的反饋
- **文件完善**: 將這些經驗整理成團隊開發規範

## 🔸 參考資源

- [Claude Code Hooks Guide](https://docs.claude.com/en/docs/claude-code/hooks-guide)
- [Claude Code Hook Events](https://docs.claude.com/en/docs/claude-code/hooks)
- [reddit網友分享 在有todo未完成的情況下用hook偵測會話轉階段，強迫AI繼續工作不要停下來](https://www.reddit.com/r/ClaudeAI/comments/1now8n7/cc_hook_that_made_my_life_easier_today)

---
