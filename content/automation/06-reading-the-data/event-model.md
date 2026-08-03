---
title: "事件模型與停留時間"
date: 2026-08-03
description: "每次瀏覽只記一列時看不出讀者停留多久、有沒有真的在讀，補上離開事件並理解那個秒數量到的是什麼"
weight: 2
tags: ["automation", "beacon", "analytics", "visibilitychange", "sendbeacon", "data-model"]
---

事件模型決定一次瀏覽在資料裡留下幾列、每列各自承載什麼。模組二的模型是一次瀏覽一列，在頁面載入時寫下——這個模型能回答「某頁被打開幾次」，回答不了「打開之後發生了什麼」。頁面被打開一秒就關掉，跟被讀了三分鐘、中途捲動了十次，在資料上完全相同。

補上這個能力需要第二則事件，而第二則事件的設計比第一則複雜：載入的時機明確且必定發生，離開的時機則有多種可能，且不保證每次都能送出。

## 進入與離開拆成兩則事件

模型是每次瀏覽產生兩列：**進入事件在頁面載入時送出，離開事件在頁面不再可見時送出**，兩列靠 session 識別碼與路徑配對起來。

```javascript
var base = { path: location.pathname, lang: navigator.language, dev: deviceType(),
             vid: visitorId, sid: sessionId };

// 進入：載入時立刻送，帶來源網址
send(Object.assign({ t: "view", ref: document.referrer || "" }, base));

// 離開：帶停留秒數與是否互動過
var arrivedAt = Date.now();
var interacted = false;
var leaveSent = false;

["scroll", "pointerdown", "keydown"].forEach(function (evt) {
  addEventListener(evt, function () { interacted = true; }, { once: true, passive: true });
});

function sendLeave() {
  if (leaveSent) return;
  leaveSent = true;
  send(Object.assign({
    t: "leave",
    dur: Math.round((Date.now() - arrivedAt) / 1000),
    act: interacted ? 1 : 0
  }, base));
}
```

**拆成兩列而不是合併成一列，是為了讓兩件事各自失敗。** 合併的設計會是「等到離開時才送一列，裡面同時放路徑與停留時間」——它看起來省一半的列數，代價是離開事件送不出去時，這次瀏覽在資料裡完全不存在。而離開事件送不出去是會實際發生的：行動裝置被系統回收記憶體、瀏覽器被強制關閉、網路在切換基地台時中斷。拆開之後，最壞情況只損失品質欄位，計數的基準線不受影響。

這個取捨的另一面是列數翻倍，對免費配額與試算表容量的影響見[模組三](/automation/03-sheet-as-database/data-model-and-capacity/)。個人網站的量體下這個代價可以接受；量體大到需要壓縮時，正確的方向是在接收端合併而不是在前端少送——前端少送會讓資料從一開始就不存在。

## 用 visibilitychange 觸發離開事件

離開事件的觸發時機有三個候選，可靠度差距很大。

**`beforeunload` 不適用。** 它在行動版 Safari 幾乎不觸發，而且註冊這個監聽器會讓頁面失去進入 bfcache（返回時的快取還原）的資格——為了統計而拖慢讀者的返回操作，取捨方向是錯的。

**`pagehide` 涵蓋頁面卸載與進入快取兩種情況**，比 `beforeunload` 可靠，但漏掉「切換到別的分頁或別的 app」這個最常見的離開方式。

**`visibilitychange` 進入 `hidden` 狀態涵蓋範圍最廣**：切換分頁、切換 app、鎖定螢幕、關閉頁面都會走到。實務上兩者都註冊、靠旗標防止重複送出：

```javascript
addEventListener("visibilitychange", function () {
  if (document.visibilityState === "hidden") sendLeave();
});
addEventListener("pagehide", sendLeave);
```

`sendLeave` 開頭那個 `leaveSent` 旗標在這裡是必要的而非防禦性的——一次真實的離開通常會同時觸發這兩個事件。

送出方式仍然是 `navigator.sendBeacon`（見[beacon 知識卡](/automation/knowledge-cards/beacon/)），它的設計目標正是這個場景：頁面正在關閉時，一般的請求會隨著頁面銷毀而被取消，`sendBeacon` 交給瀏覽器在背景送完。

