---
title: "程式碼自然語言化撰寫方法論"
date: 2026-03-04
draft: false
description: "將程式碼視為自然語言的撰寫哲學：從認知負擔的理論出發，透過五行函式、事件驅動、變數專一化，實現如同閱讀文章般流暢的程式碼"
tags: ["方法論", "程式設計", "軟體架構", "事件驅動", "程式品質", "重構","AI協作心得"]
categories: ["軟體工程", "開發方法論"]
keywords: ["自然語言程式設計", "五行函式", "單一職責原則", "事件驅動架構", "語意化命名", "程式可讀性", "認知負擔"]
toc: true
---

程式碼不是寫給電腦看的，是寫給人類讀的。電腦只管執行，人類才要維護。

<!--more-->

## 認知負擔：一切的出發點

人類工作記憶有限，大約一次只能處理七個項目（Miller's Law）。看到縮寫要在腦中展開、看到模糊詞要猜測含義、看到長函式要分段記憶——這些都是認知負擔。

自然語言化的目標很簡單：讓程式碼像讀文章一樣自然，把讀者的認知資源留給理解業務邏輯，而不是解碼程式碼本身。

---

## 第一原則：命名要能直接讀懂

### 函式命名

```dart
// 錯誤：不知道在做什麼
void process(data) {}
void handle(item) {}

// 正確：一眼看懂
void calculateBookReadingProgress(Book book) {}
void validateUserRegistrationData(User user) {}
void enrichBookMetadataFromExternalSource(Book book) {}
```

### 變數命名

```dart
// 錯誤：縮寫和多用途
var usr = getCurrentUser();
var data = loadUserData();
data = processBookData(); // 100行後同一變數換了意思

// 正確：明確且專用
final authenticatedUser = getCurrentUser();
final userProfileData = loadUserData();
final enrichedBookMetadata = processBookData();
```

### 類別命名

```dart
// 錯誤：說不清在做什麼
class Manager {}
class Handler {}
class BookDAO {}

// 正確：業務職責一目了然
class BookMetadataEnrichmentService {}
class UserRegistrationValidator {}
class LibraryBookSearchEngine {}
```

### 布林命名

布林變數應該能讀成問句，在 if 裡就能自然被理解：

```dart
bool isValid;      // "Is valid?"
bool hasPermission; // "Has permission?"
bool canEdit;       // "Can edit?"

// 不好：語意不清
bool permission;
```

### 常見命名反模式

- **匈牙利命名法**：`strName`, `intCount` — 型別系統自己會提供型別資訊，名稱不用重複
- **無意義前綴**：`theUser`, `aBook` — 沒帶來任何資訊，直接刪掉
- **過度縮寫**：`usrMgr` — 迫使讀者展開，`userManager` 更自然
- **數字後綴**：`user1`, `user2` — 改成 `primaryUser`, `secondaryUser` 才說明關係

---

## 第二原則：函式控制在五到十行

超過十行通常表示函式承擔了多重職責。判斷是否需要拆分的最快方法：函式名稱裡有「和」或「或」的話，一定要拆。

```dart
// 錯誤：15行，三種職責混在一起
Book processBook(String isbn) {
  if (isbn.length != 13) throw ArgumentError('Invalid ISBN');
  if (!isValidISBNChecksum(isbn)) throw ArgumentError('ISBN checksum failed');
  final apiResponse = httpClient.get('/books/$isbn');
  if (apiResponse.statusCode != 200) throw Exception('API failed');
  final bookData = json.decode(apiResponse.body);
  return Book.create(
    id: BookId(generateUniqueId()),
    title: BookTitle(bookData['title']),
    source: BookSource.external(),
  );
}

// 正確：拆成三個單一職責函式
Book createBookFromISBN(String isbn) {
  validateISBNFormat(isbn);
  final bookData = fetchBookDataFromExternalAPI(isbn);
  return buildBookFromExternalData(bookData);
}

void validateISBNFormat(String isbn) {
  if (isbn.length != 13) throw ArgumentError('ISBN must be 13 digits');
  if (!isValidISBNChecksum(isbn)) throw ArgumentError('ISBN checksum validation failed');
}

Map<String, dynamic> fetchBookDataFromExternalAPI(String isbn) {
  final apiResponse = httpClient.get('/books/$isbn');
  if (apiResponse.statusCode != 200) throw Exception('Failed to fetch book data');
  return json.decode(apiResponse.body);
}

Book buildBookFromExternalData(Map<String, dynamic> bookData) {
  return Book.create(
    id: BookId(generateUniqueId()),
    title: BookTitle(bookData['title']),
    source: BookSource.external(),
  );
}
```

---

## 第三原則：一個變數只做一件事

同一個變數在不同地方承載不同意義，是我見過最難追蹤的 bug 來源之一。

```dart
// 錯誤：同一變數三種身分
var result = validateUser(userData);
if (result.isValid) {
  result = processPayment(paymentData);
  if (result.success) {
    result = updateDatabase(result.data);
  }
}

// 正確：每個變數都有自己的名字
final userValidationResult = validateUser(userData);
if (userValidationResult.isValid) {
  final paymentProcessingResult = processPayment(paymentData);
  if (paymentProcessingResult.success) {
    final databaseUpdateResult = updateDatabase(paymentProcessingResult.data);
  }
}
```

