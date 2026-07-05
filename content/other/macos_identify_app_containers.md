---
title: "macOS 辨識 ~/Library/Containers 裡的 App 容器"
date: 2026-07-05
slug: "macos-identify-app-containers"
description: "Containers 目錄佔了幾十 GB 但只看到 UUID 不知道是什麼 App 時的辨識流程。特別是 iOS App on Mac 的容器用 UUID 命名、du 看不出是哪款遊戲。"
tags: ["macos", "disk-space", "apple-silicon", "troubleshooting"]
---

`~/Library/Containers` 是 macOS 沙箱 App 的資料存放位置。每個 App 一個目錄，目錄名通常是 bundle ID（例如 `com.amazon.Lassen`），從名字就能猜出是什麼 App。問題出在 Apple Silicon Mac 上透過 App Store 安裝的 iOS App——它們的容器用 UUID 命名（例如 `D678BD0C-AEB0-4E05-B0D2-58F5C45F0207`），`du` 只看到一個佔了 10G 的 UUID 目錄，完全無從得知是哪個 App。

這次排查時，兩個佔 9.7G 和 8.7G 的 UUID 容器被 content probing（探測目錄內容結構）誤判為 HoYoverse 遊戲。實際用 plist 讀取 bundle ID 後發現是 Epic Seven（第七史詩）和 Arknights（明日方舟），跟 HoYoverse 完全無關。Content probing 的問題是不同遊戲的目錄結構可能相似（都有 data.pack、BattleLog、replay_data），靠結構猜名字容易猜錯。

## 正確的辨識方法：讀 container metadata plist

每個容器目錄根部都有一個 `.com.apple.containermanagerd.metadata.plist`，裡面的 `MCMMetadataIdentifier` 欄位就是 bundle ID，完全不用猜。

```bash
plutil -extract MCMMetadataIdentifier raw \
  ~/Library/Containers/<目錄名>/.com.apple.containermanagerd.metadata.plist
```

這個指令需要 **Full Disk Access** 權限。沒授權的話會收到 `Operation not permitted`。授權路徑：系統設定 > 隱私權與安全性 > 完整磁碟取用權限，把終端機（Terminal.app 或 iTerm）加進去，完全退出再重開。

取得 bundle ID 之後，用 App Store 搜尋或直接 Google 就能確認是哪個 App。

## 批次辨識所有 UUID 容器

```bash
for dir in ~/Library/Containers/*/; do
  name="$(basename "$dir")"
  # 只看 UUID 格式的目錄
  echo "$name" | grep -qE '^[0-9A-F]{8}-' || continue
  kb="$(du -skx "$dir" 2>/dev/null | awk '{print $1}')"
  bid="$(plutil -extract MCMMetadataIdentifier raw \
    "$dir/.com.apple.containermanagerd.metadata.plist" 2>/dev/null)"
  printf '%6sM  %s  %s\n' "$((kb / 1024))" "${bid:-（無法讀取）}" "$name"
done | sort -rn
```

輸出範例：

```text
 9961M  com.stove.epic7.ios      D678BD0C-AEB0-4E05-B0D2-58F5C45F0207
 8903M  tw.txwy.ios.arknights    874686B0-10DF-4399-82A3-BF779C3A3B68
```

## iOS App on Mac 的特徵

Apple Silicon Mac 可以直接跑 iOS/iPadOS App，這些 App 的容器有幾個特徵：

- 目錄名是 UUID 而非 bundle ID
- plist 裡有 `iOSAppOnMac` 欄位
- 不一定出現在 Launchpad 或 `/Applications` 裡
- 移除 App 後容器可能殘留

確認方式：

```bash
plutil -extract iOSAppOnMac raw \
  ~/Library/Containers/<UUID>/.com.apple.containermanagerd.metadata.plist 2>/dev/null
```

回傳 `1` 就是 iOS App on Mac。

## 遊戲容器的清除判斷

遊戲類 App 的容器通常很大（數 GB 到十幾 GB），主要佔用來自下載的遊戲資源（語音、素材、更新包）。這些資源不是使用者資料，是重新下載就能復原的衍生物。帳號進度在遊戲伺服器端，刪除本地容器不影響帳號。

刪除前要確認的事：

1. **用 plist 確認是哪個 App**，不要靠猜測。目錄結構相似的遊戲很多，猜錯會刪到還在玩的遊戲。
2. **確認自己不再玩這個遊戲**。重裝後要重新下載所有資源（可能數 GB）。
3. **iOS on Mac 的 App 如果已從 App Store 移除**（下架或區域限制），刪掉容器後可能無法重新安裝。

```bash
# 確認後刪除（不可逆）
rm -rf ~/Library/Containers/<UUID>
```

## Steam 遊戲的辨識

Steam 的遊戲資料集中在 `~/Library/Application Support/Steam/steamapps/common/`，每個遊戲一個子目錄，目錄名就是遊戲名稱，不需要額外辨識。

```bash
du -shx ~/Library/Application\ Support/Steam/steamapps/common/* 2>/dev/null | sort -rh
```

```text
4.9G    Hollow Knight
450M    SlayTheSpire
262M    To the Moon
```

要回收空間，從 Steam App 內解除安裝不玩的遊戲，而不是手動刪 `common/` 下的目錄。手動刪會讓 Steam 的 manifest（`appmanifest_*.acf`）跟實際檔案不一致。

## Content probing 為什麼不可靠

這次踩到的教訓：兩個 UUID 容器裡都有 `data.pack`、`BattleLog`、`gfsdk` 等目錄，看起來像 HoYoverse 遊戲的結構。但實際上 `BattleLog` 只存在於其中一個（明日方舟），另一個（第七史詩）根本沒有這些目錄，卻有 `data.pack` + `amplitude` analytics，被另一條 heuristic 抓到後套上了錯誤的標籤。

Content probing 的根本問題：

- 同樣的目錄名（`data.pack`）在不同遊戲裡代表不同東西
- 遊戲引擎共用（Unity、Unreal）會產生相似的目錄結構
- 一個 heuristic 命中不代表辨識正確，只代表結構相似

正確做法永遠是讀 plist 的 bundle ID。Content probing 只能作為 plist 讀不到時的 fallback，而且要明確標示「無法確認，僅供參考」，不能直接輸出一個看起來確定的名字。
