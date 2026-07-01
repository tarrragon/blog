#!/usr/bin/env python3
"""
Benchmark: Go flat file vs Python sqlite-vec vs Python FAISS
on the same corpus (blogsearch index).

Reads the Go tool's index (.blogsearch/) to get embeddings + metadata,
then benchmarks sqlite-vec and FAISS ingest + query on the same data.

Usage:
    uv run bench.py [--index .blogsearch] [--queries N]
"""
import argparse
import json
import os
import struct
import sys
import time
import subprocess

def load_go_index(index_dir):
    """Load vectors and metadata from Go blogsearch index."""
    meta_path = os.path.join(index_dir, "meta.json")
    vec_path = os.path.join(index_dir, "vectors.bin")

    with open(meta_path) as f:
        idx = json.load(f)

    dim = idx["dim"]
    count = idx["count"]

    with open(vec_path, "rb") as f:
        raw = f.read()

    vectors = struct.unpack(f"<{count * dim}f", raw)
    import numpy as np
    vectors = np.array(vectors, dtype=np.float32).reshape(count, dim)

    return idx["metas"], vectors, dim


def bench_go_flatfile(index_dir, query_text, n_queries):
    """Benchmark Go flat file query by calling the binary."""
    times = []
    for _ in range(n_queries):
        start = time.perf_counter()
        subprocess.run(
            ["./bin/blogsearch", "query", "-index", index_dir, query_text],
            capture_output=True, text=True,
        )
        elapsed = time.perf_counter() - start
        times.append(elapsed)
    return times


def bench_sqlite_vec(metas, vectors, dim, query_vec, n_queries):
    """Benchmark sqlite-vec ingest + query."""
    import sqlite3
    import sqlite_vec

    db_path = "/tmp/blogsearch_bench.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    conn = sqlite3.connect(db_path)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)

    # Ingest
    ingest_start = time.perf_counter()

    conn.execute(f"""
        CREATE VIRTUAL TABLE vec_chunks USING vec0(
            embedding float[{dim}]
        )
    """)
    conn.execute("""
        CREATE TABLE chunk_meta (
            id INTEGER PRIMARY KEY,
            source TEXT,
            title TEXT,
            section TEXT
        )
    """)

    for i in range(len(metas)):
        vec_bytes = vectors[i].tobytes()
        conn.execute("INSERT INTO vec_chunks(rowid, embedding) VALUES (?, ?)",
                      (i, vec_bytes))
        m = metas[i]
        conn.execute("INSERT INTO chunk_meta VALUES (?, ?, ?, ?)",
                      (i, m.get("source", ""), m.get("title", ""), m.get("section", "")))

    conn.commit()
    ingest_time = time.perf_counter() - ingest_start

    # Query
    query_bytes = query_vec.tobytes()
    times = []
    for _ in range(n_queries):
        start = time.perf_counter()
        results = conn.execute("""
            SELECT rowid, distance
            FROM vec_chunks
            WHERE embedding MATCH ?
            ORDER BY distance
            LIMIT 5
        """, (query_bytes,)).fetchall()
        elapsed = time.perf_counter() - start
        times.append(elapsed)

    db_size = os.path.getsize(db_path)
    conn.close()
    os.remove(db_path)

    return ingest_time, times, db_size


def bench_faiss(vectors, dim, query_vec, n_queries):
    """Benchmark FAISS flat index (brute-force) and HNSW."""
    import faiss

    results = {}

    # --- Flat (brute-force, exact) ---
    ingest_start = time.perf_counter()
    index_flat = faiss.IndexFlatIP(dim)
    faiss.normalize_L2(vectors)
    index_flat.add(vectors)
    ingest_flat = time.perf_counter() - ingest_start

    qvec = query_vec.copy().reshape(1, -1)
    faiss.normalize_L2(qvec)

    times_flat = []
    for _ in range(n_queries):
        start = time.perf_counter()
        _, _ = index_flat.search(qvec, 5)
        elapsed = time.perf_counter() - start
        times_flat.append(elapsed)

    results["faiss_flat"] = {
        "ingest": ingest_flat,
        "queries": times_flat,
    }

    # --- HNSW ---
    ingest_start = time.perf_counter()
    index_hnsw = faiss.IndexHNSWFlat(dim, 32)
    index_hnsw.hnsw.efConstruction = 200
    index_hnsw.hnsw.efSearch = 64
    index_hnsw.add(vectors)
    ingest_hnsw = time.perf_counter() - ingest_start

    times_hnsw = []
    for _ in range(n_queries):
        start = time.perf_counter()
        _, _ = index_hnsw.search(qvec, 5)
        elapsed = time.perf_counter() - start
        times_hnsw.append(elapsed)

    results["faiss_hnsw"] = {
        "ingest": ingest_hnsw,
        "queries": times_hnsw,
    }

    return results


