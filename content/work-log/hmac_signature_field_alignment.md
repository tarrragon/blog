---
title: "HMAC 簽章對接：演算法拆解與兩端輸入對齊"
slug: "hmac_signature_field_alignment"
date: 2026-07-27
draft: false
description: "兩端 HMAC 算不出同一個值時要逐項核對的輸入定義，以及用簽章反推輸入、判斷問題落在哪一端的除錯手法。"
tags: ["security", "hmac", "api", "dart", "debugging", "integration"]
---

> **對接情境**：呼叫外部系統的 API，對方用 HMAC 簽章驗證呼叫方身分，回 403 但沒有說明哪個欄位對不上
> **整理目的**：記下 HMAC 的實際運算過程、兩端必須逐字對齊的輸入項目，以及用確定性反推輸入的除錯手法
> **本文邊界**：以 HMAC-SHA256 為例，其他雜湊演算法的結構相同；程式碼以 Dart 示範、對照 PHP 接收端，判讀方式與 openssl 參照值不限語言，涉及編譯期常數的段落為 Dart 與 Flutter 特有；密鑰的配發與輪替另有主題

---

## HMAC 承擔的責任

HMAC 證明兩件事：這個請求出自持有密鑰的人，而且內容從發出到接收沒有被改過。它把「身分」與「完整性」綁在同一個值上，接收方只要用同一把密鑰重算一次，比對結果就能同時驗證兩者。

HMAC 的作用範圍限於認證。產生的簽章公開可見，訊息本身也照常明文傳輸 —— 它提供的是**認證**而非**保密**。想讓內容不可讀，需要的是傳輸層加密或內容加密，那是另一組機制。

這個定位決定了排錯方向：簽章對不上時，問題落在「雙方對輸入的定義不一致」，而不是「加密解密失敗」。

## 演算法實際在做什麼

HMAC 的呼叫在多數語言只有幾行，底下卻有四個決策點，每一個都是兩端可能對不齊的地方：

```dart
final key = utf8.encode(secret);
final message = utf8.encode('$timestamp$payload');
final digest = Hmac(sha256, key).convert(message);
return digest.toString();
```

### 輸入是位元組序列

雜湊函式接受的是位元組，字串需要先決定編碼方式。`utf8.encode` 把這個決定寫死，讓兩端對「同樣的字對應哪些位元組」有共識。

字串串接同樣要精確。`'$timestamp$payload'` 產生的是連續字元，中間沒有分隔符：

```text
'1784878245' + '[]'  ->  '1784878245[]'  ->  12 個位元組
```

對應到 PHP 的 `$timestamp . $payload` 是同一件事。這裡常見的落差是引號 —— 後端 dump 出來的 `"payload" => "[]"` 是輸出格式加的引號，實際值只有 `[` 和 `]` 兩個字元。

### 密鑰經過內外兩層衍生

HMAC 的定義是巢狀的兩次雜湊：

```text
HMAC(K, m) = H( (K' XOR opad) || H( (K' XOR ipad) || m ) )
```

其中 `K'` 是密鑰補零到雜湊的區塊長度，超過長度的密鑰先雜湊過再用；`ipad` 是位元組 `0x36` 重複填滿一個區塊，`opad` 是 `0x5c`。區塊長度隨演算法而定，SHA-256 是 64 位元組，SHA-512 是 128 —— 換演算法時這個常數要跟著換，否則算出的值會與函式庫對不上。

手工實作可以驗證這個結構：

```dart
String hmacByHand(List<int> key, List<int> message) {
  const blockSize = 64;

  final normalizedKey = key.length > blockSize
      ? sha256.convert(key).bytes
      : key;
  final paddedKey = Uint8List(blockSize)..setAll(0, normalizedKey);

  final innerKey = paddedKey.map((byte) => byte ^ 0x36).toList();
  final outerKey = paddedKey.map((byte) => byte ^ 0x5c).toList();

  final innerDigest = sha256.convert([...innerKey, ...message]).bytes;
  return sha256.convert([...outerKey, ...innerDigest]).toString();
}
```

跑起來會跟函式庫的輸出逐字相同。

### 兩層結構擋掉長度延伸攻擊

直觀的做法是把密鑰接在訊息前面直接雜湊，兩者的輸出完全不同：

以 `secret = 'k'`、`message = '1784878245[]'` 為例：

```text
HMAC(secret, message)          -> d436a5cb070ecd04162da2186f7db52b2e365faeefa0492fb8cd176675823124
sha256(secret + message)       -> c9ac394e856626f834054d4b9747f4e42183db1cf22a157e170fa268bc321d88
```

差異來自安全性而非風格。SHA-256 屬於 Merkle–Damgård 結構，這類雜湊有一個性質：知道 `H(secret + m)` 的值、`m` 的內容，以及 `secret` 的長度，就能在不知道 `secret` 本身的前提下，算出 `H(secret + m + 補位 + 延伸內容)` 的合法值。長度未知時可以逐一窮舉，候選數量通常不大。偽造出的訊息會夾帶原本的補位位元組，並非乾淨的尾端追加 —— 判斷這條攻擊在自己的格式下是否可行時，要看接收端會不會接受這段補位落在 payload 中間。外層再包一次雜湊切斷了這條路徑。