## 停留秒數量到的是可見時長

這個欄位的語意需要精確界定，否則會被當成閱讀時長使用而得出錯誤結論。**它量的是「頁面從載入到不再可見之間經過的時間」**，這與讀者實際花在這篇文章上的時間有系統性的差距。

差距來自兩個方向。**切換到別的分頁去查資料再切回來，會被切成多段**——第一段在切走時就結束了，切回來不會產生新的進入事件（頁面沒有重新載入），所以回來之後的閱讀時間完全沒有被記錄。反過來，**開著分頁去做別的事**，如果沒有切換到其他分頁（例如直接離開電腦），這段時間會全部算進停留秒數。

站內導覽時還有一個可以驗證的現象：離開事件的時間戳與下一頁的進入事件時間戳幾乎相同，因為舊頁進入 `hidden` 與新頁開始載入是同一個動作的兩面。這讓連續的閱讀路徑可以在資料上被重建，也讓「這一列的秒數確實對應那一頁」得到交叉驗證。

實務上這個欄位適合用來分辨量級而非精確比較：三秒與三十秒的差別是真實的訊號，三十秒與三十五秒的差別不是。

## 互動旗標

`act` 記錄的是「這次瀏覽期間有沒有發生過捲動、點擊或按鍵」。它用 `{ once: true }` 註冊，第一次觸發後就移除監聽器——需要的資訊只是「有沒有發生過」，不是次數，持續監聽只會增加沒有用途的執行成本。

`passive: true` 這個選項對捲動事件是必要的：它向瀏覽器宣告這個監聽器不會取消預設行為，讓捲動不必等待 JS 執行完成。統計程式碼不該是頁面捲動卡頓的來源。

這個旗標的判讀價值在於它與停留秒數的組合。停留六秒且沒有任何互動，與停留六秒且捲動過，是兩種完全不同的情況——前者是頁面被打開然後放著，後者是有人真的在看。單獨看秒數分不出這兩者。

## 資料模型變更會讓既有的報表公式換語意

這個變更有一個容易被漏掉的下游影響：**在單事件模型下寫的統計公式，在雙事件模型下仍然合法執行，但回答的已經不是同一個問題**。

具體的例子是判斷「這次 session 只看了一頁」。單事件模型下，這等價於「同一個 session 識別碼只出現一次」：

```text
COUNTIFS(session欄, 當列session) = 1
```

改成雙事件之後，每次瀏覽至少產生兩列，這個條件從此永遠不成立。公式沒有報錯、沒有回傳錯誤值，只是那個分類的計數變成恆為零——而零看起來就像「沒有這種流量」。正確的寫法要把事件型別納入條件：

```text
COUNTIFS(session欄, 當列session, 事件欄, "view") = 1
```

同一個影響也及於[模組四的每日彙總](/automation/04-triggers-automation/time-driven-aggregation/)：那段 group by 對每一列加一，在單事件模型下等於數瀏覽次數，改成雙事件之後會把每次瀏覽數兩遍。修法是在迴圈裡先篩掉非進入事件，模組四的程式碼旁已標明這個前提。

**因此資料模型的變更範圍必須包含下游的分析邏輯**，把公式與彙總程式的重算當成同一次變更的一部分，而不是之後再說。延後處理會失去對照：之後回頭看時，看到的數字已經是新邏輯算出來的，沒有東西可以比對。這類失效的完整判讀方法見[假故障與靜默失效的診斷](/automation/06-reading-the-data/diagnosing-silent-failures/)，抽象層的原則見 [#250 資料多出一種形狀時，既有分析邏輯靜默換語意](/report/new-data-shape-silently-changes-analysis/)。

## 下一步

事件模型完成後，資料裡有了停留時間與互動訊號——這兩個欄位除了描述閱讀行為，也是分辨真人與機器最難偽裝的依據。怎麼組合它們與其他訊號，見[辨識自動化流量](/automation/06-reading-the-data/automated-traffic/)。
