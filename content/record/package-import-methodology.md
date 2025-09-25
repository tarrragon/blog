---
title: "Package 導入路徑語意化方法論"
date: 2025-09-21
draft: false
description: "跨語言的導入聲明語意化原則，讓程式碼架構一眼可見"
tags: ["方法論", "程式碼品質", "架構設計", "跨語言開發", "AI協作心得"]
---

## 為什麼導入聲明很重要

在程式開發中，導入聲明往往被視為技術細節，但它們實際上是**架構文件的第一行**。每個 import/require 都在告訴讀者：這個模組的依賴關係、系統的組織方式、以及設計者的架構思考。

<!--more-->

相對路徑如 `import '../../../utils/helper.js'` 只是路徑的機械表達，而語意化路徑如 `import 'package:app/core/utils/helper.dart'` 則清楚傳達了模組的架構位置和責任。

## 導入聲明的本質

### 導入不是什麼

導入聲明不是：

- **文件路徑的機械化表達**：不是為了節省字元數而設計
- **相對位置的簡化表示**：不是為了避免長路徑而妥協
- **開發便利性的工具**：不是為了快速輸入而犧牲可讀性
- **IDE 自動生成的結果**：不是讓工具決定程式碼結構

### 導入是什麼

導入聲明是：

- **依賴關係的明確宣告**：清楚表達模組間的連接
- **程式碼架構的文件化**：展示系統的組織結構
- **依賴來源的即時說明**：讓讀者立即理解依賴的性質
- **架構意圖的表達方式**：體現設計者對模組劃分的思考

## 核心原則

### 第一原則：導入路徑的架構語意性

每個導入都必須清楚表達來源的架構位置：

```dart
// ✅ 正確：清楚表達架構層級
import 'package:book_overview_app/domains/library/entities/book.dart';
import 'package:book_overview_app/core/errors/standard_error.dart';

// ❌ 錯誤：隱藏架構關係
import '../entities/book.dart';
import '../../../core/errors/standard_error.dart';
```

### 第二原則：依賴來源的即時識別

從導入聲明立即理解依賴性質：

```javascript
// 從導入立即理解：這是 Library Domain 的核心實體
import { Book } from '@app/domains/library/entities/book';

// 從導入立即理解：這是 Core 基礎設施
import { StandardError } from '@app/core/errors/standard-error';
```

### 第三原則：禁用別名與妥協

**別名是程式設計不佳的象徵**。當我們遇到重名衝突時，核心解決方案是重構和改善命名，而不是用別名掩蓋設計問題。

#### 為什麼禁用別名

別名反映的根本問題：

1. **命名不夠清晰明確**：導致不同模組產生重名衝突
2. **架構設計缺陷**：同一概念在不同領域使用相同名稱
3. **職責劃分不清**：模組邊界和責任沒有明確定義
4. **技術債務累積**：用別名掩蓋設計問題而非解決問題

#### 錯誤的別名解決方案

```dart
// ❌ 錯誤：使用別名掩蓋設計問題
import 'package:app/domains/library/entities/book.dart' as LibBook;
import 'package:app/domains/search/entities/book.dart' as SearchBook;

// 使用時仍然模糊不清
LibBook.Book bookEntity = LibBook.Book();
SearchBook.Book searchResult = SearchBook.Book();
```

#### 正確的重構解決方案

```dart
// ✅ 正確：重構命名，消除重名衝突
import 'package:app/domains/library/entities/book.dart';
import 'package:app/domains/search/entities/search_result.dart';

// 使用時語意清楚，職責明確
Book libraryBook = Book();
SearchResult searchData = SearchResult();
```

#### 重構策略

**1. 重新審視命名責任**：

- 保留核心領域的概念名稱（如 Library Domain 的 Book）
- 重構其他領域的名稱為更精確的描述（如 Search Domain 的 SearchResult）

**2. 領域邊界清晰化**：

- 根據職責重新命名類別和模組
- 確保每個名稱都有明確的領域歸屬

**3. 架構重構優於別名妥協**：

- 禁用別名迫使開發者正視設計缺陷
- 推動更清晰的領域劃分
- 維護程式碼品質標準

## 跨語言實踐標準

### Dart/Flutter: Package 系統

```dart
// Package 導入 + 完整路徑語意
import 'package:book_overview_app/domains/library/entities/book.dart';
import 'package:book_overview_app/domains/search/services/api_service.dart';
```

**實現機制**：`pubspec.yaml` 定義 package 名稱，Dart 編譯器將 `package:` 映射到 `lib/` 目錄。

### Node.js: 混合策略 (V1 專案實踐)

**生產環境**：

```javascript
// 嚴格的目錄規範 + 明確的相對路徑
const BaseModule = require('./lifecycle/base-module');
const PageDomainCoordinator = require('./domains/page/page-domain-coordinator');
```

**測試環境**：

```javascript
// Jest moduleNameMapper 實現語意化
const { ErrorCodes } = require('src/core/errors/ErrorCodes');
const QualityAssessmentService = require('src/background/domains/data-management/services/quality-assessment-service.js');
```

**Jest 配置關鍵**：

```javascript
// tests/jest.config.js
module.exports = {
  moduleNameMapper: {
    '^src/(.*)$': '<rootDir>/src/$1',           // src/ 路徑語意化
    '^@/(.*)$': '<rootDir>/src/$1',             // @ 別名映射
    '^@tests/(.*)$': '<rootDir>/tests/$1',      // 測試檔案語意化
    '^@mocks/(.*)$': '<rootDir>/tests/mocks/$1' // Mock 檔案語意化
  }
}
```

### PHP Laravel: 框架 + Composer

