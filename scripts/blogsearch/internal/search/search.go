package search

import (
	"math"
	"sort"

	"blog/scripts/blogsearch/internal/store"
)

type Result struct {
	Record store.Record
	Score  float64
}

func TopK(records []store.Record, query []float32, k int) []Result {
	results := make([]Result, len(records))
	for i, r := range records {
		results[i] = Result{
			Record: r,
			Score:  cosine(query, r.Embedding),
		}
	}
	sort.Slice(results, func(i, j int) bool {
		return results[i].Score > results[j].Score
	})
	if k > len(results) {
		k = len(results)
	}
	return results[:k]
}

func cosine(a, b []float32) float64 {
	var dot, normA, normB float64
	for i := range a {
		ai, bi := float64(a[i]), float64(b[i])
		dot += ai * bi
		normA += ai * ai
		normB += bi * bi
	}
	denom := math.Sqrt(normA) * math.Sqrt(normB)
	if denom == 0 {
		return 0
	}
	return dot / denom
}
