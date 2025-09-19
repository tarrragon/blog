---
title: "開始一個新專案的做法"
date: 2025-09-19
draft: false
description: "我已經跟AI描述過我的需求，請AI建立了相關的需求文件，現在要開始建立新專案"
tags: [ "AI協作心得"]
---
## 前情提要

我已經跟AI描述過我的需求，請AI建立了相關的需求文件，現在要開始建立新專案，接下來的步驟是一個實驗，完全依賴AI開展，所以我要記錄我開始的時候給AI的所有指令。

## 流程

1. 請先閱讀 @docs 裡面的需求文件，還有寫作規範
我們需要先在根目錄建立changelog.md，在doc目錄建立todo.md，以及work-logs 資料夾以及建立0.0.1的工作日誌，並且把專案的當前版本設定在0.0.1

```bash
 完成！已建立專案文件管理架構並設定版本為 0.0.1：

  ✅ CHANGELOG.md - 在根目錄，記錄使用者導向的版本更新
  ✅ docs/todo.md - 開發規劃與進度追蹤
  ✅ docs/work-logs/ - 資料夾已建立
  ✅ docs/work-logs/v0.0.1-work-log.md - 詳細記錄開發過程
  ✅ pubspec.yaml - 版本已更新為 0.0.1+1
```

2.接下來，請閱讀需求文件

依照 @docs/event-driven-architecture.md

使用use-case建立大流程的class

用event系統建構文件說明會發明的事件流程

我們的核心功能使用DDD系統建立domain，所以事件流程本身可以先以語意化的命名先假設不存在的函式，然後我們會再寫測試，加入這些還不存在的函式完成TDD第一步必定失敗的測試

```bash
完成！已建立：

  ✅ 事件驅動架構設計文件 (docs/event-driven-architecture-design.md)
  - DDD 領域模型（Book、Library、ImportTask、ScanTask）
  - 完整事件流程（符合 MODULE.ACTION.STATE 格式）
  - 四個核心用例的事件流實作
  - 事件優先級設定

  ✅ 第一個失敗的 TDD 測試 (test/domain/book_test.dart)
  - 6 個測試案例涵蓋核心功能
  - 測試如預期失敗（Red Phase）
  - 所有 domain 層程式碼尚未實作
```

3.我手動安裝了我覺得需要的套件，並請ai參考規格文件補充還需要用的其他套件，然後再手動把ai安裝的套件版本更新到最新

4.我請ai幫我處理了i18n相關的設定跟初始化

5.我要求ai把 main底下的 themedata、初始化的行為、homepage的內容，從main.dart拆分出去，並且新增route設定以及riverpod的設定

## 最終專案的0.0.1 初始化成果

{{< figure src="/record/project_start_up/project0.0.1.png" alt="0.0.1的專案結構" >}}

---

## 我直接貼上ai幫我做的工作日誌內容作為成果參考，這是一個flutter專案，使用riverpod做狀態管理

```yaml
---
**專案版本**: v0.0.1
**開始日期**: 2025-09-19
**開發階段**: 專案初始化與基礎架構建立
---
```

## 專案初始化階段

### 建立專案文件管理架構

#### 問題發現過程

在開始開發 Flutter 書庫管理 APP 前，需要建立完善的文件管理架構，確保開發過程的可追溯性和協作效率。根據需求文件和寫作規範的指引，需要建立三個核心文件系統。

#### 決策邏輯

根據 `docs/document-responsibilities.md` 的文件責任分工原則：

1. **CHANGELOG.md** - 面向使用者，記錄版本更新的功能變化
2. **todo.md** - 面向開發團隊，追蹤開發進度和規劃
3. **工作日誌** - 面向協作者，詳細記錄開發過程和技術決策

#### 實作過程

##### 1. CHANGELOG.md 建立

- **位置**: 根目錄
- **格式**: 採用 Keep a Changelog 標準格式
- **分類**: 使用 feat/fix/change 三大分類
- **內容**: 記錄專案初始化的基本功能建立

##### 2. todo.md 建立

- **位置**: docs 目錄
- **結構**: 包含專案狀態、進行中項目、待完成項目、已完成項目
- **優先級**: 明確標示高/中/低優先級
- **測試追蹤**: 加入測試覆蓋進度章節

##### 3. work-logs 資料夾建立

- **位置**: docs/work-logs/
- **命名規則**: vX.X.X-work-log.md
- **內容要求**: 詳細記錄思考過程、決策邏輯、問題解決流程

### 版本號設定

#### 選擇 0.0.1 的原因

- 專案剛啟動，處於最初期的基礎建設階段
- 遵循語義化版本控制原則
- 為後續的功能開發預留版本號空間

#### 版本號規劃

