// 自動連結：把文章正文（.article-body）裡出現的知識卡名稱標成連到那張卡的連結。
// 載入它的是 layouts/partials/autolink.html，詞典與比對範圍由 <script> 的 data 屬性傳進來。
//
// 部署的網站在 hugo 輸出頁面之後就連好了：`make site` 與部署流程執行 `mdtools autolink-html public`
// （scripts/mdtools/internal/autolinkhtml），它用同一份詞典、同一組規則把連結寫進 HTML 與 RSS，並在這個 <script> 加上 data-static；
// <script> 帶著 data-static 時，這支腳本不下載詞典、不再連結，只處理下面「沒有滑鼠的裝置」那一段。
// `hugo server` 不跑那一步，本機預覽的連結由這支腳本加。比對規則只列在下面這一份，Go 的套件註解指向這裡；
// 改了這支腳本、Go 或 mdcards 任何一份的比對程式碼（含下面的 SKIP），另外兩份與 Go 的測試（autolinkhtml_test.go）
// 要一起改；scripts/mdtools/internal/mdcards/autolink.go 在 markdown 原文上照這組規則做近似的比對（L2 的孤兒卡檢查
// 與 mdtools autolink-gaps 用它）。這支腳本沒有自己的測試；SKIP 與 Go 的 skipTags 不一致時，
// autolinkhtml 的 jsparity_test.go 會失敗；其他規則的分歧由 tests/autolink-parity.spec.ts 抓（Playwright CI 在
// make site 建好的網站上抽 30 段、每段一頁，各跑一次這支腳本與 Go 的輸出，比對連結清單與正文文字）。
// mdcards 與另外兩份的分歧沒有工具偵測。
//
// 比對規則：
// - 同一處有好幾個名字可以配時取最長的那一個（「交易隔離等級」優先於「交易」）：正規表示式的
//   選項依長度由長到短排列。
// - 名字的開頭或結尾是拉丁字母或數字時，那一端要是單字的邊界（「Log」不配「Logit」），不分大小寫。
// - 名字裡的空白配任何空白（正文換行時文字節點裡是換行）；名字裡的 ' 也配 Hugo 排版後的 ’。
// - 程式碼、標題、既有的連結、按鈕與表單欄位、隱藏的元素、mermaid 圖與 SVG 裡不標（mermaid 讀的是
//   區塊裡的原始文字，插進連結會讓圖解析失敗）；noscript、iframe、title、template 這類內容不是一般
//   正文的元素也不標（元素的完整清單是下面的 SKIP）。
// - 同一個名字在範圍內對到兩張卡時，取這一頁所在資料夾的那一張；兩張都不在這個資料夾就不標。
// - 這一頁本身就是那張卡時不標。不標的名字照樣參加比對、吃掉那段文字，較短的名字不會在它的內部配到
//   （「Infrastructure Drift」卡的頁面上，正文的 Infrastructure Drift 不會把 Drift 連出去）。
//
// 呈現：連結的 class 是 kc-auto（樣式在 layouts/partials/custom_head.html），帶 data-link-title
// 與 data-link-desc，滑鼠停上去時沿用站內連結的提示框。沒有滑鼠的裝置，卡片有 description 時
// 第一下點擊顯示提示框、第二下才跳到卡片；沒有 description 的卡只帶 title，點一下就跳。
(function () {
  var script = document.currentScript;
  if (!script) return;
  var body = document.querySelector(".article-body");
  if (!body) return;
  if (script.hasAttribute("data-static")) {
    bindTouch();
    return;
  }

  var scope = [];
  try { scope = JSON.parse(script.getAttribute("data-scope") || "[]"); } catch (e) { return; }
  var pageModule = script.getAttribute("data-module") || "";
  var self = script.getAttribute("data-self") || "";
  var SKIP = /^(A|CODE|PRE|KBD|SAMP|SCRIPT|STYLE|H1|H2|H3|H4|H5|H6|BUTTON|TEXTAREA|SELECT|NOSCRIPT|IFRAME|TITLE|XMP|NOEMBED|NOFRAMES|PLAINTEXT|TEMPLATE)$/;
  var LATIN_EDGE = /[A-Za-z0-9]/;

  fetch(script.getAttribute("data-terms"))
    .then(function (r) { return r.json(); })
    .then(run)
    .catch(function () {
      // 詞典讀不到、或瀏覽器不支援 lookbehind（Safari 16.4 以前）而 new RegExp 失敗時，
      // 錯誤發生在動到 DOM 之前，正文照原樣顯示
    })
    .then(function () {
      // 連結做完（或放棄）之後標記，tests/autolink-parity.spec.ts 等這個屬性再讀連結
      script.setAttribute("data-done", "");
    });

  function escapeRe(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  }

  function pickTerms(dict) {
    var picked = {};
    dict.terms.forEach(function (t) {
      var name = t.n, card = t.c, mod = t.m;
      if (scope.indexOf(mod) < 0 || !dict.cards[card]) return;
      var key = keyOf(name);
      var cur = picked[key];
      if (!cur) { picked[key] = { name: name, card: card, mod: mod, ambiguous: false }; return; }
      if (cur.mod === pageModule && mod !== pageModule) return;
      if (mod === pageModule && cur.mod !== pageModule) {
        picked[key] = { name: name, card: card, mod: mod, ambiguous: false };
        return;
      }
      cur.ambiguous = true;
    });
    // 歧義與自己那張卡的名字留在表裡、標成不連，比對時照樣吃掉那段文字
    Object.keys(picked).forEach(function (key) {
      var p = picked[key];
      p.link = !p.ambiguous && p.card !== self;
    });
    return picked;
  }

  // 比對用的鍵：小寫、連續空白縮成一個、’ 換回 '，跟詞典的名字用同一種寫法
  function keyOf(s) {
    return s.toLowerCase().replace(/\s+/g, " ").replace(/\u2019/g, "'");
  }

  function buildRegex(terms) {
    var names = Object.keys(terms).map(function (k) { return terms[k].name; });
    if (!names.length) return null;
    names.sort(function (a, b) { return b.length - a.length; });
    var parts = names.map(function (n) {
      var head = LATIN_EDGE.test(n.charAt(0)) ? "(?<![A-Za-z0-9_])" : "";
      var tail = LATIN_EDGE.test(n.charAt(n.length - 1)) ? "(?![A-Za-z0-9_])" : "";
      var body = escapeRe(n).replace(/\s+/g, "\\s+").replace(/'/g, "['\u2019]");
      return head + body + tail;
    });
    return new RegExp(parts.join("|"), "gi");
  }

  function skipped(node) {
    for (var el = node.parentElement; el && el !== body; el = el.parentElement) {
      if (SKIP.test(el.tagName) || el.hidden || el.classList.contains("mermaid")) return true;
      if (el instanceof SVGElement) return true;
    }
    return false;
  }

  function run(dict) {
    var terms = pickTerms(dict);
    var re = buildRegex(terms);
    if (!re) return;

    var nodes = [];
    var walker = document.createTreeWalker(body, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        return n.nodeValue.trim() && !skipped(n) ? NodeFilter.FILTER_ACCEPT : NodeFilter.FILTER_REJECT;
      }
    });
    while (walker.nextNode()) nodes.push(walker.currentNode);

    nodes.forEach(function (node) {
      var text = node.nodeValue;
      re.lastIndex = 0;
      var m, last = 0, frag = null;
      while ((m = re.exec(text))) {
        var term = terms[keyOf(m[0])];
        if (!term || !term.link) continue;
        var card = dict.cards[term.card];
        frag = frag || document.createDocumentFragment();
        if (m.index > last) frag.appendChild(document.createTextNode(text.slice(last, m.index)));
        var a = document.createElement("a");
        a.className = "kc-auto";
        a.href = card.u;
        a.textContent = m[0];
        if (card.d) {
          a.setAttribute("data-link-title", card.t);
          a.setAttribute("data-link-desc", card.d);
        } else {
          a.title = card.t;
        }
        frag.appendChild(a);
        last = m.index + m[0].length;
      }
      if (!frag) return;
      if (last < text.length) frag.appendChild(document.createTextNode(text.slice(last)));
      node.parentNode.replaceChild(frag, node);
    });

    bindTouch();
  }

  function bindTouch() {
    if (window.matchMedia && window.matchMedia("(hover: none)").matches) {
      body.addEventListener("click", function (e) {
        var a = e.target.closest && e.target.closest("a.kc-auto[data-link-desc]");
        body.querySelectorAll("a.kc-open").forEach(function (o) { if (o !== a) o.classList.remove("kc-open"); });
        if (!a || a.classList.contains("kc-open")) return;
        e.preventDefault();
        a.classList.add("kc-open");
      });
    }
  }
})();
