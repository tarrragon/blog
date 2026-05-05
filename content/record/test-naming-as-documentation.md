---
title: "測試命名作為文件：可執行的規格說明"
date: 2026-05-05
draft: false
description: "測試是少數會自我驗證的文件——名稱跟實際行為不符、CI 會炸。把測試命名寫成 state-based / scenario-based / failure-mode 三種模式的 spec 條目、配合 group 結構作為命名空間、讀者跳到測試檔掃名字就能取代讀 doc。"
tags: ["testing", "documentation", "code-quality", "methodology"]
---

> **核心命題**：測試是少數**會自我驗證**的文件——名稱說的事如果跟實際行為不符，CI 會炸。
> **設計原則**：測試命名應該讓「跳到測試檔讀名字」就能取代讀 doc。

> 本篇是 [函式文件分層設計](../function-doc-layered-design/) 的 Layer 4（範例與測試）展開——把「測試命名作為可執行 spec」這個職責拉成獨立主題討論。

---

## 起點：被 CI 強制同步的 doc

source code 的 doc comment 有個結構性缺陷：**寫得再好，code 改了 doc 沒改，doc 就在說謊**。沒有任何工具強制 doc 跟 code 同步。

測試是少數例外。一個命名為 `removes_item_when_quantity_reaches_zero` 的測試，如果實際上 quantity 到 0 時沒移除，**測試會失敗、CI 會擋下 commit**。測試名稱跟實際行為的一致性是被 CI 強制的——這讓測試成為**會自我驗證的文件**。

當你把這個性質有意識地利用起來，測試就不只是 regression 工具，而是**可執行的 API 規格**。

---

## 測試命名的三種主要模式

被測單元的契約大致分三類：「**在某狀態下回傳什麼**」「**某操作會做什麼**」「**何時 throw / 失敗**」——對應到測試命名也分三類 pattern。每類 pattern 的命名格式不同、負責驗證契約的不同切面。

### 模式 1：state-based（狀態描述）

「在某個狀態下，呼叫 X 會回傳 / 變成什麼」。

```dart
test('returns_null_when_user_not_found', () { ... });
test('returns_empty_list_when_no_items_match', () { ... });
test('returns_cached_value_on_second_call', () { ... });
```

適合：query / read-only 操作。

### 模式 2：scenario-based（情境描述）

「當某條件成立時，操作會做什麼」。

```dart
test('removes_item_when_quantity_reaches_zero', () { ... });
test('decreases_quantity_when_item_exists_with_quantity_above_one', () { ... });
test('updates_lastChangedItem_on_addItem', () { ... });
test('does_not_update_lastChangedItem_on_removeItem', () { ... });
```

適合：command / mutation 操作。注意 `does_not_X` 形式——**negative assertion 也該寫進名字**，這正是契約的一部分。

### 模式 3：failure-mode（失敗模式描述）

「在某輸入 / 狀態下，會 throw / error / 失敗」。

```dart
test('throws_NotFoundException_when_id_does_not_exist', () { ... });
test('throws_StateError_when_called_after_dispose', () { ... });
test('returns_error_when_network_unavailable', () { ... });
```

適合：error path、edge case。**失敗模式是 doc 最容易漏寫的部分**，但對 caller 最關鍵。

---

## Group 結構作為命名空間

巢狀 group 提供了「主題 → 操作 → 情境」的階層命名空間，比扁平命名更易讀：

```dart
group('CartService', () {
  group('addItem', () {
    test('appends_when_item_not_in_cart', () { ... });
    test('increments_quantity_when_same_item_exists', () { ... });
    test('updates_lastChangedItem', () { ... });
  });

  group('removeItem', () {
    test('removes_when_item_exists', () { ... });
    test('does_nothing_when_item_not_found', () { ... });
    test('does_not_update_lastChangedItem', () { ... });
  });

  group('decreaseQuantity', () {
    test('decreases_when_quantity_above_one', () { ... });
    test('removes_item_when_quantity_reaches_zero', () { ... });
  });
});
```

讀者掃過 group 結構，立刻知道 `CartService` 對外提供哪些操作、每個操作有哪些行為承諾——**這是這個 service 的 readable spec**。

工具支援：好的 IDE / test runner 會把 group 結構顯示為樹狀，跑測試時的輸出也帶階層。把這個視覺結構利用好，測試 console 本身就是 doc 瀏覽器。

---

## 把 tests 當 readable spec 的閱讀流程

當你不確定一個 function 的行為時，閱讀順序通常是：