def get_query_embedding(query_text):
    """Get embedding from Ollama."""
    import urllib.request
    body = json.dumps({"model": "nomic-embed-text", "prompt": query_text}).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/embeddings",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    import numpy as np
    with urllib.request.urlopen(req, timeout=60) as resp:
        r = json.loads(resp.read())
        return np.array(r["embedding"], dtype=np.float32)


def fmt_ms(seconds):
    return f"{seconds * 1000:.1f}ms"


def fmt_mb(bytes_val):
    return f"{bytes_val / (1024 * 1024):.1f}MB"


def main():
    parser = argparse.ArgumentParser(description="Blogsearch storage benchmark")
    parser.add_argument("--index", default=".blogsearch", help="Go blogsearch index dir")
    parser.add_argument("--queries", type=int, default=5, help="Number of query iterations")
    parser.add_argument("--query-text", default="RAG storage 選型", help="Query text")
    args = parser.parse_args()

    print(f"Loading Go index from {args.index}/ ...")
    metas, vectors, dim = load_go_index(args.index)
    print(f"  {len(metas)} chunks, {dim} dim\n")

    print(f"Getting query embedding for: {args.query_text!r}")
    query_vec = get_query_embedding(args.query_text)
    print()

    # --- Go flat file ---
    print("=== Go + flat file (blogsearch) ===")
    go_times = bench_go_flatfile(args.index, args.query_text, args.queries)
    go_median = sorted(go_times)[len(go_times) // 2]

    vec_size = os.path.getsize(os.path.join(args.index, "vectors.bin"))
    meta_size = os.path.getsize(os.path.join(args.index, "meta.json"))
    text_size = os.path.getsize(os.path.join(args.index, "texts.bin"))
    print(f"  query (median of {args.queries}): {fmt_ms(go_median)}")
    print(f"  index size: {fmt_mb(vec_size + meta_size + text_size)}")
    print(f"  dependencies: Go binary + Ollama")
    print()

    # --- sqlite-vec ---
    print("=== Python + sqlite-vec ===")
    sv_ingest, sv_times, sv_size = bench_sqlite_vec(metas, vectors, dim, query_vec, args.queries)
    sv_median = sorted(sv_times)[len(sv_times) // 2]
    print(f"  ingest: {fmt_ms(sv_ingest)}")
    print(f"  query (median of {args.queries}): {fmt_ms(sv_median)}")
    print(f"  index size: {fmt_mb(sv_size)}")
    print(f"  dependencies: Python + sqlite-vec")
    print()

    # --- FAISS ---
    print("=== Python + FAISS ===")
    faiss_results = bench_faiss(vectors.copy(), dim, query_vec, args.queries)

    for variant, data in faiss_results.items():
        median = sorted(data["queries"])[len(data["queries"]) // 2]
        print(f"  [{variant}]")
        print(f"    ingest: {fmt_ms(data['ingest'])}")
        print(f"    query (median of {args.queries}): {fmt_ms(median)}")
    print(f"  dependencies: Python + faiss-cpu + numpy")
    print()

    # --- Summary table ---
    print("=" * 60)
    print("Summary (query median, same 24K chunks / 768 dim):")
    print(f"  Go flat file:      {fmt_ms(go_median):>10}")
    print(f"  sqlite-vec:        {fmt_ms(sv_median):>10}")
    ff_median = sorted(faiss_results["faiss_flat"]["queries"])[args.queries // 2]
    fh_median = sorted(faiss_results["faiss_hnsw"]["queries"])[args.queries // 2]
    print(f"  FAISS flat:        {fmt_ms(ff_median):>10}")
    print(f"  FAISS HNSW:        {fmt_ms(fh_median):>10}")


if __name__ == "__main__":
    main()
