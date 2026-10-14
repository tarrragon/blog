---
title: "11.16 面向終端使用者的錯誤碼與請求編號：錯誤畫面的欄位、請求編號的產生與傳遞、錯誤碼對照表、客服收件欄位、客服查詢工具的權限與 log 保留期"
date: 2026-10-14
description: "使用者經由客服回報錯誤、再由工程查到那一次請求，系統在每一段要提供什麼：錯誤碼與請求編號各自交給誰用、請求編號為什麼要隨機以及電話上怎麼唸，入口以 Nginx 產生編號並傳進後端與 log、入口自己的 502 與前端怎麼讀到編號（實測），錯誤碼對照表怎麼跟著程式維護，客服查詢工具的唯讀、遮罩與稽核，以及 log 保留期由回報到查證的時間決定"
weight: 16
tags: ["backend", "api-design", "error-contract", "customer-support"]
---

這一篇處理終端使用者遇到錯誤之後，從他看到的畫面、到客服收件、再到工程查到那一次請求，系統在每一段要提供什麼。API 呼叫方（另一個系統）收到錯誤之後怎麼回報給 API 提供者，是同一套機制在系統之間的版本，見 [錯誤回報的回饋迴路：request-id、trace 與呈現回報分工](/backend/11-api-design/error-feedback-loop/)；錯誤要怎麼分類、錯誤回應的格式怎麼定，見 [11.4 錯誤模型設計](/backend/11-api-design/error-model-design/)。客服與工程之間的流程（什麼條件轉給值班、工程怎麼回覆）在 [8.24 客服回報的處理](/backend/08-incident-response/support-escalation-and-engineering-reply/)，這一篇寫那個流程用到的系統設計。

這一篇的例子是一個短網址服務：入口 Nginx 把請求轉給後端程式，登入的使用者建立短網址、看點擊統計，訪客點短網址時由服務轉址。

## 錯誤碼與請求編號

使用者回報錯誤時，工程要從那一句「我剛剛建立短網址失敗」找到兩件事：這是哪一種錯誤，以及是哪一次請求。這兩件事由錯誤畫面上的兩個欄位分別提供。

**錯誤碼**代表一類錯誤，同一種錯誤每次出現都一樣，例如 `LINK_EXPIRED`（短網址已過期）、`QUOTA_EXCEEDED`（本月建立額度用完）。客服拿它去查錯誤碼對照表，就知道這一類錯誤的意思與答覆方式，不必知道是哪一次請求。畫面上的錯誤碼可以直接沿用錯誤回應裡給程式判讀的 code 欄位（見 [11.4 錯誤模型設計](/backend/11-api-design/error-model-design/)），客服、工程與程式用同一個字串，對照表不必另外維護一份對應；API 的 code 分得比客服需要的細時，由前端對應成較粗的類別再顯示。不論哪一種，對照表的鍵是畫面上顯示的那個字串，而畫面上只放錯誤的類別，不放服務名稱或內部細節。

**請求編號**代表單一次請求，每次都不同，例如 `9c8561d5272320ba8aafd57145eb9894`。它是那一次請求的 [Request ID](/backend/knowledge-cards/request-id/)，工程拿它去 log 與 trace 裡找到那一次請求的完整紀錄。畫面上的欄位名稱也寫「請求編號」，與系統內部用同一個名字，客服與工程說的是同一件事。

兩者缺一個，查證就少一段。只有錯誤碼，客服知道是額度用完，而使用者說「我明明還有額度」時，工程查不出那一次請求實際讀到的額度是多少；只有請求編號，客服手上是一串看不出意思的字元，每一則回報都要轉給工程才知道是什麼錯誤。Microsoft Entra 的登入錯誤頁同時給兩者：畫面上有 `AADSTS` 開頭的錯誤碼，展開的疑難排解資訊列出 Request Id、Correlation Id 與時間戳記，管理員在登入紀錄裡以這些值找到使用者遇到的那一次失敗。系統之間的 API 也是同一個做法：Stripe 在每個回應的 `Request-Id` header 帶一個 `req_` 開頭的編號，並請使用者聯絡客服時附上它。

