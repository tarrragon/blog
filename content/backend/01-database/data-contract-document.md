---
title: "1.15 資料契約文件（Data Contract Document）"
date: 2026-07-26
description: "schema 表達不了的語意承諾——欄位單位、跨欄不變式、錯誤語意——需要專屬 artifact；整理可攜性兩區、兩旗標適用條件與 dormant 表豁免"
weight: 15
tags: ["backend", "database", "data-contract", "schema"]
---

資料契約文件（data contract document）的核心責任是承載 schema 表達不了的[語意承諾](/backend/knowledge-cards/contract/)：欄位的單位與格式粒度、跨欄位的不變式、狀態責任分層、錯誤語意的翻譯規則。DDL 能表達型別與約束、表達不了「為什麼這樣設計」與「哪些邏輯在遷移後仍然成立」；這些語意若沒有專屬載體、就只存在原作者的記憶裡。

本章結合 [1.2 Schema Design](/backend/01-database/schema-design/)（結構設計）、[1.4 Repository Adapter](/backend/01-database/repository-adapter/)（port / adapter 邊界）與 [1.7 Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/)（狀態契約先行）一起讀。讀完後能回答：哪些語意需要專屬文件、文件怎麼分區、什麼情況下合法地省下這份文件。

## 為什麼 schema 承載不了全部語意

schema 是唯一與程式碼同步執行的規格層：CHECK 違反時資料庫直接拒絕寫入、沒有人需要記得去查文件。所以第一原則是「能寫成約束的優先寫成約束」——CHECK / UNIQUE / FK / NOT NULL 應該像驗收條件一樣被設計、契約文件只承載 DDL 表達不了的部分。

問題在於「表達不了的部分」比直覺中大。兩個常見事故形態可以說明這個缺口。

### 案例一：時間戳單位混用

某表的時間欄位在 DDL 用 `DEFAULT (strftime('%s','now'))` 產生預設值、單位是秒；應用層寫入路徑用語言標準庫的 epoch 毫秒寫入。兩條路徑寫進同一個 INTEGER 欄位、型別系統完全無從分辨——秒和毫秒都是合法整數。

混存的資料在排序與區間查詢時靜默錯亂：毫秒值比秒值大三個數量級、時間軸查詢把毫秒寫入的資料排到「未來數萬年」、把秒寫入的資料判在區間之外。讀取端出現 1970 年附近或遙遠未來的異常日期、通常是這個問題浮上檯面的第一個訊號。

這裡的教訓是：**單位是語意、型別表達承載範圍**。INTEGER 只保證「這是整數」、單位承諾（秒還是毫秒、UTC 還是本地時間）需要一個權威載體。把單位寫進契約文件的欄位語意表、並讓 DDL 預設值與應用層寫入路徑都對照同一條契約、才能讓「兩條寫入路徑各自表述」在 review 時被看見。

引擎有原生時間型別（TIMESTAMP、DATETIME）時、優先用型別本身消除單位歧義；契約文件承載的是型別表達不了的情境——選用 INTEGER epoch 的單位決策、時區慣例。

### 案例二：DDL 註解的枚舉值漂移

另一個常見形態：欄位用 DDL 註解列舉合法值、例如 `-- status: 'pending' | 'paid' | 'cancelled'`。系統演進後程式碼的枚舉多了兩個值、註解沒有同步；半年後新成員按註解實作報表查詢、漏掉兩種狀態的資料。

註解的問題是**沒有執法能力、也沒有漂移偵測**。程式碼改了、註解不會報錯；資料寫入了註解沒列的值、資料庫照收。把註解當成契約載體、等於把契約放在一個沒人負責同步的位置。

枚舉值域的權威來源有三個選項、按值域特性選擇：

| 權威來源          | 適用情境                                       | 執法方式                         |
| ----------------- | ---------------------------------------------- | -------------------------------- |
| CHECK 約束        | 值域小且穩定、變更頻率低                       | DB 層拒絕違反寫入                |
| lookup table + FK | 值域會成長、或每個值帶附加屬性（顯示名、排序） | FK 保證引用完整性、新值走 INSERT |
| 契約文件          | 值域由應用層治理、DB 層刻意不執法              | 契約條目對應測試、review 時比對  |

選哪一個是設計決策、三者都比「只靠註解」可靠。DDL 註解仍然可以寫、但定位是導覽提示、權威來源在上表三選一。

## 契約文件的分區：可攜性兩區

