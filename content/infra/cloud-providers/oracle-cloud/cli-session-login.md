---
title: "從本機用 OCI CLI 操作 Oracle Cloud：session token 登入、時效與 API 簽章金鑰"
date: 2026-10-24
description: "OCI CLI 的兩種身分驗證方式——瀏覽器登入換來的 session token 與上傳公鑰的 API 簽章金鑰——各自把什麼存在本機、有效多久、外洩時的影響範圍，以及登入時的互動提示與錯誤訊息怎麼讀"
weight: 3
tags: ["infra", "cloud-providers", "oracle-cloud", "oci", "cli", "authentication"]
---

這篇整理在 macOS 上安裝 OCI CLI 之後，讓它取得操作 tenancy（Oracle Cloud 的帳號）的身分的兩種做法。範圍從 `oci` 指令裝好開始，到第一條查詢指令回傳資料為止；macOS 上的安裝是 `brew install oci-cli`，裝好後 `oci --version` 印出版本號，Linux 與 Windows 的安裝方式見官方〈Installing the CLI〉。不想在本機安裝的話，主控台頂端列的 Cloud Shell 是一個已經裝好 CLI、以目前登入身分驗證好的瀏覽器終端機，本篇的登入步驟在那裡都不需要。tenancy、home region 與主控台登入欄位見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)。實測環境是 Homebrew 安裝的 OCI CLI 3.95.1，日期 2026-10-24。

## CLI 的兩種身分驗證：session token 與 API 簽章金鑰

OCI 的 API 不收帳號密碼。CLI 送出的每一個請求都用一把私鑰簽章，OCI 用對應的公鑰驗證簽章、再查這把公鑰屬於哪個使用者，以那個使用者的權限執行請求。兩種做法的差別在這對金鑰從哪裡來、公鑰怎麼讓 OCI 認得：

- **Session token**：CLI 在本機產生一對臨時金鑰，開瀏覽器讓使用者登入主控台；登入成功後 OCI 簽發一個綁定這把臨時公鑰的 token，token 過期之後這對金鑰就沒有用了。
- **API 簽章金鑰**：使用者在主控台把一把公鑰登記到自己的帳號下，之後持有對應私鑰的程式都能以這個使用者的身分呼叫 API，直到公鑰被刪除為止。

兩者在本機都會留下一個私鑰檔，差別在私鑰檔外洩之後能用多久。Session token 的私鑰在 token 過期後失效；API 簽章金鑰的私鑰在使用者到主控台刪掉公鑰之前一直有效。實驗與互動式操作用 session token，私鑰外洩之後可被冒用的時間最長到登入後 24 小時（見〈Session token 的時效與 refresh〉）；排程腳本、CI，以及經由 SSH 連進去、沒有瀏覽器可開的遠端機器，這類沒有人能開瀏覽器登入的場合才需要 API 簽章金鑰。

## 用瀏覽器登入換 session token

```bash
oci session authenticate --region ap-batam-1 --profile-name DEFAULT
```

- `--region`：填 tenancy 的 home region 的識別碼，這次實測的 home region 是 `ap-batam-1`，換成自己的。CLI 用它決定開哪一區的登入頁、並寫進設定檔當成之後指令的預設區域；試用與 Free Tier 的 tenancy 只訂閱 home region 一個區域，填它就對。識別碼與主控台上的顯示名稱（例如「Indonesia North (Batam)」）是兩種寫法，對照列在 Governance & Administration → Account Management → Region Management 頁；不給這個選項時，CLI 也會列出全部區域的識別碼讓使用者輸入編號。
- `--profile-name`：設定檔 `~/.oci/config` 裡這一組身分的名稱。`DEFAULT` 是 CLI 在指令沒有指定 `--profile` 時使用的那一組；同一台機器要切換多個 tenancy 時，每個 tenancy 用一個不同的 profile 名稱。

實測 Homebrew 版的 CLI 跑在 Python 3.15 上時，這條指令與之後每條指令的開頭都會印一行 `SyntaxWarning`，來源是 CLI 自己的程式碼裡的正規表示式字串，不影響結果。要讓輸出乾淨，在指令前面加上 `PYTHONWARNINGS=ignore`（例如 `PYTHONWARNINGS=ignore oci session validate`）只對那一條生效；改用 `export PYTHONWARNINGS=ignore` 的話，整個 shell 裡所有 Python 程式的警告都會被關掉。

登入過程中 CLI 會問兩個問題：區域與 profile 名稱，兩個都給在選項裡就不必互動輸入。這一點在 CLI 不是跑在互動式終端機裡時有差別——例如透過另一個程式代為執行、標準輸入沒有接到鍵盤——CLI 讀不到輸入，印出 `Abort` 後結束。實測少給 `--region` 時就是在區域清單之後直接 `Abort`。

CLI 接著開瀏覽器到登入頁，並在本機的 `localhost:8181` 等登入結果。瀏覽器的登入頁跟主控台是同一個，先填租用戶，頁面要求選 identity domain 時選 `Default`，再填使用者名稱與密碼，各欄的填法見 [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/) 的〈主控台登入〉。登入成功後瀏覽器把 token 送回 `localhost:8181`，終端機印出 `Completed browser authentication process!` 與 `Config written to: /Users/<user>/.oci/config`。瀏覽器頁面不小心關掉時，終端機上印著同一個登入網址，貼回瀏覽器就能繼續；網址裡帶著這次產生的臨時公鑰，所以只對正在等待的這一次登入有效。

設定檔裡的這一組長這樣（值是佔位的）：