## 錯誤畫面上的欄位

錯誤畫面要同時給使用者與客服用，所以畫面上放四個欄位：

- **給使用者看的訊息**：發生了什麼、他現在能做什麼，不含內部的服務名稱、資料表或堆疊追蹤（stack trace）。錯誤訊息透露內部結構會成為攻擊者的偵察材料，見 [OWASP error handling：錯誤訊息是攻擊者的偵察面](/backend/11-api-design/cases/errorchain-owasp-error-handling/)。
- **錯誤碼**。
- **請求編號**，旁邊放一個複製按鈕。
- **發生時間**，標明時區。

訊息與錯誤碼對應的是錯誤的類別，可以在程式裡逐一寫好；請求編號與時間是每一次請求才有的值，要由產生錯誤的那一段程式帶到畫面上。

請求編號的長度要和回報的管道一起考慮。網頁與 App 上，使用者按複製再貼進客服表單，32 個字元不成問題；電話客服要使用者唸出來，32 個十六進位字元太長。做法之一是畫面顯示完整的編號、電話上只請使用者唸前 8 碼，工程以前 8 碼加上帳號與時間範圍篩選 log。8 碼十六進位有 16⁸ 種、約 43 億種組合；工程篩選的那個帳號與時間範圍裡共有 n 次請求時，除了使用者要找的那一次，其餘請求之中至少有一次的前 8 碼也相同的機率約為 n ÷ 43 億，一小時一千次請求時約是四百萬分之一，帳號的請求量大時把 n 換成自己的數字重算。

請求編號要是隨機產生的值，不能由帳號編號、遞增序號或時間組成。由帳號編號組成的編號讓別人從編號推出帳號；遞增序號讓別人推算服務的請求量，也讓別人猜出其他使用者的編號；以時間開頭的編號前幾碼是時間戳記，UUIDv7 的前 8 碼約每 65 秒才變一次、ULID 的前 8 碼約每秒變一次，同一段時間內的請求前 8 碼相同，電話上只唸前 8 碼就分不出是哪一次請求。

## 請求編號的產生與傳遞：Nginx 入口、後端程式、前端與 App

請求編號要在 log 裡查得到，前提是同一個值同時出現在三個地方：回給使用者的錯誤畫面、入口的 access log，以及後端程式處理這個請求時寫的每一行 log。最直接的做法是由請求最先抵達的入口產生請求編號，再把它傳下去。

Nginx 從 1.11.0 起提供 `$request_id` 變數，每個請求以 16 個隨機位元組產生，寫成 32 個十六進位字元。以下設定讓 Nginx 把它寫進 access log、加在回應的 header 上，並以 `X-Request-Id` header 傳給後端程式：

```nginx
# 以下兩行寫在 http 區塊（server 之外）
log_format withid '$remote_addr [$time_iso8601] "$request" $status rid=$request_id';
access_log /var/log/nginx/access.log withid;

server {
    listen 80;
    # 每一個回應（包括錯誤回應）都帶上同一個編號
    add_header X-Request-Id $request_id always;

    location / {
        # 把編號傳給後端；後端從這個 header 讀出編號寫進自己的 log
        proxy_set_header X-Request-Id $request_id;
        # app:8080 換成自己後端程式的位址
        proxy_pass http://app:8080;
    }
}
```

這段設定要拆開併進既有的設定檔，各行的位置與作用：

