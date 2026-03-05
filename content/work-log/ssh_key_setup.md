---
title: "SSH Key 設定筆記（macOS / Linux / Windows）"
date: 2026-03-05
draft: false
tags: ["ssh", "macos", "linux", "windows"]
---

## 0. 產生金鑰（如果還沒有的話）

目前推薦使用 **Ed25519** 演算法，相比 RSA 更安全、金鑰更短、驗證速度更快：

```bash
ssh-keygen -t ed25519 -C "your_email@example.com"
```

> 若需相容較舊的系統（不支援 Ed25519），可退而使用 RSA-4096：
>
> ```bash
> ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
> ```

產生時會提示設定 **passphrase（密碼短語）**，強烈建議設定。即使私鑰外洩，攻擊者仍需要密碼才能使用。

---

## 1. 寫入金鑰檔案

### macOS / Linux

```bash
cat > ~/.ssh/<key_name> << 'EOF'
（貼上金鑰內容）
EOF
```

> `'EOF'` 加單引號 → 防止 shell 解析內容中的特殊字元（如 `$`、`` ` ``）

### Windows（PowerShell）

```powershell
New-Item -Path "$env:USERPROFILE\.ssh" -ItemType Directory -Force
Set-Content -Path "$env:USERPROFILE\.ssh\<key_name>" -Value @"
（貼上金鑰內容）
"@
```

> Windows 的 SSH 金鑰預設路徑為 `C:\Users\<使用者>\.ssh\`

---

## 2. 設定權限

### macOS / Linux

```bash
chmod 600 ~/.ssh/<key_name>
```

> `chmod 600` → 僅擁有者可讀寫，SSH 要求私鑰權限不可過於開放，否則會拒絕使用。

### Windows（PowerShell，以系統管理員執行）

```powershell
icacls "$env:USERPROFILE\.ssh\<key_name>" /inheritance:r /grant:r "$($env:USERNAME):(R)"
```

> Windows 需透過 `icacls` 移除繼承權限，並限制為只有當前使用者可讀取。
> 若權限過於開放，OpenSSH 同樣會拒絕載入金鑰。

---

## 3. 加入 SSH Agent

### macOS

```bash
# 啟動 agent（通常 macOS 已自動啟動）
eval "$(ssh-agent -s)"

# 加入金鑰，並存入 Keychain 避免重開機後失效
ssh-add --apple-use-keychain ~/.ssh/<key_name>
```

若要讓金鑰在每次登入時自動載入，可在 `~/.ssh/config` 中加入：

```text
Host *
  AddKeysToAgent yes
  UseKeychain yes
  IdentityFile ~/.ssh/<key_name>
```

### Linux

```bash
# 啟動 agent
eval "$(ssh-agent -s)"

# 加入金鑰
ssh-add ~/.ssh/<key_name>
```

> Linux 重開機後 agent 會重置。可將 `eval "$(ssh-agent -s)"` 加入 `~/.bashrc` 或 `~/.zshrc` 讓它自動啟動。

### Windows（PowerShell，以系統管理員執行）

```powershell
# 啟用 ssh-agent 服務（預設為停用）
Get-Service ssh-agent | Set-Service -StartupType Automatic -PassThru | Start-Service

# 加入金鑰
ssh-add "$env:USERPROFILE\.ssh\<key_name>"
```

> Windows 的 `ssh-agent` 是系統服務，啟用後重開機也會自動執行，不需額外設定。

---

## 4. 測試連線

三個平台指令相同：

```bash
ssh -i ~/.ssh/<key_name> -T git@<host>
```

> Windows 請在 PowerShell 或 Git Bash 中執行，路徑會自動對應到 `$env:USERPROFILE\.ssh\`。

---

## 備註

| 項目 | macOS | Linux | Windows |
|------|-------|-------|---------|
| 金鑰路徑 | `~/.ssh/` | `~/.ssh/` | `C:\Users\<使用者>\.ssh\` |
| 權限設定 | `chmod 600` | `chmod 600` | `icacls` 移除繼承 |
| Agent 持久化 | Keychain | 需加入 shell rc | 系統服務，自動持久 |
| 預裝 SSH | 是 | 大多數發行版已預裝 | Windows 10 1809+ 內建 OpenSSH |

---

## 安全性建議

### 優先使用 Ed25519

| 演算法 | 金鑰長度 | 安全性 | 效能 | 相容性 |
|--------|---------|--------|------|--------|
| **Ed25519** | 256 bit | 高 | 最快 | 2014 年後的 OpenSSH 6.5+ |
| RSA-4096 | 4096 bit | 高 | 較慢 | 最廣泛，適合舊系統 |
| ECDSA | 256/384/521 bit | 中高 | 快 | 已被 Ed25519 取代 |
| DSA | 1024 bit | 低 | - | 已棄用，OpenSSH 7.0+ 預設停用 |

### 為私鑰設定 Passphrase

```bash
# 為已存在的金鑰補設或更換 passphrase
ssh-keygen -p -f ~/.ssh/<key_name>
```

即使私鑰檔案被他人取得，沒有 passphrase 就無法使用。搭配 SSH Agent 後只需輸入一次，不影響日常使用體驗。

### 定期輪換金鑰

建議每 1-2 年輪換一次 SSH 金鑰。可在金鑰名稱中加入年份作為提醒，例如 `id_ed25519_2026`。

### 其他注意事項

- **不要將私鑰上傳到雲端同步服務**（如 iCloud、Google Drive、OneDrive），除非經過加密
- **不要在多台機器之間複製同一把私鑰**，應為每台機器各自產生獨立金鑰
- **避免使用已棄用的 DSA 金鑰**，部分新版 OpenSSH 已預設拒絕 DSA
- **`~/.ssh/` 目錄本身權限應為 `700`**，`authorized_keys` 應為 `600`

---

## 常見問題排查

### Permission denied (publickey)

1. 確認私鑰權限：`chmod 600 ~/.ssh/<key_name>`
2. 確認 `~/.ssh/` 目錄權限：`chmod 700 ~/.ssh`
3. 確認上傳的是 **公鑰**（`.pub`）而非私鑰
4. 使用 verbose 模式查看詳細錯誤：`ssh -vvv user@host`

### Agent 中沒有金鑰

```bash
# 確認 agent 是否正在運行
ssh-add -l

# 如果顯示 "Could not open a connection to your authentication agent"
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/<key_name>
```

### 金鑰類型被伺服器拒絕

部分較新的伺服器已停用 DSA 和較短的 RSA 金鑰。檢查方式：

```bash
ssh -vvv user@host 2>&1 | grep "Offering"
```

如果你的金鑰類型不在伺服器接受的清單中，需要重新產生 Ed25519 金鑰。