契約文件的內容依「資料庫遷移後是否仍成立」分成兩區。判斷標準來自 [1.4 Repository Adapter](/backend/01-database/repository-adapter/) 的 port / adapter 邊界：repository 介面跨引擎成立的語意歸 A 區、引擎專屬的實作機制歸 B 區。

| 區塊           | 判斷標準                          | 資料庫遷移後   |
| -------------- | --------------------------------- | -------------- |
| A 區：邏輯契約 | DB-agnostic、描述業務語意與不變式 | 仍成立、照搬   |
| B 區：實作綁定 | DB-specific、描述特定引擎實現機制 | 需依新引擎重寫 |

**A 區承載的內容**：

- **欄位語意**：單位、值域、格式粒度（案例一的時間戳單位就放這裡）
- **狀態責任分層**：canonical（正式狀態、唯一寫入來源）／derived（衍生、只能 rebuild）／追蹤欄位（審計用）——與 [1.8 State Ownership](/backend/01-database/state-ownership-query-boundary/) 的分層對齊
- **不變式清單**：跨欄位、跨表的業務規則陳述（例如「同一分類至多一筆活躍記錄」）、只陳述規則本身、把保證層歸屬留給 B 區
- **交易邊界**：哪些寫入必須一起成立、只描述原子性要求、[isolation level](/backend/knowledge-cards/isolation-level/) 屬 B 區
- **錯誤語意契約**：唯一鍵衝突、外鍵違反對應哪個 domain error——這是 [1.4](/backend/01-database/repository-adapter/) error translation 的規格來源
- **恢復模型**：備份還原後如何驗證資料完整

**B 區承載的內容**：

- **保證層歸屬**：每條 A 區不變式由誰保證——DB 約束、應用層驗證、或雙層。歸屬是綁定決策：換引擎後不變式陳述不變、保證方式可能重新分配
- **引擎機制**：upsert 語法、FK 刪除策略、CHECK 違反的例外型別行為
- **schema 演進策略**：凍結或支援升級、與 [Expand / Contract](/backend/knowledge-cards/expand-contract/) 模式的銜接

分區的價值在遷移評估時兌現：換 DB 時 A 區整份照搬、B 區按新引擎重寫、工作量邊界在動手前就清楚。分區也讓 review 更聚焦——A 區變更代表業務語意變了、需要 domain 層的人看；B 區變更是實作調整、資料庫層的人可以獨立判斷。

「用 ORM model 取代契約文件」是常見的反駁：model 定義已經寫了型別與約束、何必再維護一份文件。這個反駁不成立、因為 ORM model 與 DDL 同屬型別 + 約束表達層——同樣表達不了單位、跨欄不變式的設計理由、錯誤語意的翻譯規則、恢復模型；且 ORM schema 綁定特定引擎與框架、屬 B 區綁定物而非 A 區邏輯契約。ORM 選型的取捨見 [Repository Adapter](/backend/01-database/repository-adapter/) 的「ORM vs Query Builder vs Raw SQL」段。

### 契約↔測試的最低要求

契約條目要成為可驗證的規格、而非只供閱讀的敘述、最低要求是：每條契約條目至少對應一個直接針對該約束行為的測試；mock 層測試不計入 DB 約束覆蓋——mock 不經過真實引擎、驗不到約束的實際行為。

## 適用條件：兩個正交旗標

契約文件有維護成本、寫不寫應該有判斷標準、判斷標準用兩個獨立旗標：

| 旗標           | 判斷標準：要                    | 判斷標準：不要           |
| -------------- | ------------------------------- | ------------------------ |
| 契約文件       | 多人或 AI 代理協作、有交接需求  | 單人專案、無交接對象     |
| migration 治理 | 已上線有存量資料、schema 需演進 | 全新專案或 schema 已凍結 |

兩個旗標各自獨立判定、四種組合各有對應投入：兩者皆要就是完整配置（契約文件 + [1.6 Migration Playbook](/backend/01-database/database-migration-playbook/) 的分段驗證流程）；只要其一就只補其一。

用兩個正交旗標、放棄線性分級（L1 / L2 / L3 這類）、理由是正交的邊界案例在線性軸上沒有位置：「單人小專案、但已上線且有存量資料」——契約文件旗標為否、migration 治理旗標為要。線性分級會把這種組合硬塞進某一級、正交旗標讓它被正確分類。兩個旗標的判斷標準邊界仍在跨場景校準中、遇到上表覆蓋不到的組合時、記錄場景並回饋判斷標準本身。

### 降級出口：僅 DDL 註解是合法終態