1. **看簽章** → 知道 what / takes / returns
2. **讀 doc** → 知道契約、edge case
3. **看實作** → 知道 how
4. **找測試** → 看具體 case

但如果測試命名做得好，**順序可以對調**：

1. 看簽章
2. **跳到對應 test file，掃 group + test names** → 看 API 支援哪些 case、各 case 的承諾
3. 不夠才回去讀 doc / 實作

這個順序的優勢：

- **測試名是被驗證過的事實**，doc 是聲明（可能 outdated）
- **測試名涵蓋 edge case**，比 doc 完整
- **跳到測試只要一個快捷鍵**（多數 IDE 有 "Go to Test" 命令）

當團隊習慣這個閱讀順序，**doc 寫多寫少的壓力就會減輕**——很多 edge case 直接讓測試說明，doc 留給「測試也表達不了」的部分（業務動機、隱性需求）。

---

## 反模式

### 反模式 1：`test_` 前綴 + 模糊主題

**正向概念**：測試名字的每個 token 都該承載資訊——前綴或主題詞如果讀者一眼推不出「在驗什麼」、就是浪費 token budget。

```dart
// 反：純 noise
test('test_user', () { ... });
test('test_user_2', () { ... });
test('test_user_creation', () { ... });

// 正：說明具體行為
test('creates_user_with_default_role_when_role_omitted', () { ... });
```

`test_` 前綴是工具年代留下的習慣（早期某些 framework 靠它識別測試 method）；現代 framework 用 annotation / 函式簽章識別、前綴變成純 noise。模糊的主題（`test_user`、`test_creation`）等於沒命名——讀者必須跳進 body 才能分辨兩個 test 在驗什麼、命名的 doc 價值消失。

### 反模式 2：實作洩漏的命名

**正向概念**：測試驗的是**對外可觀察的契約**——換實作而契約沒變、測試應該繼續通過、命名也不該需要改。

```dart
// 反：洩漏實作（用 hashmap、用 cache）
test('uses_hashmap_for_lookup', () { ... });
test('caches_result_after_first_call', () { ... });

// 正：描述對外可觀察行為
test('returns_value_in_O_1_for_existing_key', () { ... });
test('subsequent_calls_return_same_instance', () { ... });
```

命名洩漏實作後、重構（換 hashmap 為 trie、移除 cache 改用 lazy init）會逼迫測試一起改名——但對外行為其實沒變。一個良好的契約測試、應該在 codebase 大改造後仍能驗證「行為是否還是當初承諾的樣子」、命名洩漏實作會破壞這個性質。

### 反模式 3：描述「怎麼做」而非「做什麼」

**正向概念**：測試名描述「被測單元的契約」、test body 描述「測試怎麼寫」——分配給對應的位置、讀者跳到名字看契約、跳到 body 看細節。

```dart
// 反：描述測試怎麼跑（過程）
test('mocks_db_and_calls_findUser_then_asserts_result', () { ... });

// 正：描述被測 function 的行為
test('returns_null_when_user_not_found', () { ... });
```

把「mocks_db_and_calls_X」寫進名字、讀者拿到的是「測試怎麼寫的過程」、不是「被測單元承諾什麼」——但讀 spec 想知道的是後者。「怎麼寫」放 test body、「驗證什麼契約」放名字、兩種讀者都得益。

### 反模式 4：assertion-style 命名

**正向概念**：測試名是業務語義的入口、不是 assertion 框架的字面映射——讀者讀名字想推「業務上發生什麼」、不是「assert 用了哪個動詞」。

```dart
// 反：assertion 寫在名字
test('isFalse_when_disabled', () { ... });
test('equal_when_same_input', () { ... });

// 正：描述行為
test('returns_false_when_feature_disabled', () { ... });
test('returns_same_result_for_equivalent_inputs', () { ... });
```

`isTrue`、`equal`、`isNotEmpty` 是 assertion 動詞、不是行為描述。讀者讀 `isFalse_when_disabled` 不知道「false」對應什麼業務語義（feature 關掉？user 不存在？status 失效？）——把業務語義寫進名字、讀者一眼就能 map 到實際情境。

### 反模式 5：用 numbering 取代命名

**正向概念**：每個 test case 都有獨特的「驗什麼情境」、命名就是把那個情境寫出來。編號只負責「不重複」、不負責「能識別」——失去命名最關鍵的功能。

```dart
// 反：靠編號區分
test('addItem_case_1', () { ... });
test('addItem_case_2', () { ... });
test('addItem_case_3', () { ... });

// 正：編號變描述
test('addItem_appends_when_cart_empty', () { ... });
test('addItem_increments_when_same_item_exists', () { ... });
test('addItem_handles_null_customization', () { ... });
```