變數生命週期也要管：

```dart
// 錯誤：books 在100行間一直換狀態
void processLibraryBooks() {
  var books = getAllBooks();
  books = filterAvailableBooks(books);
  books = sortBooksByTitle(books);
}

// 正確：每個階段的狀態都有名字
void processLibraryBooks() {
  final allLibraryBooks = getAllBooks();
  final availableBooks = filterAvailableBooks(allLibraryBooks);
  final sortedAvailableBooks = sortBooksByTitle(availableBooks);
}
```

---

## 第四原則：用事件驅動表達業務流程

複雜的業務流程往往會寫成一個大函式，裡面塞滿 if/else。問題不在於 if/else 本身，而是把不同職責的邏輯混在一起。

```dart
// 錯誤：驗證、API呼叫、結果處理全混在一起
void submitForm(FormData formData) {
  if (formData.name.isEmpty) { showErrorMessage('姓名不能為空'); return; }
  if (formData.email.isEmpty) { showErrorMessage('Email不能為空'); return; }
  if (!isValidEmail(formData.email)) { showErrorMessage('Email格式不正確'); return; }
  final apiResult = submitToAPI(formData);
  if (apiResult.success) {
    showSuccessMessage('提交成功');
    navigateToSuccessPage();
    clearForm();
  } else {
    showErrorMessage('提交失敗：' + apiResult.error);
    highlightErrorFields(apiResult.errorFields);
  }
}

// 正確：每個事件有自己的函式
void submitUserRegistrationForm(UserRegistrationFormData formData) {
  final validationResult = validateUserRegistrationData(formData);
  if (validationResult.isValid) {
    handleSuccessfulValidation(formData);
  } else {
    handleValidationFailure(validationResult.errors);
  }
}

ValidationResult validateUserRegistrationData(UserRegistrationFormData formData) {
  final errors = <ValidationError>[];
  if (!isValidUserName(formData.name)) errors.add(ValidationError.invalidUserName());
  if (!isValidUserEmail(formData.email)) errors.add(ValidationError.invalidEmail());
  return ValidationResult.fromErrors(errors);
}

void handleSuccessfulValidation(UserRegistrationFormData formData) {
  submitUserRegistrationToAPI(formData)
    .then(handleSuccessfulAPIResponse)
    .catchError(handleAPIFailure);
}

void handleValidationFailure(List<ValidationError> errors) {
  displayValidationErrors(errors);
  highlightInvalidFormFields(errors);
}
```

狀態機也是同樣的道理：

```dart
// 錯誤：一個函式根據狀態做完全不同的事
void updateBookStatus(Book book, String newStatus) {
  if (newStatus == 'available') {
    book.status = BookStatus.available;
    book.borrower = null;
    updateSearchIndex(book);
    notifyWaitingUsers(book);
  } else if (newStatus == 'borrowed') {
    book.status = BookStatus.borrowed;
    book.borrowDate = DateTime.now();
    sendBorrowConfirmation(book);
  } else if (newStatus == 'maintenance') {
    book.status = BookStatus.maintenance;
    removeFromSearchIndex(book);
    notifyMaintenanceTeam(book);
  }
}

// 正確：每個事件獨立
void handleBookReturnEvent(Book book) {
  executeBookReturn(book);
  notifyBookBecameAvailable(book);
}

void handleBookBorrowEvent(Book book, User borrower) {
  executeBookBorrow(book, borrower);
  confirmBorrowingToUser(book, borrower);
}

void handleBookMaintenanceEvent(Book book) {
  markBookForMaintenance(book);
  notifyMaintenanceRequired(book);
}
```

---

## 第五原則：可讀性優於簡潔性

程式碼的價值排序：正確性 > 可讀性 > 可維護性 > 簡潔性。

行數從來不是指標，清晰才是：

```dart
// 錯誤：為了少寫幾行犧牲可讀性
books.where((b) => b.s == 'a' && b.p > 100).map((b) => b.t).toList();

// 正確：每一步都說清楚在做什麼
final availableBooksWithMoreThan100Pages = allBooks
    .where((book) => book.status == BookStatus.available)
    .where((book) => book.pageCount > 100)
    .toList();

final bookTitlesForDisplay = availableBooksWithMoreThan100Pages
    .map((book) => book.title.value)
    .toList();
```

---

## 如何驗證程式碼品質

**陌生人測試**：讓不熟悉這段程式碼的工程師讀。5分鐘內能理解主要邏輯算合格，需要解釋才能理解就要重寫。

**自然語言測試**：把程式碼翻譯成中文說出來。翻譯流暢自然算合格，說不清楚就改命名。

**六個月後測試**：假設半年後的自己要修改這段程式碼，能快速找到位置算合格，不敢動怕壞掉就要重新設計。

---

每一行程式碼都是一句話，每個函式都是一個段落。好的程式碼是對未來維護者的體貼——不只是風格偏好，而是降低維護成本的工程決策。