- **0.0.x**: 基礎架構建立階段
- **0.1.x**: 核心功能開發（資料模型、資料庫）
- **0.2.x**: 匯入功能實作
- **0.3.x**: ISBN 掃描功能
- **0.4.x**: UI 介面開發
- **0.5.x**: 測試與優化
- **1.0.0**: 第一個正式發布版本

---

## 技術架構決策記錄

### Flutter 專案結構規劃

根據需求規格書建議的目錄結構，專案將採用 Feature-based 架構：

```text
lib/
  main.dart                    # 應用程式入口
  app/                         # 應用程式設定
  core/                        # 核心功能模組
    database/                  # SQLite 資料庫
    models/                    # 資料模型
    services/                  # 核心服務
    utils/                     # 工具函式
  features/                    # 功能模組
    library/                   # 書庫管理
    import_export/            # 匯入匯出
    isbn_scanner/             # ISBN 掃描
    book_search/              # 書籍搜尋
```

### 技術棧確認

- **前端框架**: Flutter 3.x
- **狀態管理**: Provider 或 Riverpod（待評估）
- **本地資料庫**: SQLite + sqflite
- **網路請求**: http 套件
- **相機功能**: camera + mlkit_barcode_scanner
- **測試框架**: flutter_test、mockito、integration_test

---

## 下一步計畫

### 立即任務

1. 更新 pubspec.yaml 設定版本號為 0.0.1
2. 開始實作 Phase 1: 核心資料模型與資料庫

### TDD 開發流程準備

根據需求規格書的 TDD 待辦清單，下一步將開始：

1. `should_create_book_with_simplified_source_model`
2. `should_create_platform_lookup_table`
3. `should_link_book_to_platform_correctly`

### 開發原則確認

- 嚴格遵循 TDD 循環：Red → Green → Refactor
- 每次只實作最小可失敗測試
- 結構性變更與行為性變更分開提交
- 保持小而頻繁的 Commit

---

## 協作交接資訊

### 環境設定提醒

- Flutter SDK 需要 3.x 或以上版本
- 需要設定 iOS 和 Android 開發環境
- 建議使用 VS Code 或 Android Studio 開發

### 檔案位置速查

- 需求文件: `docs/app-requirements-spec.md`
- 錯誤處理設計: `docs/app-error-handling-design.md`
- 使用案例: `docs/app-use-cases.md`
- 文件責任說明: `docs/document-responsibilities.md`

### Git 工作流程

- 主分支: main
- 每個功能使用獨立分支開發
- 遵循 Conventional Commits 格式

---

## 技術債務追蹤

- 無（專案剛啟動）

---

## 已知問題

- 無（專案剛啟動）

---

## 學習與改進

- 建立清晰的文件管理架構有助於後續開發的組織性
- 版本號從 0.0.1 開始給予充分的迭代空間
- Feature-based 架構適合 Flutter 專案的模組化開發

---

## TDD 開發流程記錄

### Red Phase - 第一個失敗測試 (2025-09-19)

#### 建立事件驅動架構設計

完成 `docs/event-driven-architecture-design.md` 文件，包含：

- 核心領域模型設計（Book、Library、ImportTask、ScanTask）
- 完整的事件流程定義（遵循 MODULE.ACTION.STATE 格式）
- 四個核心用例的事件流實作
- 事件優先級設定（URGENT、HIGH、NORMAL、LOW）

#### 撰寫第一個失敗測試

建立 `test/domain/book_test.dart`，包含六個測試案例：

1. `should_create_book_with_simplified_source_model` - 測試書籍基本建立
2. `should_create_platform_lookup_table` - 測試平台查詢表
3. `should_link_book_to_platform_correctly` - 測試書籍與平台連結
4. `should_handle_borrower_information_for_borrowed_books` - 測試借閱書籍資訊
5. `should_validate_book_creation_with_required_fields` - 測試必填欄位驗證
6. `should_support_physical_books_without_platform` - 測試實體書籍支援

#### 測試執行結果

如預期，測試完全失敗，錯誤原因：

- 所有 domain 層檔案都不存在
- Book 實體類別尚未實作
- 值物件（BookId、BookTitle、BookCover、BookSource）尚未定義
- 列舉（SourceType、Platform）尚未建立
- PlatformRegistry 服務尚未實作
- 例外類別（InvalidBookIdException、InvalidBookTitleException）尚未定義

這符合 TDD 的 Red Phase，確認測試正確地失敗。

---

## 專案架構實作階段

### Main.dart 重構與模組化

根據用戶要求，將 main.dart 中的三個區塊進行分離：

#### 1. 應用程式初始化分離

- 建立 `lib/app/app.dart` 作為主應用程式類別
- 實作 ProviderScope 包裝和初始化邏輯
- 加入國際化初始設定: `Intl.defaultLocale = 'zh_TW'`
- 建立應用程式狀態管理與錯誤處理

