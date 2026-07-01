package embed

import (
	"bytes"
	"encoding/json"
	"fmt"
	"net/http"
	"time"
)

var (
	BaseURL = "http://localhost:11434"
	Model   = "nomic-embed-text"
	client  = &http.Client{Timeout: 120 * time.Second}
)

type request struct {
	Model  string `json:"model"`
	Prompt string `json:"prompt"`
}

type response struct {
	Embedding []float64 `json:"embedding"`
}

func Text(text string) ([]float32, error) {
	body, err := json.Marshal(request{Model: Model, Prompt: text})
	if err != nil {
		return nil, err
	}

	resp, err := client.Post(BaseURL+"/api/embeddings", "application/json", bytes.NewReader(body))
	if err != nil {
		return nil, fmt.Errorf("ollama embed: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("ollama embed: status %d", resp.StatusCode)
	}

	var r response
	if err := json.NewDecoder(resp.Body).Decode(&r); err != nil {
		return nil, err
	}

	out := make([]float32, len(r.Embedding))
	for i, v := range r.Embedding {
		out[i] = float32(v)
	}
	return out, nil
}