兩旗標皆否時、**僅維持 schema 約束 + DDL 註解就是合法終態**。這是有依據的豁免、給判斷標準一個明確的「零文件」出口、讓小專案免於為了完整感而製造文件。

沒有這個出口、判斷標準會退化成「所有專案都該有契約文件」——而為了合規而寫的文件、沒人讀也沒人更新、腐爛後反而比沒有文件更誤導（讀者以為它是權威、它已經過期）。降級出口讓「省下這份文件」是一個被判斷標準支持的決定、可以被 review、也可以在旗標翻轉時（例如專案開始多人協作）被重新檢視。

## Dormant 表豁免：文件跟著行為走

**dormant 表**：schema 已建立、寫入方法已實作、但沒有 production 觸達路徑的表——依賴注入（DI）沒接線、或呼叫鏈終止於死路。

對 dormant 表撰寫契約文件是負債。契約文件描述的是寫入路徑的行為事實；沒有 production 寫入路徑、就沒有行為事實可承載、寫出來的文件只能複述 DDL、並在首次真實接線時全文重審。所以 dormant 表可以豁免契約撰寫——但豁免要有依據、依據要可驗證。

### 三軸觸達實查

判定一張表 dormant、單靠程式碼註解（「規劃中」「未來擴充」）或一次 grep 命中數量都會誤判：漏看間接呼叫鏈、或誤信過期註解。豁免前用三個軸交叉驗證、每軸都留下可重跑的指令與命中結果：

| 軸       | 驗證內容                                                                                                        | 完成條件                                           |
| -------- | --------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| 表名軸   | 表名關鍵字反查全部程式碼、逐一分類每個命中是寫入還是型別引用                                                    | 全部命中檔案逐檔標註分類、只看命中數量算未完成     |
| 呼叫者軸 | 該表寫入方法（insert / update / delete）反查全部呼叫者                                                          | 每個寫入方法的呼叫者清單完整列出、測試替身標註排除 |
| 消費鏈軸 | 對每個呼叫者逐層上溯實例化點與 DI 消費者、直到服務進入點（API handler、排程 job、consumer）或 UI 進入點、或死路 | 每條鏈的終點明確判定「觸達」或「死路」、死路附成因 |

三軸缺一即判定失效：表名軸顯示低使用頻率、只是必要條件、仍需消費鏈軸證明死路。指令與原始命中結果要記錄在可回查的位置（工作追蹤系統或設計文件）、後續任何人懷疑豁免過期時直接重跑核對——口頭結論「已確認無使用」沒有這個性質。

### 重啟條件綁可驗證觸發事件

豁免是暫態、必須聲明何時失效、且失效條件要可驗證。「未來再評估」這種開放式豁免、在「未來」與「永不」之間沒有可判定的邊界。

可靠的做法是把重啟條件綁在**可驗證的觸發事件**上、並附至少一則機械偵測指令：

```text
grep -rln "<DI 接線點或 provider 名稱>" <程式碼根目錄> | wc -l
# 計數由 0 變 >0、代表該表出現 production 寫入路徑、重啟條件成立
```

機械偵測條件的價值是把「是否該重啟」從記憶轉為可執行檢查：任何人（含未來的 AI 代理）重跑指令就得到是或否、免於回頭重建豁免當時的完整脈絡。搭配流程面的保險——讓「為該表接線」的變更在 review checklist 帶上「補契約文件」這一項——豁免就有了雙層失效偵測：機械指令抓狀態、review 流程抓變更。

## 判讀訊號

| 訊號                                            | 判讀重點                             | 對應動作                                          |
| ----------------------------------------------- | ------------------------------------ | ------------------------------------------------- |
| 時間欄位在讀取端出現異常年代（1970 或遙遠未來） | 單位語意未成文、多條寫入路徑各自表述 | 把單位寫進契約欄位語意表、收斂寫入路徑            |
| DDL 註解列的合法值與程式碼枚舉對不上            | 註解被當成契約載體                   | 三選一定權威來源：CHECK / lookup table / 契約文件 |
| 新成員問「這欄位為什麼這樣設計」查無答案        | 設計意圖只存在原作者記憶             | 補契約文件 A 區（欄位語意 + 不變式）              |
| 換 DB 評估時分不清哪些規格要重寫                | 邏輯契約與實作綁定混寫               | 依可攜性兩區重整、B 區標註引擎綁定                |
| 契約文件描述的行為在程式碼找不到寫入路徑        | dormant 表被強行補文件               | 三軸實查、符合即豁免並綁重啟條件                  |
| 文件更新頻率遠低於 schema 變更頻率              | 文件承載了本該寫成約束的內容         | 逐條檢查「能否寫成 CHECK」、能則改寫成約束        |

