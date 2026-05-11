#!/usr/bin/env python3
"""
Minimal ComfyUI test: POST a SDXL workflow to /prompt, poll /history,
download the generated image.

Usage:
    python3 generate.py [--prompt TEXT] [--steps N]
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

BASE = "http://127.0.0.1:8188"


def http_post_json(path: str, body: dict) -> dict:
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def http_get_json(path: str) -> dict:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=30) as resp:
        return json.loads(resp.read())


def http_get_bytes(path: str) -> bytes:
    with urllib.request.urlopen(f"{BASE}{path}", timeout=60) as resp:
        return resp.read()


def build_workflow(prompt_text: str, neg_text: str, steps: int) -> dict:
    return {
        "3": {
            "inputs": {
                "seed": 42,
                "steps": steps,
                "cfg": 7.0,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            },
            "class_type": "KSampler",
        },
        "4": {
            "inputs": {"ckpt_name": "sd_xl_base_1.0.safetensors"},
            "class_type": "CheckpointLoaderSimple",
        },
        "5": {
            "inputs": {"width": 1024, "height": 1024, "batch_size": 1},
            "class_type": "EmptyLatentImage",
        },
        "6": {
            "inputs": {"text": prompt_text, "clip": ["4", 1]},
            "class_type": "CLIPTextEncode",
        },
        "7": {
            "inputs": {"text": neg_text, "clip": ["4", 1]},
            "class_type": "CLIPTextEncode",
        },
        "8": {
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]},
            "class_type": "VAEDecode",
        },
        "9": {
            "inputs": {"filename_prefix": "comfyui-test", "images": ["8", 0]},
            "class_type": "SaveImage",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--prompt",
        default="a photograph of an orange cat sitting on a wooden chair, soft natural lighting, detailed fur",
    )
    ap.add_argument("--neg", default="blurry, low quality, distorted, watermark")
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--out", default="/tmp/comfyui-test-output.png")
    args = ap.parse_args()

    client_id = str(uuid.uuid4())
    workflow = build_workflow(args.prompt, args.neg, args.steps)

    print(f"[+] POST /prompt (client_id={client_id[:8]})", file=sys.stderr)
    start = time.time()
    resp = http_post_json("/prompt", {"prompt": workflow, "client_id": client_id})
    prompt_id = resp["prompt_id"]
    print(f"    prompt_id={prompt_id}", file=sys.stderr)

    print("[+] polling /history ...", file=sys.stderr)
    while True:
        time.sleep(2)
        history = http_get_json(f"/history/{prompt_id}")
        if prompt_id in history:
            elapsed = time.time() - start
            print(f"    done in {elapsed:.1f}s", file=sys.stderr)
            outputs = history[prompt_id].get("outputs", {})
            break
        elapsed = time.time() - start
        if elapsed > 600:
            print(f"    timeout after {elapsed:.0f}s", file=sys.stderr)
            sys.exit(1)
        print(f"    {elapsed:.0f}s elapsed...", file=sys.stderr)

    save_node = outputs.get("9", {})
    images = save_node.get("images", [])
    if not images:
        print("    no images in output, dumping full result:", file=sys.stderr)
        print(json.dumps(history[prompt_id], indent=2), file=sys.stderr)
        sys.exit(1)

    img = images[0]
    qs = urllib.parse.urlencode(
        {"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")}
    )
    print(f"[+] downloading /view?{qs}", file=sys.stderr)
    blob = http_get_bytes(f"/view?{qs}")

    Path(args.out).write_bytes(blob)
    print(f"[+] saved {len(blob)} bytes to {args.out}", file=sys.stderr)
    print(args.out)


if __name__ == "__main__":
    main()
