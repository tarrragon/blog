package chunk

import (
	"regexp"
	"strings"
)

var (
	frontmatterRe = regexp.MustCompile(`(?s)^---\n.*?\n---\n`)
	blankLineRe   = regexp.MustCompile(`\n\s*\n`)
)

type Chunk struct {
	Text     string
	ChunkIdx int
}

func Markdown(text string, softTokenCap int) []Chunk {
	text = frontmatterRe.ReplaceAllString(text, "")
	paragraphs := blankLineRe.Split(text, -1)

	var chunks []Chunk
	var buf []string
	bufLen := 0

	for _, p := range paragraphs {
		p = strings.TrimSpace(p)
		if p == "" {
			continue
		}
		pLen := estimateTokens(p)
		if len(buf) > 0 && bufLen+pLen > softTokenCap {
			chunks = append(chunks, Chunk{
				Text:     strings.Join(buf, "\n\n"),
				ChunkIdx: len(chunks),
			})
			buf = buf[:0]
			bufLen = 0
		}
		buf = append(buf, p)
		bufLen += pLen
	}
	if len(buf) > 0 {
		chunks = append(chunks, Chunk{
			Text:     strings.Join(buf, "\n\n"),
			ChunkIdx: len(chunks),
		})
	}
	return chunks
}

func estimateTokens(s string) int {
	n := 0
	for _, r := range s {
		n++
		if r >= 0x4E00 {
			n++
		}
	}
	return n / 2
}
