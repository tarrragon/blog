# 讀程式自己的 log 定位根因

症狀是「某程式行為不對」而終端機輸出不足以定位時，去讀它自己的 log。原則見 [讀程式自己的 log](principles/read-the-programs-own-log.md)，這裡是操作面。

## 找 log 在哪

- 程式自己的 log 檔：`~/.local/state/<程式>/`、`~/.cache/<程式>/`、`~/.config/<程式>/`、`/var/log/`。
- systemd 服務：`journalctl -u <unit>`（`-b` 本次開機、`-e` 跳到尾、`-f` 跟隨、`--since "10 min ago"`、`-p err` 只看 error 級）。
- 使用者 unit：`journalctl --user -u <unit>`。
- 核心 / 開機：`dmesg`、`journalctl -k`、`journalctl -b -1`（上次開機）。
- 程式啟動訊息常印 log 路徑（找 "log" / "writing to")。
- 不確定去處：`lsof -p <pid> | grep -iE 'log|state'` 看該行程開了哪些檔。

## 讀二進位 / 非純文字 log

有些程式的 log 是自訂二進位格式，`grep` 會說 "binary file matches"。用 `strings` 先抽出可讀文字：

```bash
strings <log> | grep -iE '<症狀關鍵字>'
strings <log> | tail -40          # 看最後發生什麼
```

## 讀法：往上游找第一個異常

- 用症狀 / 錯誤字串當關鍵字搜：`grep -iE 'error|fail|not found|does not exist|denied|refused'`。
- 找「第一個」異常，不要停在最後一個下游錯 —— 下游錯常是誤導性的表面症狀。
- 錨點：時間戳、行號、`ERROR`/`WARN`、明確的 `File does not exist` 之類。
- 實測：某 shell 換配色沒生效、畫面無異狀，log 一句「讀取 scheme 檔失敗：檔案不存在」直指根因（那個檔在 shell 啟動當下還沒被建出來）。畫面沉默、log 說話。

## 對照兩次跑的差異

事後可回溯的 log（帶時間戳、每次跑各留一份）能比對「上次成功 vs 這次失敗差在哪」。若程式沒留這種 log，除錯自己寫的腳本時就該內建：`exec > >(tee -a "$LOG") 2>&1` 導全部輸出進帶時間戳的檔、`trap 'echo "ERR line $LINENO: [$BASH_COMMAND] exit=$?"' ERR` 印出錯行與指令。把「失敗可診斷」當設計目標，未來從瞎找變定位。

## 快速路由

| 要讀什麼         | 工具                                         |
| ---------------- | -------------------------------------------- |
| systemd 服務 log | `journalctl -u <unit> -e` / `-f` / `-p err`  |
| 核心 / 開機      | `dmesg` / `journalctl -k` / `-b -1`          |
| 程式自訂 log 檔  | 找 `~/.local/state/`、`strings <log>`        |
| 不知道開了哪些檔 | `lsof -p <pid> \| grep -i log`               |
| 定位根因         | `grep` 症狀關鍵字 → 找第一個異常，非最後一個 |
