package store

import (
	"encoding/binary"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
)

type ChunkMeta struct {
	Source   string   `json:"source"`
	Title    string   `json:"title"`
	Section  string   `json:"section"`
	Tags     []string `json:"tags"`
	ChunkIdx int      `json:"chunk_idx"`
}

type Record struct {
	Meta      ChunkMeta
	Text      string
	Embedding []float32
}

type Index struct {
	Dim     int          `json:"dim"`
	Count   int          `json:"count"`
	Records []RecordMeta `json:"records"`
}

type RecordMeta struct {
	ChunkMeta
	Text string `json:"text"`
}

func Save(dir string, records []Record) error {
	if len(records) == 0 {
		return fmt.Errorf("no records to save")
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}

	dim := len(records[0].Embedding)

	vecPath := filepath.Join(dir, "vectors.bin")
	f, err := os.Create(vecPath)
	if err != nil {
		return err
	}
	defer f.Close()

	buf := make([]byte, 4)
	for _, r := range records {
		if len(r.Embedding) != dim {
			return fmt.Errorf("inconsistent dim: expected %d, got %d", dim, len(r.Embedding))
		}
		for _, v := range r.Embedding {
			binary.LittleEndian.PutUint32(buf, math.Float32bits(v))
			if _, err := f.Write(buf); err != nil {
				return err
			}
		}
	}

	idx := Index{
		Dim:     dim,
		Count:   len(records),
		Records: make([]RecordMeta, len(records)),
	}
	for i, r := range records {
		idx.Records[i] = RecordMeta{
			ChunkMeta: r.Meta,
			Text:      r.Text,
		}
	}

	metaPath := filepath.Join(dir, "index.json")
	mf, err := os.Create(metaPath)
	if err != nil {
		return err
	}
	defer mf.Close()

	enc := json.NewEncoder(mf)
	enc.SetIndent("", "  ")
	return enc.Encode(idx)
}

func Load(dir string) ([]Record, error) {
	metaPath := filepath.Join(dir, "index.json")
	mf, err := os.Open(metaPath)
	if err != nil {
		return nil, err
	}
	defer mf.Close()

	var idx Index
	if err := json.NewDecoder(mf).Decode(&idx); err != nil {
		return nil, err
	}

	vecPath := filepath.Join(dir, "vectors.bin")
	vf, err := os.Open(vecPath)
	if err != nil {
		return nil, err
	}
	defer vf.Close()

	records := make([]Record, idx.Count)
	buf := make([]byte, 4)
	for i := range records {
		vec := make([]float32, idx.Dim)
		for j := range vec {
			if _, err := vf.Read(buf); err != nil {
				return nil, fmt.Errorf("read vector %d dim %d: %w", i, j, err)
			}
			vec[j] = math.Float32frombits(binary.LittleEndian.Uint32(buf))
		}
		records[i] = Record{
			Meta:      idx.Records[i].ChunkMeta,
			Text:      idx.Records[i].Text,
			Embedding: vec,
		}
	}
	return records, nil
}
