---
title: "commit message 引用外部 issue 會在對方 repo 留下事件——檔案內容裡的同一串字不會"
slug: "github-cross-reference-from-commit-message"
date: 2026-08-24
description: "在 commit message 裡提到其他專案的 issue 之前先讀。判斷哪些寫法會讓引用出現在對方 issue 的 timeline、哪些停在純文字，以及出現之後還能不能收回。"
tags: ["github", "git", "collaboration", "workflow"]
---

## commit message 裡的 issue 引用會出現在對方的 issue 上

commit message 尾端補上來源引用時，形式大致是這樣：

```text
References:
- owner/repo#1234
```

commit push 上去之後，被引用的那個 issue 的 timeline 會多出一筆事件：

```text
<帳號名稱> added a commit that references this issue
```

這件事是從一則升級測試框架版本的 commit 發現的：message 的 `References:` 區塊寫了兩行指向上游專案的引用，那兩個 issue 的 timeline 就各多了一筆記錄，指回這則 commit。

兩件事促成它：引用寫成 GitHub 認得的形式，以及 commit 被 push 上去。事件記在**推送者**的帳號名下，所以出現在對方 issue 上的是推送者的名字。

寫了引用不保證一定送達。要確認對方 timeline 上有沒有這一筆，用 `gh api repos/{owner}/{repo}/issues/{n}/timeline --paginate` 查得到——想讓引用成立的時候，這是驗收的動作。

repo 的公開性不是觸發條件，它影響的是權限不足的人看得到多少細節。

## 解析只發生在對話類的位置

GitHub 把 issue 與 pull request 的縮寫引用展開成連結（官方稱為 autolink），範圍限於對話類的位置。文件的正面描述是「Within conversations on GitHub」，而做功的判準是那句排除條文：

> Autolinked references are not created in wikis or files in a repository.

同一串字的效果取決於它住在哪個位置。

| 文字所在位置                          | 解析行為   | 對外效果                                |
| ------------------------------------- | ---------- | --------------------------------------- |
| commit message                        | 解析成引用 | 目標 issue 產生 `referenced` 事件       |
| issue / PR 內文與留言                 | 解析成引用 | 目標 issue 產生 `cross-referenced` 事件 |
| repo 內的檔案（README、原始碼、文件） | 維持純文字 | 該串字只是文字，不產生任何事件          |
| wiki 頁面                             | 維持純文字 | 該串字只是文字，不產生任何事件          |

檔案內容留在純文字這一格是最省事的迴避方式：把引用寫進 README 或專案文件，形式照原樣保留，對方那邊不會有任何動靜。要控制的只有會被解析的那三處——commit message、PR 描述與 issue 留言。

前兩列的事件型別在 GitHub API 裡是分開的：commit message 來源記成 `referenced`，issue 與 PR 來源記成 `cross-referenced`。兩者在 timeline 上的呈現相近，查 API 或寫自動化時要分清楚。

## 哪些寫法會觸發

本節的判斷限於 commit message。issue 與 PR 內文會經過 markdown 渲染，解析細節與這裡不同。

| 寫法                    | 解析結果                                                             |
| ----------------------- | -------------------------------------------------------------------- |
| `#1234`                 | 指向 commit 所在 repo 自己的第 1234 號 issue；號碼不存在時無事件產生 |
| `GH-1234`               | 指向 commit 所在 repo 自己的第 1234 號 issue，效果與裸井字號相同     |
| `owner/repo#1234`       | 跨 repo 引用，目標 issue 產生事件                                    |
| issue 的完整網址        | 跨 repo 引用，效果與 `owner/repo#1234` 相同                          |
| `owner/repo issue 1234` | 維持純文字，人讀得懂而解析器不認                                     |

**要讓引用成立**，用 `owner/repo#1234` 或完整網址。裸的井字號沒有跨 repo 效果，它指的是 commit 所在的那個 repo。

**要避免觸發**，把井字號拿掉寫成 `owner/repo issue 1234`。語意完整保留、人讀得懂，而解析器不認。改貼完整網址不是迴避方式，網址形式一樣被解析。

commit SHA 也會 autolink（`<40-hex>`、`user@SHA`、`owner/repo@SHA`），跨 repo 的形式同樣會在對方留下記錄。

## 引用與關閉是兩種不同的動作

單純提及只產生 timeline 事件。GitHub 另有一組關閉關鍵字（`fixes` / `closes` / `resolves` 等）：commit 併入 default branch 時關閉對應 issue，跨 repo 的形式寫成 `KEYWORD OWNER/REPOSITORY#ISSUE-NUMBER`。