編號是「我懶得想名字」的訊號。讀者要跳進 test body 才能區分 case 1 跟 case 2 是什麼差別——失去測試命名的全部 doc 價值；CI 報告看到「`addItem_case_2` 失敗」也無從直接判斷哪個情境壞了。

---

## 邊界：什麼時候測試名不適合當 spec

「測試名是 spec 條目」是預設、**但有些情境測試命名無法獨自承擔 doc 責任**：

- **大量參數化 / property-based test**：「對任意輸入 N、結果都 ≥ N」這類 invariant、命名只能寫概念名（`preserves_minimum`）、具體 input 範圍要靠 doc 或 generator 描述
- **整合 / e2e test**：跨多個系統的行為、命名常壓不下完整流程（「user_can_complete_checkout_with_loyalty_points_and_split_payment」）、要靠 setup / scenario doc 補上下文
- **測試本身是業務動機的二次表達**：例如 GDPR 合規規則、業務動機的詳細條款仍要寫在介面 doc / spec 文件、命名只負責「驗證點」
- **內部行為對齊 vs 對外契約**：私有 helper / internal worker 的測試命名不必當公開 spec、可以直接用實作詞彙（這時候命名價值是「regression 防護」而非「對外文件」）

判斷標準：「讀者只看名字、能不能拿到他要的資訊？」答「能」就讓命名當 spec 用、答「不能」就把詳細上下文寫進 doc / scenario file、命名只當「定位錨點」。

---

## 給測試寫作的 checklist

寫一個 test 之前，跑這個 checklist：

- [ ] **名字能不能讓讀者不看 body 就知道驗證什麼？** 不能 → 重命名
- [ ] **名字描述的是被測 function 的契約嗎？** 不是（描述測試過程）→ 重寫
- [ ] **名字有沒有業務面詞彙？** 沒有（只有 assertion 動詞）→ 加業務詞彙
- [ ] **同 group 下這個名字跟其他 test 有區辨度嗎？** 沒有（靠編號）→ 加情境描述
- [ ] **這個行為契約是 doc 沒寫但這個 test 在驗的嗎？** 是 → 太好了，這個 test 補了 doc 漏洞
- [ ] **這個 test 在驗實作細節嗎？** 是 → 改成驗對外可觀察行為，否則重構必折斷

---

## Trade-off：測試名變長的代價

把測試當 doc 寫，名字會變長——`addItem_increments_quantity_when_same_item_exists_with_identical_customizations` 比 `test_add` 長 5 倍。

值得嗎？看你怎麼讀測試：

- **只看綠紅燈、不讀名字** → 短名字便利
- **把測試當 spec 讀** → 長名字回收成本

多數團隊低估「把測試當 spec 讀」的價值，因為這個習慣需要團隊一致才有效——一個人寫好命名，其他人不讀，回收不到。**這是團隊習慣問題，不是個人偏好問題**。要建立這個習慣，最好的切入點是：

1. **新功能 PR 直接讀新 test 的名字判斷契約是否合理**——把命名變成 review 的一環
2. **修 bug 時要求新增的 regression test 名字描述 bug 行為**（例如 `does_not_double_charge_on_retry`）——這些名字本身是 incident 紀錄
3. **重構 PR 不允許改 test 名**（除非是改名抓 bug 暴露的契約變動）——避免重構順手「整理」掉重要命名

---

## 一句話 heuristic

把整個討論濃縮：

> 測試名是「**讀者跳到測試檔、不看 body 就能讀懂的 spec 條目**」。

寫測試名時想像一個讀者只會看到名字，他要能從名字推得：

- 在驗哪個操作？
- 在哪個情境下？
- 期待什麼結果？

三件事缺一不可。寫到名字過長覺得難寫——通常是被測 function 同時在做多件事，**測試名長是設計訊號**，先別急著縮名字，先想能不能拆 function。

---

## 收束：測試命名是文件設計的一環

回到開頭——測試是少數會自我驗證的文件。但這個性質**只在你有意識利用時才有價值**。把測試名寫成 `test_1`、`test_2`，你寫的是 regression 網，不是 doc。

把測試名寫成可讀 spec 條目，你寫的是同時包辦兩件事的東西：**驗證 + 文件**。這兩件事用同一份成本同時做完，是測試這個工具的最高槓桿用法。

下次寫 test 時想：「**如果這份 test file 是這個模組唯一的 doc，讀者夠不夠用？**」——把這個問題當質量門檻，測試命名自動會變好。