理解這點的實務價值在於：對方文件寫 `hash_hmac` 或 `HMAC` 時，就要用函式庫的 HMAC 實作。自行以 `sha256(secret + message)` 拼接算出的值不會與它吻合。

### 輸出是小寫十六進位

`Digest` 內部是 32 個位元組，`toString()` 轉成小寫十六進位共 64 個字元。PHP 的 `hash_hmac()` 預設輸出同樣格式，所以兩端天然對齊。改用 Base64 或大寫十六進位的系統也存在，對接時先確認對方的輸出格式。

這個固定長度可以寫進測試當作格式護欄：

```dart
expect(headers['X-Signature'], matches(RegExp(r'^[0-9a-f]{64}$')));
```

## 兩端必須逐項對齊的輸入

簽章值只呈現吻合或不吻合，本身不指出差異落在哪一項，所以對接時把輸入拆成獨立項目逐一確認，比反覆重試有效率。以下說的簽章素材，就是選型層與知識卡所稱的「驗證素材」——進入計算的那串內容。

| 項目             | 要確認的內容                               | 常見落差                                    |
| ---------------- | ------------------------------------------ | ------------------------------------------- |
| 素材組成         | 哪些欄位進簽章、順序如何、有無分隔符       | 一端加了分隔符、或多納入一個 header         |
| 時間戳單位       | Unix 秒或毫秒                              | 語言預設值不同，Dart 與 Java 慣用毫秒       |
| 空請求的 payload | 沒有 request body 時，簽章素材那一段填什麼 | 一端用空字串、一端用 `[]`                   |
| 字元編碼         | UTF-8 或其他                               | 非 ASCII 字元才會顯現，測試資料常是純 ASCII |
| 輸出格式         | 十六進位大小寫、或 Base64                  | 文件常省略不寫                              |

### 時間戳單位的特殊之處

接收方通常直接以 header 的原字串進簽章素材，因為重新格式化會多引入一個要對齊的決策點。在這個前提下，發送方送毫秒、接收方也用同一串字重算 —— **簽章本身會吻合**。真正擋下請求的是另一道時效檢查：把毫秒值當秒解讀會落在數萬年後，任何有效期窗口都不會通過。接收方若先把時間戳解析成整數、再依自己認定的單位重新格式化才進素材，簽章就會不吻合，這一段的結論反過來。

所以「簽章算法正確但仍被拒絕」是有可能的。排查時把「簽章比對」與「時效檢查」當成兩道獨立關卡，比籠統地懷疑「簽章有問題」更快收斂。

時效檢查本身的窗口該設多寬，取決於兩端的 [時鐘偏移](/backend/knowledge-cards/clock-skew/) 而非單位換算，那是另一個獨立的參數。

判讀訊號：如果對方的錯誤堆疊在修正某一項之後**換了位置**（例如從第 26 行移到第 46 行），代表通過了前一道檢查、撞上下一道。錯誤位置改變是進度的證據。

### 空請求的 payload

沒有 request body 的端點，簽章素材裡的 payload 段落取決於接收方怎麼取值：

- 讀原始 body（`$request->getContent()`）：空請求得到空字串
- 讀解析後的參數再序列化（`json_encode($request->all())`）：空請求得到 `[]`

兩者在文件上都可能被寫成「payload」。想同時滿足兩種實作，可以讓 request body 就是簽章素材本身 —— 送出的位元組與簽名的位元組是同一份，接收方無論用哪種取法都會得到相同結果。

## 用簽章反推輸入

HMAC 是確定性的：同樣的密鑰與訊息永遠產生同樣的輸出。這個性質可以反過來用 —— 手上有對方收到的簽章與時間戳，加上自己的密鑰，就能反解出「送出去的那一刻，實際用的是哪組輸入」。

完整可執行的腳本如下。放進一個空目錄，`pubspec.yaml` 只需要 `crypto` 一個依賴，密鑰放同目錄的 `.env.local`（內容一行 `API_SECRET=實際密鑰`）：

```dart
// verify_signature.dart
import 'dart:convert';
import 'dart:io';

import 'package:crypto/crypto.dart';

String sign(String secret, String timestamp, String payload) {
  final key = utf8.encode(secret);
  final message = utf8.encode('$timestamp$payload');
  return Hmac(sha256, key).convert(message).toString();
}

String readSecret(String path) {
  final line = File(path)
      .readAsLinesSync()
      .firstWhere((line) => line.startsWith('API_SECRET='));
  return line.split('=').sublist(1).join('=').trim();
}

void main(List<String> args) {
  final sentTimestamp = args[0];
  final sentSignature = args[1];
  final secret = readSecret('.env.local');

  for (final payload in const ['[]', '', '{}', 'null']) {
    final signature = sign(secret, sentTimestamp, payload);
    print('payload = $payload\t相符: ${signature == sentSignature}');
  }
}
```

