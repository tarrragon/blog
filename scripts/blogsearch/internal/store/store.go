package store

import (
	"encoding/binary"
	"encoding/json"
	"fmt"
	"math"
	"os"
	"path/filepath"
	"unsafe"
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
	Dim   int         `json:"dim"`
	Count int         `json:"count"`
	Metas []ChunkMeta `json:"metas"`
}

func Save(dir string, records []Record) error {
	if len(records) == 0 {
		return fmt.Errorf("no records to save")
	}
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return err
	}

	dim := len(records[0].Embedding)

	if err := saveVectors(filepath.Join(dir, "vectors.bin"), records, dim); err != nil {
		return err
	}
	if err := saveTexts(filepath.Join(dir, "texts.bin"), records); err != nil {
		return err
	}
	return saveMeta(filepath.Join(dir, "meta.json"), records, dim)
}

func saveVectors(path string, records []Record, dim int) error {
	buf := make([]byte, len(records)*dim*4)
	off := 0
	for _, r := range records {
		if len(r.Embedding) != dim {
			return fmt.Errorf("inconsistent dim: expected %d, got %d", dim, len(r.Embedding))
		}
		for _, v := range r.Embedding {
			binary.LittleEndian.PutUint32(buf[off:], math.Float32bits(v))
			off += 4
		}
	}
	return os.WriteFile(path, buf, 0o644)
}

func saveTexts(path string, records []Record) error {
	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	lenBuf := make([]byte, 4)
	for _, r := range records {
		textBytes := []byte(r.Text)
		binary.LittleEndian.PutUint32(lenBuf, uint32(len(textBytes)))
		if _, err := f.Write(lenBuf); err != nil {
			return err
		}
		if _, err := f.Write(textBytes); err != nil {
			return err
		}
	}
	return nil
}

func saveMeta(path string, records []Record, dim int) error {
	idx := Index{
		Dim:   dim,
		Count: len(records),
		Metas: make([]ChunkMeta, len(records)),
	}
	for i, r := range records {
		idx.Metas[i] = r.Meta
	}

	f, err := os.Create(path)
	if err != nil {
		return err
	}
	defer f.Close()

	enc := json.NewEncoder(f)
	enc.SetIndent("", "  ")
	return enc.Encode(idx)
}

// LoadForSearch loads vectors and metadata for search (no text).
// Text is loaded separately via LoadTexts for top-K results only.
func LoadForSearch(dir string) (metas []ChunkMeta, vectors []float32, dim int, err error) {
	metaPath := filepath.Join(dir, "meta.json")
	metaBytes, err := os.ReadFile(metaPath)
	if err != nil {
		return nil, nil, 0, err
	}

	var idx Index
	if err := json.Unmarshal(metaBytes, &idx); err != nil {
		return nil, nil, 0, err
	}

	vecBytes, err := os.ReadFile(filepath.Join(dir, "vectors.bin"))
	if err != nil {
		return nil, nil, 0, err
	}

	expected := idx.Count * idx.Dim * 4
	if len(vecBytes) != expected {
		return nil, nil, 0, fmt.Errorf("vectors.bin size %d != expected %d", len(vecBytes), expected)
	}

	vectors = bytesToFloat32(vecBytes)
	return idx.Metas, vectors, idx.Dim, nil
}

// LoadTexts reads the texts.bin file and returns text for given record indices.
func LoadTexts(dir string, indices []int) (map[int]string, error) {
	f, err := os.Open(filepath.Join(dir, "texts.bin"))
	if err != nil {
		return nil, err
	}
	defer f.Close()

	want := make(map[int]bool, len(indices))
	maxIdx := -1
	for _, i := range indices {
		want[i] = true
		if i > maxIdx {
			maxIdx = i
		}
	}

	result := make(map[int]string, len(indices))
	lenBuf := make([]byte, 4)
	for i := 0; i <= maxIdx; i++ {
		if _, err := f.Read(lenBuf); err != nil {
			return nil, fmt.Errorf("read text len %d: %w", i, err)
		}
		textLen := binary.LittleEndian.Uint32(lenBuf)

		if want[i] {
			textBuf := make([]byte, textLen)
			if _, err := f.Read(textBuf); err != nil {
				return nil, fmt.Errorf("read text %d: %w", i, err)
			}
			result[i] = string(textBuf)
		} else {
			if _, err := f.Seek(int64(textLen), 1); err != nil {
				return nil, fmt.Errorf("skip text %d: %w", i, err)
			}
		}
	}
	return result, nil
}

// Load loads all records (vectors + metadata + text). Used by status command.
func Load(dir string) ([]Record, error) {
	metas, vectors, dim, err := LoadForSearch(dir)
	if err != nil {
		return nil, err
	}

	allIndices := make([]int, len(metas))
	for i := range allIndices {
		allIndices[i] = i
	}
	texts, err := LoadTexts(dir, allIndices)
	if err != nil {
		return nil, err
	}

	records := make([]Record, len(metas))
	for i := range records {
		vecStart := i * dim
		records[i] = Record{
			Meta:      metas[i],
			Text:      texts[i],
			Embedding: vectors[vecStart : vecStart+dim],
		}
	}
	return records, nil
}

func bytesToFloat32(b []byte) []float32 {
	n := len(b) / 4
	// Safe reinterpret: []byte with len multiple of 4 → []float32
	return unsafe.Slice((*float32)(unsafe.Pointer(&b[0])), n)
}