- `log_format` 只能寫在 `http` 區塊，寫進 `server` 時 `nginx -t` 會回報 `"log_format" directive is not allowed here`。官方映像與多數套件的 `conf.d/*.conf` 是在 `http` 區塊裡被引入的，所以寫在那些檔案的最外層就是 `http` 層。名字 `withid` 與欄位標記 `rid=` 都是自取的，`access_log` 那一行以同一個名字引用它；log 檔的路徑換成自己主機上的位置。
- 套件預設的 `nginx.conf` 在 `http` 層已經有一行 `access_log … main;`。這時把那一行的格式名改成 `withid`，或在原本的 `main` 格式後面加上 `rid=$request_id`；另加一行 `access_log` 的話，每個請求會以兩種格式各寫一次。
- `add_header` 併進既有的 `server`，`proxy_set_header` 併進每一個有 `proxy_pass` 的 `location`。這兩個指令都只在當層沒有同名指令時才繼承上一層的設定，所以某個 `location` 自己寫了其他 `add_header` 或 `proxy_set_header` 時，要在那個 `location` 裡再寫一次這一行。
- `add_header` 後面的 `always` 讓 Nginx 在 4xx 與 5xx 的回應上也加這個 header。少了它，Nginx 只在 200、201、204、206、301、302、303、304、307、308 這幾種回應加 header，而使用者回報的正好是錯誤回應。

