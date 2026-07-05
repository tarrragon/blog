---
title: "macOS 辨識 ~/Library/Containers 裡的 App 容器"
date: 2026-07-05
slug: "macos-identify-app-containers"
description: "Containers 目錄佔了幾十 GB 但只看到 UUID 不知道是什麼 App 時的辨識方法。讀 plist 取 bundle ID 是唯一可靠的做法，content probing 會猜錯。"
tags: ["macos", "disk-space", "apple-silicon", "troubleshooting"]
---

[~/Library/Containers](../macos_app_sandbox_container/) 裡每個 App 一個目錄。原生 Mac App 用 bundle ID 命名（`com.amazon.Lassen`），從名字就能辨識；[iOS App on Mac](../macos_ios_app_on_mac/) 用 UUID 命名（`D678BD0C-AEB0-4E05-B0D2-58F5C45F0207`），`du` 只看到一個佔了 10G 的 UUID，完全不知道是什麼。

## 讀 container metadata plist

每個容器目錄根部都有一個 `.com.apple.containermanagerd.metadata.plist`，裡面的 `MCMMetadataIdentifier` 欄位就是 bundle ID。

```bash
plutil -extract MCMMetadataIdentifier raw \
  ~/Library/Containers/<目錄名>/.com.apple.containermanagerd.metadata.plist
```

這個指令需要 **Full Disk Access** 權限。授權路徑：系統設定 > 隱私權與安全性 > 完整磁碟取用權限，把終端機加進去，完全退出再重開。

取得 bundle ID 之後，用 App Store 搜尋或 Google 就能確認是哪個 App。

## 批次辨識所有 UUID 容器

```bash
for dir in ~/Library/Containers/*/; do
  name="$(basename "$dir")"
  echo "$name" | grep -qE '^[0-9A-F]{8}-' || continue
  kb="$(du -skx "$dir" 2>/dev/null | awk '{print $1}')"
  bid="$(plutil -extract MCMMetadataIdentifier raw \
    "$dir/.com.apple.containermanagerd.metadata.plist" 2>/dev/null)"
  ios="$(plutil -extract iOSAppOnMac raw \
    "$dir/.com.apple.containermanagerd.metadata.plist" 2>/dev/null)"
  platform=""
  [[ "$ios" == "1" ]] && platform=" [iOS on Mac]"
  printf '%6sM  %-40s %s%s\n' "$((kb / 1024))" "${bid:-（無法讀取）}" "$name" "$platform"
done | sort -rn
```

輸出範例：

```text
 9961M  com.stove.epic7.ios                       D678BD0C-... [iOS on Mac]
 8903M  tw.txwy.ios.arknights                     874686B0-... [iOS on Mac]
```

## 清除判斷

辨識出 App 之後，清除判斷依 [Container 的內部結構](../macos_app_sandbox_container/) 而定：

- `Data/Library/Caches/` — 快取，清除零風險
- `Data/Documents/` — 使用者資料或遊戲資源。遊戲資源是可重新下載的衍生物（帳號進度在伺服器端），確認不再玩可整個刪除。電子書庫、筆記資料庫等則需要確認有雲端備份
- [iOS App on Mac](../macos_ios_app_on_mac/) 的 App 如果已從 App Store 下架，刪除容器後可能無法重新安裝

```bash
# 確認後刪除（不可逆）
rm -rf ~/Library/Containers/<UUID>
```

## Steam 遊戲的辨識

Steam 遊戲的儲存機制跟 App Container 不同——資料集中在 `~/Library/Application Support/Steam/steamapps/common/`，每個遊戲一個子目錄，目錄名就是遊戲名稱。

```bash
du -shx ~/Library/Application\ Support/Steam/steamapps/common/* 2>/dev/null | sort -rh
```

回收空間從 Steam App 內解除安裝，手動刪 `common/` 下的目錄會讓 Steam 的 manifest 跟實際檔案不一致。

## Content probing 為什麼不可靠

這次排查的教訓：兩個 UUID 容器被 content probing（探測目錄內容特徵）誤判為 HoYoverse 遊戲。實際讀 plist 後發現是 Epic Seven（第七史詩）和 Arknights（明日方舟），完全不同的廠商。

Content probing 的根本問題是同樣的目錄名（`data.pack`）在不同遊戲裡代表不同東西，遊戲引擎共用（Unity、Unreal）會產生相似的目錄結構。一個 heuristic 命中只代表結構相似，輸出一個看起來確定的名字會導致使用者基於錯誤資訊做決策。

讀 plist 的 bundle ID 是唯一可靠的辨識方法。Content probing 只能作為 plist 讀不到時的 fallback，且必須標示「無法確認，僅供參考」。
