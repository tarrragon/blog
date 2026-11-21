package autolinkhtml

import (
	"bytes"
	"encoding/json"
	"io"
	"strings"

	"golang.org/x/net/html"
)

// skipTags are the elements whose text the page script leaves alone (its
// SKIP pattern), plus svg: everything inside an SVG element is skipped. The
// raw-text elements (noscript, iframe, title, xmp, noembed, noframes,
// plaintext) are in the list because the tokenizer hands their content over
// undecoded, and LinkText would escape it a second time; template is in it
// because its content is not part of the document the page script walks.
var skipTags = map[string]bool{
	"a": true, "code": true, "pre": true, "kbd": true, "samp": true, "script": true, "style": true,
	"h1": true, "h2": true, "h3": true, "h4": true, "h5": true, "h6": true,
	"button": true, "textarea": true, "select": true, "svg": true,
	"noscript": true, "iframe": true, "title": true, "xmp": true, "noembed": true, "noframes": true,
	"plaintext": true, "template": true,
}

// voidTags never have an end tag, so they are not pushed on the stack.
var voidTags = map[string]bool{
	"area": true, "base": true, "br": true, "col": true, "embed": true, "hr": true, "img": true,
	"input": true, "link": true, "meta": true, "param": true, "source": true, "track": true, "wbr": true,
}

// StaticAttr marks a page's autolink <script> once this step has linked the
// page; the page script then skips its own linking.
const StaticAttr = "data-static"

func attr(t html.Token, key string) (string, bool) {
	for _, a := range t.Attr {
		if a.Key == key {
			return a.Val, true
		}
	}
	return "", false
}

func hasClass(t html.Token, class string) bool {
	v, _ := attr(t, "class")
	for _, c := range strings.Fields(v) {
		if c == class {
			return true
		}
	}
	return false
}

func skips(t html.Token) bool {
	if skipTags[t.Data] || hasClass(t, "mermaid") {
		return true
	}
	_, hidden := attr(t, "hidden")
	return hidden
}

func isAutolinkScript(t html.Token) bool {
	if t.Data != "script" {
		return false
	}
	_, ok := attr(t, "data-terms")
	return ok
}

// ScriptInfo reads the page's autolink <script>: the dictionary URL, the
// Page it describes, and whether this step already linked the page. ok is
// false when the page has no such script (its folder does not auto-link).
func ScriptInfo(src []byte) (terms string, p Page, done, ok bool, err error) {
	z := html.NewTokenizer(bytes.NewReader(src))
	for {
		switch z.Next() {
		case html.ErrorToken:
			if z.Err() == io.EOF {
				return "", Page{}, false, false, nil
			}
			return "", Page{}, false, false, z.Err()
		case html.StartTagToken, html.SelfClosingTagToken:
			t := z.Token()
			if !isAutolinkScript(t) {
				continue
			}
			terms, _ = attr(t, "data-terms")
			scope, _ := attr(t, "data-scope")
			if err := json.Unmarshal([]byte(scope), &p.Scope); err != nil {
				return "", Page{}, false, false, err
			}
			p.Module, _ = attr(t, "data-module")
			p.Self, _ = attr(t, "data-self")
			_, done = attr(t, StaticAttr)
			return terms, p, done, true, nil
		}
	}
}

// LinkPage links the names in the page's .article-body and marks its
// autolink script with data-static. Bytes outside the rewritten text and that
// attribute are copied unchanged, so a page with no name in its body differs
// from its input only by data-static. A page without a <div class=article-body>
// (the container layouts/_default/single.html writes) is not marked, so the
// page script still links it in the browser; ScriptInfo on the output reports
// such a page as not done.
func LinkPage(src []byte, l *Linker) ([]byte, int, error) {
	return rewrite(src, l, false)
}

// LinkFragment links the names in an HTML fragment (an RSS item's content),
// treating the whole fragment as article body.
func LinkFragment(src []byte, l *Linker) ([]byte, int, error) {
	return rewrite(src, l, true)
}

type frame struct {
	tag  string
	skip bool
}

func rewrite(src []byte, l *Linker, fragment bool) ([]byte, int, error) {
	z := html.NewTokenizer(bytes.NewReader(src))
	var out bytes.Buffer
	out.Grow(len(src) + len(src)/8)
	var stack []frame
	inBody := fragment
	sawBody := false
	markAt := -1 // offset in out of the autolink "<script" to mark
	links := 0
	skipping := func() bool {
		for _, f := range stack {
			if f.skip {
				return true
			}
		}
		return false
	}
	for {
		tt := z.Next()
		if tt == html.ErrorToken {
			if z.Err() == io.EOF {
				b := out.Bytes()
				if markAt >= 0 && sawBody {
					marked := make([]byte, 0, len(b)+len(StaticAttr)+1)
					marked = append(marked, b[:markAt]...)
					marked = append(marked, "<script "+StaticAttr...)
					b = append(marked, b[markAt+len("<script"):]...)
				}
				return b, links, nil
			}
			return nil, 0, z.Err()
		}
		raw := append([]byte(nil), z.Raw()...)
		switch tt {
		case html.StartTagToken:
			t := z.Token()
			switch {
			case !fragment && isAutolinkScript(t):
				if _, done := attr(t, StaticAttr); !done {
					markAt = out.Len()
				}
			case !inBody:
				if t.Data == "div" && hasClass(t, "article-body") {
					inBody = true
					sawBody = true
					stack = []frame{{tag: "div"}}
				}
			case !voidTags[t.Data]:
				stack = append(stack, frame{tag: t.Data, skip: skips(t)})
			}
		case html.EndTagToken:
			if !inBody {
				break
			}
			name, _ := z.TagName()
			for i := len(stack) - 1; i >= 0; i-- {
				if stack[i].tag == string(name) {
					stack = stack[:i]
					break
				}
			}
			if !fragment && len(stack) == 0 {
				inBody = false
			}
		case html.TextToken:
			if !inBody || skipping() {
				break
			}
			text := z.Token().Data
			if strings.TrimSpace(text) == "" {
				break
			}
			if linked, n := l.LinkText(text); n > 0 {
				raw = []byte(linked)
				links += n
			}
		}
		out.Write(raw)
	}
}
