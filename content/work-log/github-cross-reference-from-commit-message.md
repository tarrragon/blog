---
title: "commit message 引用外部 issue 會在對方 repo 留下永久事件——檔案內容裡的同一串字不會"
slug: "github-cross-reference-from-commit-message"
date: 2026-08-24
description: "在 commit message 裡寫下對其他專案 issue 的引用之前先讀。判斷哪些寫法會在對方 repo 產生 timeline 事件、哪些維持純文字，以及事件產生後還剩多少處置空間。"
tags: ["github", "git", "commit-message", "collaboration", "workflow"]
---

## 觸發這件事的條件

修完一個由 upstream bug 引起的問題，commit message 尾端習慣補一段來源引用，形式大致是這樣：

```text
References:
- owner/repo#1234
```

commit push 到一個 public repo 之後，被引用的那個 issue 的 timeline 會多出一筆事件：

```text
<帳號名稱> added a commit that references this issue
```

三個條件同時成立才會產生這筆事件：引用寫成 GitHub 認得的形式、commit 所在的 repo 是 public、以及有人把它 push 上去。事件的行為者是**執行 push 的帳號**，跟 commit 的 author 與 `Co-Authored-By` 欄位無關——所以 commit message 由誰或由什麼工具起草，都不影響這筆事件記在哪個帳號名下。

本站遇到的實例是一則升級測試框架版本的 commit：message 的 `References:` 區塊用完整縮寫形式寫了 microsoft/playwright 的 issue 41000，該 issue 的 timeline 因此出現一筆引用事件。當時的技術脈絡在 [CI step silent hang：時間真空才是訊號](/work-log/ci-silent-hang-diagnosis/)。

## 解析範圍限於對話類 surface

GitHub 把 issue 與 pull request 的縮寫引用展開成連結，範圍限於對話類的 surface。官方文件對範圍的正面描述是「Within conversations on GitHub」，而排除項寫得比範圍本身更明確：

> Autolinked references are not created in wikis or files in a repository.

這一句是判斷「寫在哪裡會有對外效果」的依據——同一串字的效果完全取決於它住在哪個位置。

| 文字所在位置               | 解析行為   | 對外效果                      |
| -------------------------- | ---------- | ----------------------------- |
| commit message             | 解析成引用 | 目標 issue 產生 timeline 事件 |
| issue / PR 內文與留言      | 解析成引用 | 目標 issue 產生 timeline 事件 |
| repo 內的原始碼與 `.md` 檔 | 維持純文字 | 僅在該檔案內顯示              |
| wiki 頁面                  | 維持純文字 | 僅在該頁面顯示                |

檔案內容留在純文字這一格帶來一個直接推論：把觸發語法寫進教學文章的正文或 code block，不會產生任何新的事件。要控制的位置只有 commit message 一處。

## 寫法與解析結果

| 寫法                    | 解析結果                                                       |
| ----------------------- | -------------------------------------------------------------- |
| `#1234`                 | 指向 commit 所在 repo 自己的第 1234 號；號碼不存在時無事件產生 |
| `owner/repo#1234`       | 跨 repo 引用，目標 repo 產生 timeline 事件                     |
| issue 的完整網址        | 跨 repo 引用，效果與縮寫形式相同                               |
| `owner/repo issue 1234` | 維持純文字，語意保留                                           |

裸的井字號寫法值得單獨說明，因為它的解析範圍是 commit 所在的那個 repo。前述那則 commit 的正文段落也出現過裸寫的 `#41000`，GitHub 把它解析成本 blog repo 自己的第 41000 號、該號碼不存在，於是沒有產生任何事件——真正觸發的只有 `References:` 區塊那一行完整形式。

要保留可讀性又停在純文字，把井字號拿掉就夠了。改貼完整網址則得到相同的觸發效果，網址形式一樣被解析。

## 引用與關閉是兩種不同的動作

單純提及只產生 timeline 事件。GitHub 另有一組關閉關鍵字（`fixes` / `closes` / `resolves` 等），文件對 commit message 的行為說明是：commit 併入 default branch 時關閉對應 issue，跨 repo 的形式寫成 `KEYWORD OWNER/REPOSITORY#ISSUE-NUMBER`。

這裡有一條本文沒有走完的邊界：「在自己的 repo 用關閉關鍵字關掉他人專案的 issue 需要什麼權限」，官方文件沒有明確條文，本文也沒有實測——在別人的 repo 上做這種實驗本身就是打擾。可以確定的部分是，`References:` 這種中性前綴不帶關閉語意，是引用 upstream issue 時語意最窄的寫法。

## 事件產生後的處置空間

這筆事件寫在對方 repo 的 timeline 上，兩邊能做的事都有限：

- **引用方**要移除它，得把該 commit 從 public 歷史裡拿掉（改寫歷史加上等待 GitHub 回收物件），而 timeline 事件未必跟著消失。
- **被引用方**能做的是鎖定該 issue；cross-reference 事件本身留在 timeline 上。

私有 repo 的行為方向一致、只差在可見度。GitHub 文件描述的情境是：私有 repo 的 default branch 收到一則帶關閉關鍵字的 commit，公開 issue 確實被關閉，而只有具備權限的人看得到是哪個 commit 關的。私有 repo 提供的是可見度上的遮蔽，不是「引用不成立」。

處置空間窄，代表這是**寫 commit message 的當下**要決定的事，事後沒有等價的撤回動作。

## 判準

| 情境                                                    | 寫法                                                  |
| ------------------------------------------------------- | ----------------------------------------------------- |
| 修法直接來自某個 upstream issue、希望留下雙向可回溯線索 | 用 `owner/repo#N` 完整形式，讓事件成立                |
| 只是記錄查證過程、不打算通知上游                        | 拿掉井字號，寫成 `owner/repo issue N`                 |
| 要記錄的脈絡較長                                        | 寫進 repo 內的檔案（work-log 或隨 commit 附上的文件） |
| 不確定 commit 落在哪個 repo                             | 先確認公開性；public 才會對外產生事件                 |

讓事件成立這一條值得補一句立場：它通常對雙方有利。對上游 maintainer 而言，「有下游因此升版並解決」是一筆可回溯的實證，而已關閉的 issue 上多一筆引用不干擾 triage 流程。避開觸發的理由通常是別的——引用只是自己的查證筆記、或者引用的是仍在活躍討論中的 issue，此時一筆無關的下游事件確實構成雜訊。

## 參考資料

- [GitHub Docs：Autolinked references and URLs](https://docs.github.com/en/get-started/writing-on-github/working-with-advanced-formatting/autolinked-references-and-urls) — 引用語法，以及「wiki 與 repo 內檔案不建立 autolink」的排除條文
- [GitHub Docs：Linking a pull request to an issue](https://docs.github.com/en/issues/tracking-your-work-with-issues/using-issues/linking-a-pull-request-to-an-issue) — 關閉關鍵字在 commit message 的行為與跨 repo 形式
- [GitHub Docs：Creating an issues-only repository](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-an-issues-only-repository) — 跨 repo 引用在權限不足時的遮蔽行為
- 同站：[CI step silent hang：時間真空才是訊號](/work-log/ci-silent-hang-diagnosis/) — 本文案例的技術脈絡
