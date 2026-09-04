# case-first-module-workflow 版本紀錄

新到舊。版號規則與兩個住址（本檔與 `SKILL.md` frontmatter 的 `metadata.version`）見專案的 skill 同步規範。

**Version**: 1.7.1 — `fix-the-class-not-the-cited-instances` 卡補「執行本身有深淺」（與本體同步）：那三次的層級分別是不掃、掃了但只掃同形、掃同形再加逐項對照，寫成「掃一遍」的那一行會停在它最便宜的解釋上。

**Version**: 1.7.0 — `fix-the-class-not-the-cited-instances` 原則卡補三項（與本體同步）：字串掃描抓得到同形殘留而抓不到異形殘留、掃描的輸出要逐條列出不讀計數、以及這一條要放進收尾動作清單而不是只放在原則層——一次四輪審查裡同型失誤發生三次，三次的動作差別只有一項（修完有沒有再掃一遍），而規則在三次之前就已經讀過。

**Version**: 1.6.1 — 版本紀錄搬到同目錄的 `CHANGELOG.md`。skill 是 runtime 整份載入的檔案，而沒有任何規則要求任何人讀版本紀錄，留在 SKILL.md 等於每次叫用都付一次無效讀取。SKILL.md 末尾留一行指過去，版號的兩個住址改成「CHANGELOG.md 最上面那一條 + frontmatter 的 metadata.version」。skill 的指令內容一個字都沒改。

**Version**: 1.6.0 — Stage 4 修正循環補一條處置端紀律並新增 principle 卡 fix-the-class-not-the-cited-instances：**每個 issue 修完之後掃的是那一類、不是清單上的那幾行**。原本整段以 issue 清單為單位組織（按嚴重度、按檔案批次），沒有任何一步要求回頭掃同類的其他位置，而 reviewer 列出的是抽樣位置、清單的形式卻在暗示完整性。實測是同一個動詞的同一處論元結構歧義散在三個位置，四份理解探針一致指向其中一行、修好並經驗證翻轉，另外兩處由後續換 frame 的探針才撞見；同批另有四次同形態復發。修法是用特徵字串掃整批、掃描指令先驗管道、無關鍵詞的類別改派限定 scope 的複掃

**Version**: 1.5.1 — 術語校正：判準全數改為判斷標準（動作修飾語縮為「X 標準」、狀態義改為「X 條件」）。判準的語域在哲學與教育評量、工程讀者解析不了——五份低階模型探針一致回報非通用

**Version**: 1.5.0 — Stage 2 寫作前加「承重論點先 steelman 再寫」gate：分析 / 合成型模組若架在一個承重論點上（方法論主張、跨 case 合成 frame、核心分類假設），動筆前先對它跑對抗性挑戰當生產閘門、別等 Stage 3 才挑戰（同 cadence 抽樣「別等 reviewer」邏輯、只在 Stage 3 抓＝錯誤已寫進 N 章跨章回改）；承重論點常是全稱 / 唯一性宣稱、別把「還沒找到反例」當「不存在反例」；挑戰交對抗 / 異源。從神經多樣性方法論生產順序事故抽出（對應 report 卡 #236）。
**Version**: 1.4.0 — 從 backend/11 API 設計模組（10 主章、54 case、3 reviewer 63 issue）retrospective 回流兩個新 pattern：(1) 合成章的引力 — 合成型框架章吸走主寫章案例細節、SSoT map 主寫方向被靜默反轉、加「一句話案例 + link」硬規則（Stage 2 核心條目 7、反覆陷阱 16、ssot-correspondence 新段）；(2) 預測性索引要有寫後回填輪 — 大綱案例支撐欄與 case 檔對應大綱欄是預測、正文完成後跑機械性回填、跟 lint 同級（Stage 2 尾段、反覆陷阱 17、ssot-correspondence 自掃描提示 5-6）。

**Version**: 1.0.0
