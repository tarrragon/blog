package autolinkhtml

import (
	"bytes"
	"html"
	"net/url"
	"strings"
)

// LinkFeed links the names in each RSS item's <content:encoded> and returns
// the feed, the number of items changed and the number of links made.
// linkerFor resolves an item's <link> to the Linker of the page its built
// HTML declared, or nil when that page does not auto-link. The content may be
// a CDATA section (what hugo writes) or escaped text. Bytes outside the
// rewritten content are copied unchanged.
func LinkFeed(src []byte, linkerFor func(link string) *Linker) ([]byte, int, int, error) {
	const (
		itemOpen, itemClose       = "<item>", "</item>"
		linkOpen, linkClose       = "<link>", "</link>"
		contentOpen, contentClose = "<content:encoded>", "</content:encoded>"
		cdataOpen, cdataClose     = "<![CDATA[", "]]>"
	)
	var out bytes.Buffer
	s := string(src)
	items, links := 0, 0
	for {
		i := strings.Index(s, itemOpen)
		if i < 0 {
			out.WriteString(s)
			return out.Bytes(), items, links, nil
		}
		j := strings.Index(s[i:], itemClose)
		if j < 0 {
			out.WriteString(s)
			return out.Bytes(), items, links, nil
		}
		j += i + len(itemClose)
		out.WriteString(s[:i])
		item := s[i:j]
		s = s[j:]

		l := linkerFor(between(item, linkOpen, linkClose))
		ci := strings.Index(item, contentOpen)
		ce := strings.Index(item, contentClose)
		if l == nil || ci < 0 || ce < ci {
			out.WriteString(item)
			continue
		}
		l = l.forFeed()
		body := item[ci+len(contentOpen) : ce]
		var linked string
		var n int
		if strings.HasPrefix(body, cdataOpen) && strings.HasSuffix(body, cdataClose) {
			frag, k, err := LinkFragment([]byte(body[len(cdataOpen):len(body)-len(cdataClose)]), l)
			if err != nil {
				return nil, 0, 0, err
			}
			linked, n = cdataOpen+string(frag)+cdataClose, k
		} else {
			frag, k, err := LinkFragment([]byte(html.UnescapeString(body)), l)
			if err != nil {
				return nil, 0, 0, err
			}
			linked, n = escapeXML(string(frag)), k
		}
		if n == 0 {
			out.WriteString(item)
			continue
		}
		items++
		links += n
		out.WriteString(item[:ci+len(contentOpen)])
		out.WriteString(linked)
		out.WriteString(item[ce:])
	}
}

func between(s, open, close string) string {
	i := strings.Index(s, open)
	if i < 0 {
		return ""
	}
	s = s[i+len(open):]
	j := strings.Index(s, close)
	if j < 0 {
		return ""
	}
	return strings.TrimSpace(s[:j])
}

func escapeXML(s string) string {
	return strings.NewReplacer("&", "&amp;", "<", "&lt;", ">", "&gt;").Replace(s)
}

// PagePath returns the URL path of an item link ("/blog/backend/x/" for
// "https://example.org/blog/backend/x/"), the key the command's page index
// uses; it is "" when the link does not parse.
func PagePath(link string) string {
	u, err := url.Parse(link)
	if err != nil {
		return ""
	}
	return u.Path
}

// BasePath returns the site's base path ("/blog/") from the URL of the
// dictionary, which hugo publishes as <base path>js/<name>; ok is false when
// the URL has no /js/ segment.
func BasePath(termsURL string) (base, file string, ok bool) {
	p := termsURL
	if u, err := url.Parse(termsURL); err == nil {
		p = u.Path
	}
	i := strings.LastIndex(p, "/js/")
	if i < 0 {
		return "", "", false
	}
	return p[:i+1], p[i+1:], true
}