## 常見誤區

把 migration 腳本當成契約、是最常見的混淆。腳本記錄「做了什麼變更」、契約記錄「為何這樣設計、不變式是什麼」——兩者回答不同的問題。只有腳本的專案、schema 的每一步演進都可重放、但演進背後的設計意圖無從審計。

把 DDL 註解當契約載體、忽略註解沒有執法能力也沒有漂移偵測。註解適合當導覽提示、權威來源要落在 CHECK、lookup table 或契約文件三者之一。

為了完整感替小專案補契約文件、忽略兩旗標皆否時 DDL 註解已是合法終態。沒人維護的文件過期後比沒有文件更誤導。

為 dormant 表撰寫契約、忽略契約承載的是行為事實。表還沒有 production 寫入路徑時、文件只能複述 DDL、接線時還要全文重審——先豁免、綁好重啟條件、等行為出現再寫。

反過來的誤區同樣成立：把「能寫成 CHECK 的不變式」留在文件裡。文件會腐爛、DDL 會執法——能下沉到約束層的規則優先下沉、文件只留「為何選這個約束」的決策理由。

## 案例對照

| 案例                                                                                                                        | 契約視角的重點                                                                   |
| --------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| [1.7 訂單付款狀態欄位演進](/backend/01-database/schema-migration-rollout-evidence/)                                         | mapping table 這類狀態契約先進 artifact、validation query 才有判讀基準           |
| [3.C9 Queue 語意不匹配 cutover 反例](/backend/03-message-queue/cases/failure-queue-semantics-mismatch-cutover/)             | 語意契約缺席時、cutover 前後的行為差異無從驗證                                   |
| [GitHub 2018 Oct21 MySQL Topology Incident](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/) | 此類事故的修復依賴人工比對跨區資料；對帳鍵與欄位語意若有成文載體、比對成本可壓縮 |

## 案例回寫

語意載體議題可以用 [GitHub 2018 Oct21 MySQL Topology Incident](/backend/08-incident-response/cases/github/2018-oct21-mysql-topology-incident/) 做回寫練習。讀這個事件時、先看跨區資料分歧後的修復過程需要哪些人工比對、再回到本章檢查三件事：對帳鍵是否有成文載體、欄位語意是否收進 A 區欄位語意表、恢復模型是否寫明還原後如何驗證資料完整。

這個案例主要支撐「語意載體缺失使人工比對成本升高」類判讀、不支撐拓樸切換或 failover 調校類問題；若問題是切換決策與事故指揮、應轉到 [08 事故應變](/backend/08-incident-response/) 章節處理。

## 跨模組路由

1. 與 1.2 的交接：能寫成約束的規則回到 [Schema Design](/backend/01-database/schema-design/) 的結構層處理、契約文件只承載結構表達不了的語意。
2. 與 1.4 的交接：A 區錯誤語意契約是 [Repository Adapter](/backend/01-database/repository-adapter/) error translation 的規格來源。
3. 與 1.6 的交接：migration 治理旗標為要時、分段驗證流程落在 [資料庫轉換實作](/backend/01-database/database-migration-playbook/)。
4. 與 1.7 的交接：契約條目進入 production rollout 時、驗證證據落在 [Schema Migration Rollout 證據實作示範](/backend/01-database/schema-migration-rollout-evidence/)。
5. 與 1.8 的交接：A 區狀態責任分層與 [State Ownership](/backend/01-database/state-ownership-query-boundary/) 的 canonical / derived 分層對齊。
6. 與 6.10 的交接：契約作為可驗證 artifact 的一般框架、與 schema 演進的相容性驗證、見 [Contract Testing 與 Schema 演進](/backend/06-reliability/contract-testing/)。

## 下一步路由

- 平行：[1.2 Schema Design](/backend/01-database/schema-design/)、[1.8 State Ownership](/backend/01-database/state-ownership-query-boundary/)
- 下游：[1.6 Database Migration Playbook](/backend/01-database/database-migration-playbook/)、[1.7 Schema Migration Rollout Evidence](/backend/01-database/schema-migration-rollout-evidence/)
- 知識卡：[contract](/backend/knowledge-cards/contract/)、[source of truth](/backend/knowledge-cards/source-of-truth/)、[schema migration](/backend/knowledge-cards/schema-migration/)、[Expand / Contract](/backend/knowledge-cards/expand-contract/)