```bash
dart pub add crypto
dart run verify_signature.dart 1784878245 d436a5cb070ecd04162da2186f7db52b2e365faeefa0492fb8cd176675823124
```

有一組吻合，就同時證明了兩件事：payload 定義是那一個，而且本機實作與執行中的程式走同一條路徑。對外部規格的正確性由另一件事負責：拿對方的測試向量或語言中立的參照值重現他們的簽章（下一節的檢查順序會用到）。兩者證明的是不同的事 —— 自己的兩端可以一致地錯，例如同時漏掉一個欄位。

沒有任何一組吻合，代表變因落在候選集合之外：真實的 payload 取值不在清單裡、素材組成多納入了欄位（路徑、method 或額外 header）、串接順序或分隔符不同，也可能是本機密鑰與執行中的程式不同。順序上先擴大 payload 與素材組成的候選，再懷疑密鑰 —— 密鑰不一致是四種成因裡最少見的一種。

這個手法在編譯期常數的情境特別有用。以 Dart 為例，`String.fromEnvironment` 的值在編譯時就被寫進產出物，改了設定檔之後若只做 hot reload，執行中的程式仍然帶著舊值 —— 這種狀態在裝置上完全看不出來，卻能被反推立刻辨識。

**操作前提**：驗證腳本從設定檔讀密鑰，不從命令列參數傳入。命令列參數會留在 shell 歷史與行程列表裡。

## 對接時的檢查順序

問題可能落在網路層、輸入定義或密鑰本身，由外而內排查能較快縮小範圍：

1. **請求真的到了預期的位置** —— 在送出前把最終組出來的 URL 整串印出來，不是印 path 常數；兩者的差異正是中介層改寫的落點。全域的路徑改寫（語系前綴之類）常會套用到不該套用的外部呼叫上。對方端有存取日誌時，拿他們記錄到的路徑與自己印出的字串逐字比對，一次就能定位。
2. **確認演算法與素材組成算得出預期的值** —— 對方提供測試向量時直接重現它。對方沒有提供時，用系統內建的 `openssl` 建立一個語言中立的參照值：

   ```bash
   printf '1784878245[]' | openssl dgst -sha256 -hmac 'k'
   ```

   `printf` 不附加換行，這一點決定結果 —— `echo` 會多送一個 `\n`，算出完全不同的值。輸出的 `d436a5cb...` 拿來與自己程式的輸出比對，相符就證明實作沒問題，範圍收斂到素材定義。這條路徑不限語言，Node、Python、Go 的實作都能用同一個參照值校準。
3. **用實際送出的簽章反推輸入** —— 確認執行中的程式用的密鑰與 payload 定義符合預期。
4. **前三項都通過仍被拒絕** —— 範圍已收斂到接收方的設定，這時請對方提供四項資料：他們重算出的簽章值、重算所用的素材字串（標出分隔符位置）、他們收到的 timestamp 與 body 原文、以及拒絕的原因碼（簽章不符或時效過期）。這四項對應前文的四個決策點，拿到之後不需要再往返第二輪。

前三項都能在本機完成，不需要對方配合，也不需要反覆重新部署。

## 判讀與邊界

**這篇適用的情境**：串接使用 HMAC 簽章驗證的外部 API、簽章比對失敗且錯誤訊息不具體。

**不在範圍內**：密鑰的配發、儲存與輪替機制；簽章之外的授權判斷（呼叫方有沒有權限存取該資源）；HTTPS 傳輸層安全。這些是獨立的設計問題。為什麼這個場景選訊息驗證而不是加密、金鑰該放在哪一端，屬於它上一層的選型判斷，見 [7.28 密碼學原語選型](/backend/07-security-data-protection/cryptographic-primitive-selection/)；在同一批機器憑證機制裡為什麼選它，見 [7.34 機器憑證的機制選型](/backend/07-security-data-protection/machine-credential-mechanism-selection/)。素材對齊之外的另一個收斂條件（時間戳與識別值要被檢查）與這一篇是同一階段的工作，判讀見 [7.35 簽章對接的驗證收斂](/backend/07-security-data-protection/signature-integration-verification/)；機制本身的責任邊界見 [Message Authentication](/backend/knowledge-cards/message-authentication/)。

自己也是接收方時（雙向對接的情況），比對簽章要用等時比較函式而不是一般的字串相等運算，理由與逐位元組短路造成的洩漏見 [Timing Attack](/backend/knowledge-cards/timing-attack/)。

對接完成之後，有兩個檢查值得留成測試而不是留在記憶裡。密鑰為空時要輸出明確訊息，否則它會偽裝成後端問題，讓排查方向整個偏掉。時間戳單位要寫成斷言（送出值與現在時間的差距落在合理範圍內），只檢查欄位有值的斷言對單位錯誤完全是盲的 —— 而單位錯誤正是這類對接最常復發的一項。
