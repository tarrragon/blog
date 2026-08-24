---
title: "commit message 引用外部 issue 會在對方 repo 留下事件——檔案內容裡的同一串字不會"
slug: "github-cross-reference-from-commit-message"
date: 2026-08-24
description: "在 commit message 裡寫下對其他專案 issue 的引用之前先讀。判斷這次引用會不會在對方 repo 留下事件，以及留下之後還剩多少處置空間。"
tags: ["github", "git", "collaboration", "workflow"]
---

## 引用形式與 push 是產生事件的必要條件

commit message 尾端補上來源引用時，形式大致是這樣：

```text
References:
- owner/repo#1234
```

會走到這一步的情境不只一種：修完一個由上游 bug 引起的問題、升版撿了對方已經修好的 fix、對應到同一個組織底下另一個 repo 的 issue、或者引用自己 fork 的來源專案。共同點是引用的目標在**另一個 repo**。

commit push 上去之後，被引用的那個 issue 的 timeline 會多出一筆事件：

```text
<帳號名稱> added a commit that references this issue
```

兩件事促成它：引用寫成 GitHub 認得的形式，以及 commit 被 push 上去。這兩件是必要條件，而下一節記錄了一次兩者都成立、事件卻沒有產生的觀察——把它們當成充分條件並不安全。事件已經產生、想知道還能不能收回的讀者，可以直接跳到[沒有任何操作是刪掉這一筆事件](#沒有任何操作是刪掉這一筆事件)。

事件的行為者記給推送者還是 commit 的 author，本文的案例分辨不出來：兩則 commit 的 author、committer 與 pusher 都是同一個帳號。官方只寫「產生該事件的人」，沒有進一步界定。案例的 `Co-Authored-By` 用的是不對應任何 GitHub 帳號的信箱，所以「署名欄位不參與歸屬」這件事同樣沒有被這組資料驗證。

repo 的公開性不是觸發條件。官方文件說明 issues-only repo 的段落描述過私有 repo 的 commit 關閉公開 issue 的情形，可以推得引用本身成立；公開性影響的是權限不足的人看得到多少細節。

## 一則帶引用的 commit 沒有產生事件、原因未知

案例是一則升級測試框架版本的 commit（雜湊 `1e696dd9`，2026-05-27）。它的 `References:` 區塊寫了兩行完整形式的引用，指向兩個不同的上游專案。用 `gh api repos/{owner}/{repo}/issues/{n}/timeline --paginate` 讀那兩個 issue，各出現一筆 `referenced` 事件，`commit_id` 都指向該 commit。

隔天另有一則 commit（雜湊 `cb7da7c9`）在 message 裡引用了**同樣那兩個 issue**、同樣是完整形式、同樣單獨推上 default branch，而兩個 issue 都沒有因此增加事件。

一個看起來合理的解釋是「同一個 repo 對同一個 issue 只記一次」。**這個解釋被同一批資料推翻**：把那兩個 issue 的完整 timeline 按來源 repo 分組，`microsoft/playwright#41000` 的 43 個來源 repo 裡有 13 個各留下超過一筆事件，最高的一個 repo 有 9 筆；`nodejs/node#63487` 的 28 個裡有 8 個超過一筆，最高 6 筆。同一個 repo、同一個帳號、甚至同一次 push 產生兩筆的情形都存在。

其餘假說也逐一排除掉了：

- 事件有產生而分頁沒抓到——用 `--paginate` 重查，該帳號在兩個 issue 各只有一筆
- 去重的條件是 per-actor——同一帳號對同一 issue 的多筆事件存在
- 第二則 commit 進了別的分支或推送批次被截斷——`git rev-list --count 1e696dd9..cb7da7c9` 是 1，單獨一則推上 `origin/main`
- 目標 issue 已關閉所以不再收事件——那兩個 issue 在關閉之後仍持續累積事件

剩下沒有排除的是解析邊界。`cb7da7c9` 的兩處引用格式不同：一處夾在全形括號 `（）` 之間、字元緊貼沒有 ASCII 邊界，另一處是列表項中以半形空格分隔的裸寫。前者有合理的解析失敗理由，後者的邊界看起來乾淨，而這組資料無法單獨驗證後者。

**這個非事件目前沒有解釋。** 記下來是為了讓遇到同樣情形的人知道它會發生，以及哪些解釋已經被排掉。實務上的推論只到這裡：引用寫了不一定就會送達，要確認對方 timeline 上有沒有這一筆，用上面那條 timeline 指令查得到——那是事前與事後都可執行的檢查。

同一批資料另有一個歸因限制。`1e696dd9` 對其中一個 issue 的引用出現兩次（一次在正文的全形括號內、一次在 `References:` 區塊），總共一筆事件。哪一處造成的分不出來，所以「同一則 commit 裡重複的引用會被合併」與「只有格式乾淨的那一處被解析」在這組觀察下等價。

## 解析範圍限於對話類的位置

GitHub 把 issue 與 pull request 的縮寫引用展開成連結（官方稱為 autolink），範圍限於對話類的位置。文件對範圍的正面描述是「Within conversations on GitHub」，而做功的判準是那句排除條文：

> Autolinked references are not created in wikis or files in a repository.

同一串字的效果取決於它住在哪個位置。

| 文字所在位置                          | 解析行為   | 對外效果                                |
| ------------------------------------- | ---------- | --------------------------------------- |
| commit message                        | 解析成引用 | 目標 issue 產生 `referenced` 事件       |
| issue / PR 內文與留言                 | 解析成引用 | 目標 issue 產生 `cross-referenced` 事件 |
| repo 內的檔案（README、原始碼、文件） | 維持純文字 | 該串字只是文字，不產生任何事件          |
| wiki 頁面                             | 維持純文字 | 該串字只是文字，不產生任何事件          |

前兩列的事件型別在 GitHub API 裡是分開的：commit message 來源記成 `referenced`（文件的說明是 "The issue was referenced from a commit message"），issue 與 PR 來源記成 `cross-referenced`。兩者在 timeline 上的呈現相近，查 API 或寫自動化時要分清楚。

檔案內容留在純文字這一格帶來一個直接推論：把觸發語法寫進 README 或教學文章的正文與 code block，不會產生任何新的事件。檔案與 wiki 這一側不需要控制；要控制的是會被解析的那一類位置，也就是 commit message、PR 描述與 issue 留言這三處。

## commit message 裡是形式決定觸不觸發

本節的判斷限於 commit message。issue 與 PR 內文會經過 markdown 渲染，解析細節與這裡不同，不在本文範圍。

| 寫法                    | 解析結果                                                             |
| ----------------------- | -------------------------------------------------------------------- |
| `#1234`                 | 指向 commit 所在 repo 自己的第 1234 號 issue；號碼不存在時無事件產生 |
| `GH-1234`               | 指向 commit 所在 repo 自己的第 1234 號 issue，效果與裸井字號相同     |
| `owner/repo#1234`       | 跨 repo 引用，目標 issue 產生事件                                    |
| issue 的完整網址        | 跨 repo 引用，效果與 `owner/repo#1234` 相同                          |
| `owner/repo issue 1234` | 維持純文字，人讀得懂而解析器不認                                     |

裸的井字號解析範圍限於 commit 所在的那個 repo。案例那則 commit 的正文裸寫過 `#41000`，GitHub 把它解析成本 repo 自己的第 41000 號、該號碼不存在，於是沒有產生任何事件。

commit SHA 也會 autolink（`<40-hex>`、`user@SHA`、`owner/repo@SHA`），跨 repo 的形式同樣會在對方留下記錄。本文其餘部分討論的是 issue 引用。

要保留可讀性又停在純文字，把井字號拿掉就夠了。改貼完整網址則得到相同的觸發效果，網址形式一樣被解析。

## 引用與關閉是兩種不同的動作

單純提及只產生 timeline 事件。GitHub 另有一組關閉關鍵字（`fixes` / `closes` / `resolves` 等），文件對 commit message 的行為說明是：commit 併入 default branch 時關閉對應 issue，跨 repo 的形式寫成 `KEYWORD OWNER/REPOSITORY#ISSUE-NUMBER`。

跨 repo 關閉的權限條件有明文，寫在說明 issues-only repo 的那一頁：

> Users with write access to both can reference and close issues back and forth across the repositories, but those without the required permissions will see references that contain a minimum of information.

對一般的上游開源專案沒有這個權限，關閉關鍵字因此只會退化成一般引用。權限成立的組合則要留意：同一個組織底下的兩個 repo 是常見形態，成員對兩邊通常都有 write access，關閉會真的發生。團隊的 commit template 固定用 `fixes` 前綴、而這次對應的是另一個 repo 的 issue 時，這兩個條件湊在一起就足以關掉對方的 issue。關閉發生在對方 repo，引用方這端沒有任何提示；對方若用 open 清單做 triage，被關掉的項目直接退出清單。

template 用的是**裸**井字號時，後果換一個方向但同樣要檢查：`fixes #N` 的解析範圍是 commit 所在的 repo，關掉的是自己這邊第 N 號那張無關的 issue。想引用另一個 repo 卻沿用 template 的號碼寫法，兩種寫法都會出事，只是出在不同地方。

誤觸關閉的補救成本遠低於引用事件：issue 可以直接 reopen，代價是重開與說明。兩者的不可逆程度不同，下一節談的是引用事件那一側。

## 沒有任何操作是刪掉這一筆事件

引用方與被引用方都有辦法讓這筆事件從畫面上消失，但沒有一個操作的作用對象是這筆事件本身：

- **引用方**可以把 commit 從公開歷史裡拿掉，代價是 force-push 改寫已公開的分支——所有已經 clone 的人都要處理分歧，別處引用過的 SHA 全部失效，而物件回收之後 timeline 事件會不會跟著消失，官方文件沒有說明。另一條路是把整個 repo 轉為私有或刪除，成本低得多，作用對象卻是整個 repo。
- **被引用方**可以刪除或搬移那張 issue，整條 timeline 隨之消失；也可以封鎖引用方的帳號。鎖定 issue 管的是留言與 reaction，對已經寫入的引用事件沒有作用。

這些選項的共同形狀是：能動的都是整個 repo、整張 issue 或整個帳號，沒有一個是「刪掉這一列」。想只移除這一筆而不動其他東西，做不到。

這筆事件對被引用方造成多少打擾，是本文查不到答案的一項：GitHub 的通知文件只說明什麼情況會被自動訂閱，沒有列舉哪些 timeline 事件會發出通知，因此無法判斷引用會不會進到對方的收件匣。可以確定的是它會留在 issue 頁面上，後來讀這個 issue 的人都看得到。

## 判準

判準之前先過一道閘門：這次的 commit message 裡有沒有關閉關鍵字。有的話，先確認號碼指向哪個 repo、以及自己對那個 repo 有沒有 write access——上一節的兩種出事方向都發生在這一步沒檢查的時候。

閘門過了之後，決定引用要不要寫成會觸發的形式，判準看的是這次變更與目標 issue 的因果關係。

| 這次變更與目標 issue 的關係                    | 寫法                                                        |
| ---------------------------------------------- | ----------------------------------------------------------- |
| 變更的原因來自它（修法、升版、繞過都算）       | 用 `owner/repo#N` 完整形式，事件對上游是有效訊號            |
| 查證時讀過它，而變更與它沒有因果               | 拿掉井字號寫成 `owner/repo issue N`，事件對雙方沒有資訊價值 |
| 有因果，但同一件事本 repo 已經引用過           | 拿掉井字號，重複的引用只增加對方 timeline 的長度            |
| 需要記錄的脈絡超過 commit message 容得下的長度 | 寫進 repo 內的紀錄檔，形式仍照上面三列決定                  |

因果關係在動手前就知道，不需要等事件產生才判斷。目標 issue 是 open 還是已關閉不影響這張表：有因果的引用對正在追這件事的 maintainer 是訊號、對已關閉的 issue 是可回溯的實證，兩種情形都值得讓事件成立。最後一列跟前三列正交，長脈絡與引用形式是兩個獨立決定。

commit message 與 repo 內紀錄檔的分工，另見[Commit message vs source code doc](/record/commit-message-vs-source-doc/)。

## 參考資料

- [GitHub Docs：Autolinked references and URLs](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/autolinked-references-and-urls) — 各種引用形式，以及「wiki 與 repo 內檔案不建立 autolink」的排除條文
- [GitHub Docs：Linking a pull request to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue) — 關閉關鍵字在 commit message 的行為與跨 repo 形式
- [GitHub Docs：Creating an issues-only repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-an-issues-only-repository) — 跨 repo 引用與關閉的權限條件，以及權限不足時的遮蔽行為
- [GitHub Docs：Issue event types](https://docs.github.com/en/rest/using-the-rest-api/issue-event-types) — `referenced` 與 `cross-referenced` 的定義差異
- 同站：[CI step silent hang：時間真空才是訊號](/work-log/ci-silent-hang-diagnosis/) — 本文案例的技術脈絡
- 同站：[移除已推送的 git 歷史內容](/work-log/remove_git_content/) — 改寫公開歷史的完整流程，與本文撤回那一節搭配讀
