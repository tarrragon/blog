package search

import (
	"math"
	"sort"

	"blog/scripts/blogsearch/internal/store"
)

type Result struct {
	Index int
	Meta  store.ChunkMeta
	Score float64
}

// TopK finds the top-K most similar records using brute-force cosine similarity.
// vectors is a flat slice of all embeddings (n * dim float32 values).
func TopK(metas []store.ChunkMeta, vectors []float32, dim int, query []float32, k int) []Result {
	n := len(metas)
	results := make([]Result, n)

	for i := 0; i < n; i++ {
		vecStart := i * dim
		results[i] = Result{
			Index: i,
			Meta:  metas[i],
			Score: cosine(query, vectors[vecStart:vecStart+dim]),
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