#### 2. 主題資料分離

- 建立 `lib/app/theme.dart` 獨立檔案
- 實作 Material 3 設計系統
- 建立書籍主題相關樣式：
  - BookStyles: 書籍封面、標題、作者樣式
  - Animations: 動畫時間常數
  - Spacing: 間距常數
  - BookSizes: 書籍封面尺寸規範

#### 3. 路由系統建立

- 建立 `lib/app/routes.dart` 路由管理系統
- 實作命名路由與路由生成器
- 加入錯誤路由處理機制
- 建立「開發中」頁面佔位符

#### 4. Riverpod 服務配置

- 建立 `lib/core/providers/app_providers.dart`
- 建立 `lib/core/providers/ui_providers.dart`
- 實作完整的事件驅動狀態管理系統
- 包含 EventBus、優先級事件處理、全域狀態管理

### 套件相依性整合

#### 核心套件選擇

根據書庫管理需求選擇以下套件：

- `mobile_scanner: ^7.0.1` - ISBN 條碼掃描
- `sqflite: ^2.4.2` - SQLite 本地資料庫
- `flutter_riverpod: ^3.0.0` - 現代狀態管理
- `dio: ^5.9.0` - HTTP 網路請求
- `file_picker: ^10.3.3` - 檔案選擇（JSON 匯入）
- `cached_network_image: ^3.4.1` - 圖片快取
- `permission_handler: ^12.0.1` - 權限管理

#### 相依性衝突解決

遇到 flutter_riverpod 3.0.0 與測試工具衝突：

- **問題**: mockito 5.5.1 與 build_runner 2.8.0 因 analyzer 版本不相容
- **解決方案**:
  - 降級 mockito 至 5.5.0 (支援 analyzer ≥6.0.0 <7.0.0)
  - 降級 build_runner 至 2.7.1 (避免版本衝突)
  - 保持 flutter_riverpod 3.0.0 最新版本

### 跨平台權限設定

#### Android 平台配置

更新 `android/app/src/main/AndroidManifest.xml`：

- CAMERA 權限 (ISBN 掃描)
- INTERNET 權限 (Google Books API)
- READ_EXTERNAL_STORAGE 權限 (JSON 匯入)

#### iOS 平台配置

更新 `ios/Runner/Info.plist`：

- NSCameraUsageDescription (相機使用說明)
- UTExportedTypeDeclarations (JSON 檔案類型)
- CFBundleDocumentTypes (文件支援)

#### macOS 平台配置

更新 `macos/Runner/Info.plist`：

- LSApplicationCategoryType (生產力應用程式分類)
- 檔案存取權限設定

#### Windows 平台配置

更新 `windows/runner/main.cpp`：

- 應用程式標題設定為「書庫管理」

### 完整架構系統完成

#### 事件驅動架構

- 實作完整的 EventBus 系統
- 支援事件優先級 (URGENT, HIGH, NORMAL, LOW)
- 整合 Riverpod 狀態管理
- 建立全域錯誤處理機制

#### 國際化支援

- 設定中文為預設語言 (`zh_TW`)
- 整合 flutter_localizations
- 準備多語言擴展架構

#### UI/UX 設計系統

- Material 3 設計規範
- 綠色書籍主題色彩
- 響應式設計支援
- 淺色/深色主題

---

## v0.0.1 最終總結

### 完成的核心功能

✅ **專案基礎架構** - 完整的 Flutter 跨平台專案
✅ **事件驅動架構** - 支援 MODULE.ACTION.STATE 模式
✅ **狀態管理系統** - Riverpod 3.0.0 完整整合
✅ **國際化支援** - 中文/英文多語言準備
✅ **Material 3 設計** - 書籍主題 UI 系統
✅ **跨平台權限** - Android/iOS/Windows/macOS 設定完成
✅ **套件相依性** - 所有核心套件整合無衝突
✅ **文件管理** - CHANGELOG、TODO、工作日誌系統建立

### 技術債務

- 無 (專案初期，架構清晰)

### 下一階段目標

**v0.1.0**: 開始 TDD Domain Layer 開發

- 實作 Book 領域模型
- 建立第一個通過的測試
- Red-Green-Refactor 循環開始

### 專案狀態

- **版本**: v0.0.1 ✅ 基礎架構完成
- **架構版本**: α (Alpha) - 核心架構建立完成
- **開發階段**: 準備進入 TDD 開發
- **整體進度**: 基礎建設完成 (100%)，準備開始功能開發

---

*本工作日誌記錄了 v0.0.1 版本的完整開發過程，為後續 TDD 開發提供完整的技術背景和決策依據。*