跨 repo 關閉的權限條件有明文，寫在說明 issues-only repo 的那一頁：

> Users with write access to both can reference and close issues back and forth across the repositories, but those without the required permissions will see references that contain a minimum of information.

對一般的上游開源專案沒有這個權限，關閉關鍵字只會退化成一般引用。權限成立的組合要留意：同一個組織底下的兩個 repo 是常見形態，成員對兩邊通常都有 write access，關閉會真的發生。

commit template 固定用 `fixes` 前綴的團隊有兩個方向會出事。寫成 `fixes other-repo#N` 且雙邊都有 write access 時，關掉的是對方的 issue，而引用方這端沒有任何提示。沿用 template 的裸號碼寫成 `fixes #N` 時，關掉的是自己這邊第 N 號那張無關的 issue。

誤觸關閉的補救成本低：issue 直接 reopen 即可。真正收不回來的是下一節談的引用事件。

## 事件留下之後沒有辦法只刪掉它

引用方與被引用方都有辦法讓這筆事件從畫面上消失，但沒有一個操作的作用對象是這筆事件本身：

- **引用方**可以把 commit 從公開歷史裡拿掉，代價是 force-push 改寫已公開的分支——所有已經 clone 的人都要處理分歧，別處引用過的 SHA 全部失效。另一條路是把整個 repo 轉為私有或刪除，作用對象是整個 repo。
- **被引用方**可以刪除或搬移那張 issue，整條 timeline 隨之消失；也可以封鎖引用方的帳號。鎖定 issue 管的是留言與 reaction，對已經寫入的引用事件沒有作用。

能動的都是整個 repo、整張 issue 或整個帳號，沒有一個是「刪掉這一列」。

這筆事件對被引用方造成多少打擾，官方文件查不到答案：GitHub 的通知文件只說明什麼情況會被自動訂閱，沒有列舉哪些 timeline 事件會發出通知。可以確定的是它會留在 issue 頁面上，後來讀這個 issue 的人都看得到。

這就是這個機制的意義所在：寫進 commit message 的一串字會在別人的專案裡留下永久記錄，而決定的時機只有寫的當下。

## 判準

先過一道閘門：這次的 commit message 裡有沒有關閉關鍵字。有的話，先確認號碼指向哪個 repo、以及自己對那個 repo 有沒有 write access。

閘門過了之後，判準看的是這次變更與目標 issue 的因果關係。

| 這次變更與目標 issue 的關係                    | 寫法                                                        |
| ---------------------------------------------- | ----------------------------------------------------------- |
| 變更的原因來自它（修法、升版、繞過都算）       | 用 `owner/repo#N` 完整形式，事件對上游是有效訊號            |
| 查證時讀過它，而變更與它沒有因果               | 拿掉井字號寫成 `owner/repo issue N`，事件對雙方沒有資訊價值 |
| 有因果，但同一件事本 repo 已經引用過           | 拿掉井字號，重複的引用只增加對方 timeline 的長度            |
| 需要記錄的脈絡超過 commit message 容得下的長度 | 寫進 repo 內的紀錄檔，形式仍照上面三列決定                  |

因果關係在動手前就知道，不需要等事件產生才判斷。目標 issue 是 open 還是已關閉不影響這張表：有因果的引用對正在追這件事的 maintainer 是訊號、對已關閉的 issue 是可回溯的實證。最後一列跟前三列正交，長脈絡與引用形式是兩個獨立決定。

commit message 與 repo 內紀錄檔的分工，另見[Commit message vs source code doc](/record/commit-message-vs-source-doc/)。

## 參考資料

- [GitHub Docs：Autolinked references and URLs](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/autolinked-references-and-urls) — 各種引用形式，以及「wiki 與 repo 內檔案不建立 autolink」的排除條文
- [GitHub Docs：Linking a pull request to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue) — 關閉關鍵字在 commit message 的行為與跨 repo 形式
- [GitHub Docs：Creating an issues-only repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-an-issues-only-repository) — 跨 repo 引用與關閉的權限條件，以及權限不足時的遮蔽行為
- [GitHub Docs：Issue event types](https://docs.github.com/en/rest/using-the-rest-api/issue-event-types) — `referenced` 與 `cross-referenced` 的定義差異
- 同站：[CI step silent hang：時間真空才是訊號](/work-log/ci-silent-hang-diagnosis/) — 本文案例的技術脈絡
- 同站：[移除已推送的 git 歷史內容](/work-log/remove_git_content/) — 改寫公開歷史的完整流程