以 Nginx 1.27.5 實測這段設定：一次請求的回應 header、後端收到的 `X-Request-Id` 與 access log 的 `rid=` 欄位是同一個值。用戶端自己在請求裡帶了 `X-Request-Id` 時，Nginx 產生 `$request_id` 不讀這個 header，仍然產生新的值，後端收到的是 Nginx 產生的那一個；入口因此不必信任外部送進來的編號，與 W3C Trace Context 允許在信任邊界重新開始 trace 是同一個考量（見 [錯誤回報的回饋迴路：request-id、trace 與呈現回報分工](/backend/11-api-design/error-feedback-loop/#定位鉤子request-id-與-trace-的契約) 的〈定位鉤子：request-id 與 trace 的契約〉）。

Nginx 前面還有 CDN 或雲端負載平衡器時，連不上 Nginx 的錯誤頁由那一層產生，不會有 `$request_id`。這時那一層的錯誤頁要顯示它自己產生的請求編號，Nginx 的 access log 也要記下那一層傳來的編號 header，兩個編號才接得起來。

後端程式要做兩件事。第一件是從 `X-Request-Id` header 讀出編號，放進這個請求的 log 欄位（多數 logging 函式庫稱為 context 或 MDC），讓這個請求寫的每一行 log 都帶著它；log 欄位怎麼命名、跨服務怎麼保持一致，見 [4.1 log schema 與搜尋規劃](/backend/04-observability/log-schema/)。第二件是回應錯誤時把它放進錯誤回應的 body，讓前端顯示在畫面上。

錯誤回應採用 [RFC 9457](/backend/knowledge-cards/problem-details/)（HTTP API 錯誤回應的 Problem Details 格式）時，編號可以放在 `instance` 成員，它要寫成 URI，RFC 建議帶完整路徑，例如 `/requests/9c8561d5272320ba8aafd57145eb9894`；也可以放在自訂的欄位。

後端程式不能用自己產生的編號取代入口的編號：錯誤畫面與 access log 上寫的是入口的編號，後端的 log 只寫自己的編號時，拿使用者給的編號就找不到後端那一段紀錄。後端需要自己的編號時，兩個一起寫進 log。請求在後端又呼叫其他服務時，跨服務的關聯改由 trace 承擔，log 同時寫入 [trace-id](/backend/knowledge-cards/trace-id/)，工程從請求編號找到 log，再從 trace-id 找到整條呼叫鏈。

入口自己產生的錯誤也要帶編號。後端程式停掉時，Nginx 回 502，錯誤頁是 Nginx 產生的，不經過後端；以 `error_page` 把這些錯誤導到一個以 `return` 回應的具名 location，錯誤頁就能顯示同一個編號：

```nginx
location / {
    proxy_set_header X-Request-Id $request_id;
    proxy_pass http://app:8080;
    # 後端連不上或逾時時，改由下面的 location 產生錯誤頁
    error_page 502 503 504 = @upstream_error;
}

# @upstream_error 是自取的名字
location @upstream_error {
    default_type text/plain;
    return 502 "服務暫時無法使用。錯誤碼 UPSTREAM_UNAVAILABLE，請求編號 $request_id\n";
}
```

`error_page` 寫了 `=` 而沒有接回應碼時，Nginx 回給用戶端的回應碼改用 `@upstream_error` 回的值，這裡一律是 502；要保留 503 與 504 的區分，就為它們各寫一個具名 location。錯誤頁要用 HTML 時，把 `default_type` 改成 `text/html`，內文換成 HTML。這裡的 `UPSTREAM_UNAVAILABLE` 也會顯示在使用者畫面上，同樣要在錯誤碼對照表上有一列。實測時把 `proxy_pass` 指向一個沒有程式在聽的埠，回應是 502，內文的請求編號、header 的 `X-Request-Id` 與 access log 的 `rid=` 三者相同。

前端或 App 自己畫錯誤畫面時，請求編號有兩個來源：後端錯誤回應 body 裡的欄位，以及每一個回應都帶的 `X-Request-Id` header。入口自己回的 502 是上面那段純文字，不是後端的錯誤格式，前端從 body 解析不出欄位，這時改讀 header。網頁前端與 API 不同源時，瀏覽器只讓前端程式讀到 CORS 公開的 header，入口要在同一層再加一行 `add_header Access-Control-Expose-Headers X-Request-Id always;`；實測 502 回應同時帶著這兩個 header。

行動 App 的錯誤可能根本沒有到達伺服器（沒有網路、DNS 解析失敗、連線逾時），這時沒有入口產生的編號。App 可以在每次送出請求時自己產生一個編號，在畫面上顯示 App 自己的錯誤碼（例如 `NETWORK_UNREACHABLE`）與這個編號，並把它與錯誤一起寫進 App 自己送出的 log 或當機回報；請求沒有到達伺服器時，工程只能在那裡查到它。這個編號要放在另一個 header 送出，例如 `X-Client-Request-Id`，因為入口會以 `$request_id` 覆寫 `X-Request-Id`。請求到達了伺服器、只是回應沒有回到 App 時，要讓工程在伺服器的 access log 查得到這個編號，把前面那一行 `log_format withid` 換成下面這一行（同名的 `log_format` 只能定義一次，另加一行同名的，`nginx -t` 會回報 `duplicate "log_format" name`）：

```nginx
# 取代前面的 log_format withid：在 rid= 之後多記 App 送來的編號；沒有帶這個 header 的請求記成 -
log_format withid '$remote_addr [$time_iso8601] "$request" $status rid=$request_id crid=$http_x_client_request_id';
```

`$http_x_client_request_id` 是 Nginx 讀請求 header 的變數，名字由 `$http_` 加上 header 名稱的小寫、連字號換成底線組成。以 Nginx 1.27.5 實測，帶了 `X-Client-Request-Id: app-7f3a9c` 的請求在 access log 記成 `crid=app-7f3a9c`，沒帶的記成 `crid=-`；Nginx 預設把請求裡的其他 header 原樣轉給後端（名稱含底線的 header 預設會被丟棄），後端不必另外設定就收得到它。App 若已經依 [4.24 Client-to-Server 端到端觀測串接](/backend/04-observability/client-server-trace-integration/) 送出 `traceparent`，可以不另外產生編號，直接以其中的 trace-id 當作 App 端的編號，用戶端與伺服器端的紀錄由同一個 trace 串起來。

## 錯誤碼對照表

錯誤碼對照表讓客服不經過工程就答覆使用者。每一個會顯示在使用者畫面上的錯誤碼佔一列，欄位如下：

| 欄位           | 內容                                   | 短網址服務的例子（`LINK_EXPIRED`）                           |
| -------------- | -------------------------------------- | ------------------------------------------------------------ |
| 錯誤碼         | 畫面上顯示的字串                       | `LINK_EXPIRED`                                               |
| 意思           | 用客服聽得懂的話說明                   | 這個短網址超過有效期限，服務已停止轉址                       |
| 使用者能做的事 | 使用者自己可以採取的動作，沒有就寫沒有 | 擁有者登入後可以延長期限；訪客請聯絡分享網址的人             |
| 客服的答覆     | 客服可以直接用的一段話                 | 「這個短網址已在 ○ 月 ○ 日到期，擁有者可在管理頁延長期限。」 |
| 轉給工程的條件 | 什麼情形下這個錯誤碼不是使用者端的狀況 | 擁有者表示期限未到卻收到這個錯誤                             |
| 處理時查的工具 | 客服查證時要開的頁面                   | 客服查詢工具的短碼頁，看到期日                               |
| 負責的團隊     | 這一列由誰維護                         | 短網址服務團隊                                               |

同一個錯誤碼多數時候代表使用者端的狀況，少數時候是程式錯誤：`LINK_EXPIRED` 出現在一個期限未到的短網址上，代表到期判斷寫錯了。只寫錯誤說明的文件分不出這兩種情形，客服只能每一則都照「已過期」答覆；對照表多了「轉給工程的條件」這一欄，客服才分得出來，使用者端的狀況自己答覆，程式錯誤轉給工程。

錯誤碼與它的使用者訊息一旦出現在使用者畫面上，就是對客服與使用者的承諾：重新命名一個錯誤碼，客服的對照表與知識文章就對不上，使用者手上的舊截圖也查不到。錯誤碼的變更紀律因此與 API 欄位相同，見 [11.6 向後相容的變更紀律](/backend/11-api-design/backward-compatibility-discipline/)；命名用可讀的字串而不是連續數字，理由見 [11.4 錯誤模型設計](/backend/11-api-design/error-model-design/#常見設計錯誤) 的〈常見設計錯誤〉。

對照表最常見的失效是程式新增了錯誤碼而對照表沒有跟上，客服遇到一個查不到的錯誤碼，只能把整張單轉給工程。一種做法是讓對照表從程式裡的錯誤定義產生：每一個錯誤碼在定義的地方同時寫上客服用的欄位，文件由建置流程從那裡產生，CI（每次提交時自動執行的建置與檢查）在客服欄位空白時讓建置失敗。新增錯誤碼的那一次變更因此必須同時寫好客服的答覆。不從程式產生時，至少把負責的團隊寫在每一列上，並在每週營運會議裡比對客服單出現過的錯誤碼與對照表的列（見 [4.29 值班的例行檢查](/backend/04-observability/on-call-routine-checks/#每週營運會議讀的訊號) 的〈每週營運會議讀的訊號〉）。

## 客服收件的欄位

客服收到回報時要收齊的欄位，每一個都對應工程查證的一個步驟：

- **帳號**（或使用者自己看得到的使用者編號）：沒有請求編號時，以帳號篩選 log；也用來查這個帳號的資料狀態。
- **發生時間與時區**：縮小 log 的查詢範圍。使用者說的「下午三點」沒有時區時，工程可能在差八小時的位置找。
- **錯誤碼**：查對照表，客服自己就可能答覆。
- **請求編號**：直接找到那一次請求。
- **裝置、作業系統與 App 版本或瀏覽器**：判斷是否只發生在某個版本；只發生在低於最低支援版本的 App 上時，處理方式是請使用者更新（見 [Minimum Supported Version](/backend/knowledge-cards/minimum-supported-version/)）。
- **操作步驟與螢幕截圖**：重現問題，也從截圖補回使用者沒抄下的錯誤碼與請求編號。

使用者沒有抄下請求編號時，工程以帳號加上前後幾分鐘的時間範圍查 log，再以錯誤碼與請求的路徑縮小到那一次請求。這條退路成立的前提是 log 有帳號與錯誤碼欄位可以篩選，而帳號屬於個人資料，寫進 log 時要依 [PII](/backend/knowledge-cards/pii/) 的規則處理：寫內部的使用者編號，不寫電子郵件或姓名。

## 客服查詢工具的權限

客服查詢工具讓客服以帳號或短碼查到資料的狀態，取代請工程查資料庫。工具的設計重點在客服看得到什麼、以及每一次查詢留下什麼紀錄：

- **只讀**：工具只顯示狀態，延長期限、退款、解除停用這類會改資料的動作另外走有核准流程的後台。
- **欄位層級的遮罩**：客服看得到短碼的狀態、原始網址、到期日、建立時間與檢舉紀錄，以及帳號的方案與本月剩餘額度；電子郵件、姓名這類個人資料不顯示，付款資訊只顯示卡號末四碼。遮罩的做法見 [Data Masking](/backend/knowledge-cards/data-masking/)。
- **查詢要附單號**：客服以帳號查詢時要填這次查詢對應的客服單號，工具只在單子存在時顯示資料。這讓每一次查詢都有理由，也讓查詢量異常時看得出來。
- **每一次查詢都寫進稽核紀錄**：誰、什麼時間、以哪一張單、查了哪個帳號（見 [Audit Log](/backend/knowledge-cards/audit-log/)）。客服帳號被盜用時，攻擊者用的就是這個工具，稽核紀錄是事後查出影響範圍的依據；客服支援系統被入侵而外洩客戶資料的實例見 [Okta 支援系統事件](/backend/07-security-data-protection/cases/okta-support-system-incident-2023/)。

客服不直接查 log。log 裡有其他使用者的資料與內部細節，而且 log 系統的權限多半以整個資料集為單位，給了客服就等於給了全部；客服需要的狀態，由查詢工具挑出來顯示。權限的整體設計原則見 [Least Privilege](/backend/knowledge-cards/least-privilege/)。

## log 保留期與客服處理時間

請求編號在 log 裡查得到的前提，是那一行 log 在工程查詢時還在，而且仍是逐筆的完整紀錄。這一節說的客服處理時間，指從使用者遇到錯誤到工程以請求編號查 log 的整段時間，由幾段相加：使用者隔幾天才回報、客服單在佇列裡等、客服處理後轉給工程、工程排到這張單並開始查。開單在上班時間處理的回報，這段時間常以天甚至週計算。[Retention（保留期）](/backend/knowledge-cards/retention/) 比這段時間短的 log，工程拿著正確的請求編號也查不到，看起來像使用者抄錯了編號。

所以可以逐筆以請求編號查詢的那一層 log（完整粒度、沒有聚合），保留期要以這段時間的上限決定，再加上餘裕。例如使用者一週後才回報、客服兩天內轉單（遇到週末約四天）、工程在期限內第一次回覆之後，實際查 log 可能再隔兩週，加起來約二十五天，再加上餘裕，請求層級的 log 保留三十天；這幾段時間換成自己服務的數字重算。

保留期越長，儲存成本與個人資料外洩的影響範圍越大，所以常見的做法是分層：請求層級的 log 以完整粒度保留到涵蓋客服處理時間為止，其中的個人資料欄位遮罩或只存內部編號，更長期的統計改用聚合過的指標。[4.7 Cardinality 治理與成本邊界](/backend/04-observability/cardinality-cost-governance/#控制面與保留階梯) 的保留階梯以最近 7 天的熱層保留完整粒度、7 到 30 天聚合為例，用在請求 log 時要把完整粒度那一層延長到客服處理時間；營運 log（operational log）的保留期與它的漂移見 [4.12 Audit Log 邊界與 PII 治理](/backend/04-observability/audit-log-governance/#retention-與保留策略漂移) 的〈Retention 與保留策略漂移〉。

## 延伸閱讀：客服流程、系統之間的錯誤回報與錯誤分類

- 客服當場答覆時用的資訊、轉給值班的條件、工程查證後給客服的回覆：[8.24 客服回報的處理](/backend/08-incident-response/support-escalation-and-engineering-reply/)
- API 呼叫方與提供者之間以 request-id 與 trace 回報錯誤、錯誤內容分成給使用者的呈現與給工程的回報：[錯誤回報的回饋迴路：request-id、trace 與呈現回報分工](/backend/11-api-design/error-feedback-loop/)
- 錯誤分成可重試與終態、錯誤回應的格式與演化條款：[11.4 錯誤模型設計](/backend/11-api-design/error-model-design/)
- API、非同步工作與外部呼叫的錯誤要帶哪些診斷欄位：[4.19 Debuggability by Design](/backend/04-observability/debuggability-by-design/)