```ini
[DEFAULT]
fingerprint=<臨時公鑰的指紋>
key_file=/Users/<user>/.oci/sessions/DEFAULT/oci_api_key.pem
tenancy=<tenancy 的 OCID>
region=<home region 的識別碼>
security_token_file=/Users/<user>/.oci/sessions/DEFAULT/token
```

`tenancy` 是 tenancy 的 OCID：OCI 給每一個資源（tenancy、compartment、VCN、主機）一個以 `ocid1.<資源類型>.` 開頭的唯一識別碼，叫 OCID（Oracle Cloud ID），CLI 與 API 用它指定要操作哪一個資源，各資源的詳細頁上都有一個可以複製的 OCID 欄位。`key_file` 是 CLI 產生的臨時私鑰，`security_token_file` 是 OCI 簽發的 token，兩個檔都在 `~/.oci/sessions/<profile 名稱>/` 底下。

不再使用時跑 `oci session terminate --profile <profile 名稱>`，CLI 會從設定檔移除這一組並刪掉它參照的金鑰與 token 檔。這個動作只清本機，OCI 那一端不會撤銷已經簽發的 token，所以這兩個檔被複製走時，拿到的人可以在 token 過期前自己跑 `oci session refresh`，影響的期限最長到登入後 24 小時。

## 使用 session token 時每條指令要帶的設定：config file is invalid 與 user missing

CLI 預設用 API 簽章金鑰的方式驗證身分，用 session token 時要明確告訴它。兩種寫法效果相同：

```bash
# 每條指令各自指定
oci iam region-subscription list --auth security_token
# 整個 shell 工作階段都用 session token
export OCI_CLI_AUTH=security_token
```

少了這個設定，CLI 照 API 簽章金鑰的流程檢查設定檔，而那個流程要求設定檔裡有 `user`（使用者的 OCID），session 登入寫出的設定檔沒有這一欄。實測 CLI 在送出請求之前就停下來，印出 `ERROR: The config file at ~/.oci/config is invalid`，表格裡列出 `user | missing`，提示去主控台找使用者的 OCID——照提示補上 `user` 是在改成 API 簽章金鑰的做法，對 session token 是錯的方向，該補的是 `--auth security_token`。

確認登入成功、同時查出 tenancy 的基本資訊，可以跑這幾條：

```bash
oci session validate --auth security_token          # 印出 token 的到期時間
oci iam region-subscription list --auth security_token   # 訂閱的區域，is-home-region 為 true 的是 home region
oci iam availability-domain list --auth security_token   # home region 的 availability domain 清單
```


## Session token 的時效與 refresh

Token 的預設效期是 1 小時：實測 17:44 登入，`oci session validate` 回報到期時間 18:44。過期之前可以延長：

```bash
oci session refresh --profile DEFAULT
```

`--profile` 填登入時取的 profile 名稱；登入那一條指令的選項叫 `--profile-name`，其他指令（refresh、terminate、一般查詢）都叫 `--profile`。profile 不是 `DEFAULT` 時，上一節那幾條查詢指令也要各加 `--profile <名稱>`。官方文件說明 refresh 要在 token 還有效時做，可以一路延長到登入後的 24 小時；超過 24 小時，或 token 已經過期，就要重新跑一次 `oci session authenticate`、在瀏覽器重新登入。

## API 簽章金鑰：不需要每天登入的做法

API 簽章金鑰在主控台的人像選單 → User settings 頁建立：在 API keys 那一區新增一把，讓主控台產生金鑰對並下載私鑰，完成後頁面顯示一段 `[DEFAULT]` 開頭的設定文字。

那段文字是 CLI 設定檔的一組 profile，其中 `key_file` 是一個佔位路徑，CLI 會照這一行去讀私鑰，所以貼進 `~/.oci/config` 之後要把它改成私鑰實際存放的路徑。同一台機器已經照上面的步驟用 session token 登入過時，設定檔裡已經有一組 `[DEFAULT]`，貼上的這一組要改成另一個名稱（例如 `[apikey]`），兩組同名時 CLI 只會讀其中一組。私鑰檔的權限設成只有自己能讀寫，因為持有它的人能以這個使用者的全部權限呼叫 API：

```bash
mv ~/Downloads/<下載的私鑰檔名>.pem ~/.oci/   # 瀏覽器下載的位置換成自己的
chmod 600 ~/.oci/<下載的私鑰檔名>.pem          # 私鑰檔只允許擁有者讀寫
unset OCI_CLI_AUTH                              # 前面設過 session token 的 shell 要先取消，否則仍走 session
oci iam region-subscription list --profile apikey   # 不帶 --auth，CLI 用 API 簽章金鑰
```

這把金鑰沒有到期時間。不用的時候回到 API keys 頁面刪掉它，持有私鑰的程式就無法再呼叫 API。私鑰外洩的影響範圍是這個使用者的全部權限，所以給排程與 CI 用的金鑰，建在一個只有必要權限的專用使用者底下，不建在申請時建立的管理員帳號底下。

## 延伸閱讀：帳號結構與免費額度

- [Oracle Cloud 的帳號結構與 home region](/infra/cloud-providers/oracle-cloud/account-and-home-region/)：登入頁的租用戶與使用者名稱欄位、home region 對 Always Free 的限制
- [雲端免費額度與小型主機的收費比較](/infra/cloud-providers/pricing-comparison/)：登入之後要建主機時，各家免費額度的計算方式
- [身分與存取憑證地基 — IAM 模型、OIDC 短期憑證與權限邊界設計](/infra/02-identity-credentials/iam-oidc-privilege-boundary/)：session token 與 API 簽章金鑰這組取捨背後的概念，〈長期 access key 的風險〉與〈OIDC：給 CI/CD 的短期憑證〉