```php
<?php
// Laravel 的命名空間 + Composer Autoloader
namespace App\Domains\Library\Entities;

use App\Domains\Search\Services\ApiService;
use App\Core\Errors\StandardError;
use Illuminate\Database\Eloquent\Model;

class Book extends Model
{
    // 完整命名空間讓讀者立即理解依賴來源
}
```

### Go: Module System

```go
package main

import (
    // 外部依賴使用 module path
    "github.com/gin-gonic/gin"
    "gorm.io/gorm"

    // 內部模組使用完整 module path
    "book-overview-app/domains/library/entities"
    "book-overview-app/domains/search/services"
    "book-overview-app/core/errors"
)
```

### TypeScript: Module Resolution

```typescript
// Module 導入 + 完整路徑語意
import { Book } from '@app/domains/library/entities/book';
import { ApiService } from '@app/domains/search/services/api-service';
```

## V1 專案：無框架的成功實踐

### 為什麼 V1 可以不需要絕對路徑

1. **一致的目錄結構**：所有模組都在 `/src/background/` 下，層級關係固定
2. **明確的相對路徑語意**：`./` = 同級，`../` = 上一級，路徑語意清楚
3. **避免深層嵌套**：最多 3-4 層目錄，相對路徑仍然可讀
4. **Jest 測試環境的語意化支援**：透過配置實現測試檔案的語意化路徑

### npm test vs Jest 直接執行的選擇

V1 專案選擇 **npm test** 的原因：

1. **一致性管理**：統一的測試入口
2. **環境隔離**：確保所有開發者使用相同配置
3. **工具鏈整合**：可以執行測試前後的額外工作

```json
// package.json - 統一的測試入口
"scripts": {
  "test": "npm run test:core",
  "test:core": "jest tests/unit tests/integration",
  "test:unit": "jest tests/unit",
  "test:integration": "jest tests/integration"
}
```

### 測試路徑語意化的實現機制

```javascript
// Jest 如何解析語意化路徑：
// 1. 測試檔案寫入: require('src/core/errors/ErrorCodes')
// 2. Jest moduleNameMapper 攔截: '^src/(.*)$': '<rootDir>/src/$1'
// 3. 實際解析路徑: /project-root/src/core/errors/ErrorCodes.js
// 4. Node.js 載入模組: 成功匯入 ErrorCodes
```

## 語言特性對比

| 語言 | 實現機制 | 優勢 | 測試環境支援 |
|------|----------|------|-------------|
| **Dart** | Package system | 編譯時解析，IDE 支援佳 | 原生支援 package: 導入 |
| **Go** | Module system | 強制語意化，無相對路徑 | 測試檔案使用相同 module path |
| **PHP Laravel** | 框架 + Composer | 自動載入，標準化目錄 | PHPUnit 自動載入命名空間 |
| **TypeScript** | Module resolution | 彈性配置，工具支援 | Jest/Vitest 支援 path mapping |
| **Node.js (V1)** | 相對路徑 + Jest 映射 | 生產簡單，測試語意化 | **Jest moduleNameMapper 實現語意化** |
| **Python** | Package imports | 簡潔語法，標準化 | pytest 原生支援 package 導入 |

## 實踐選擇指南

### 有框架的專案

- 使用框架提供的模組系統
- 例如：Laravel、Angular、Next.js
- 測試環境通常自動繼承框架的模組解析

### 無框架的專案 (如 V1 範例)

- **生產環境**：採用嚴格的目錄規範 + 相對路徑
- **測試環境**：使用 Jest moduleNameMapper 實現語意化
- **關鍵優勢**：生產簡單，測試語意化

### 混合策略專案

- 生產環境使用簡單的相對路徑
- 測試環境透過工具配置實現語意化
- 適合輕量級 Node.js 專案

## 架構透明性的價值

### 從導入理解系統設計

```dart
// 從這個檔案的導入可以立即理解：
// 1. 這是一個跨 Domain 的協調器
// 2. 主要整合 Library、Import、Search 三個領域
// 3. 使用 Core 的標準錯誤處理
// 4. 依賴外部的 HTTP 套件

import 'package:http/http.dart';
import 'package:book_overview_app/core/errors/standard_error.dart';
import 'package:book_overview_app/domains/library/services/library_service.dart';
import 'package:book_overview_app/domains/import/services/import_service.dart';
import 'package:book_overview_app/domains/search/services/search_service.dart';
```

### 依賴方向的視覺化

```dart
// 讀者可以立即看出依賴方向：
// UI → Domain → Core
// 沒有反向依賴，符合乾淨架構原則

import 'package:book_overview_app/core/interfaces/repository.dart';           // 向下依賴
import 'package:book_overview_app/domains/library/entities/book.dart';       // 平行依賴
import 'package:book_overview_app/domains/library/value_objects/book_id.dart'; // 向下依賴
```

## 總結

Package 導入路徑語意化方法論的核心價值：

1. **架構透明性**：從導入立即理解系統結構
2. **維護便利性**：減少理解和修改的認知負擔
3. **團隊協作**：統一的導入風格提升溝通效率
4. **跨語言一致性**：建立統一的程式碼組織哲學

遵循這個方法論，程式碼將成為自說明的架構文件，每個導入聲明都清楚表達系統的設計意圖和模組關係。無論是有框架還是無框架的專案，都能找到適合的語意化導入策略。

V1 專案證明了即使在無框架環境下，透過嚴格的目錄規範和 Jest 測試配置，仍然可以實現生產環境簡潔、測試環境語意化的理想狀態。這為其他類似專案提供了寶貴的實踐參考。

## 結論

這是架構透明化機制，讓每個導入聲明都成為架構的即時文件。
