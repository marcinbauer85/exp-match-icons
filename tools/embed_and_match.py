#!/usr/bin/env python3
"""
Compute DINOv2 embeddings for all rasterized icons and find the top-N
visually closest icons in fluent/tabler/ph for each MDI source icon.

Outputs tools/matches.json — a dict keyed by MDI slug with ranked candidates.

Usage:
  python3 tools/embed_and_match.py [--top 5]
"""

import argparse
import json
import os
import sys
from pathlib import Path
import numpy as np

TOOLS = Path(__file__).parent
ICONS = TOOLS / "icons"
OUT = TOOLS / "matches.json"

SETS = ["fluent", "tabler", "ph"]
IMG_SIZE = 224  # DINOv2 input size

try:
    import torch
    from transformers import AutoImageProcessor, AutoModel
    from PIL import Image
except ImportError as e:
    sys.exit(f"Missing dep: {e}. Run: pip3 install torch transformers pillow")


def load_images(prefix: str) -> tuple[list[str], list[Image.Image]]:
    d = ICONS / prefix
    if not d.exists():
        return [], []
    paths = sorted(d.glob("*.png"))
    slugs, imgs = [], []
    for p in paths:
        try:
            img = Image.open(p).convert("RGB").resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)
            slugs.append(p.stem)
            imgs.append(img)
        except Exception:
            pass
    return slugs, imgs


def embed_images(
    imgs: list[Image.Image],
    processor,
    model,
    device: str,
    batch_size: int = 64,
) -> np.ndarray:
    all_vecs = []
    for i in range(0, len(imgs), batch_size):
        batch = imgs[i : i + batch_size]
        inputs = processor(images=batch, return_tensors="pt").to(device)
        with torch.no_grad():
            out = model(**inputs)
        # CLS token from last hidden state
        vecs = out.last_hidden_state[:, 0, :].cpu().float().numpy()
        all_vecs.append(vecs)
        print(f"  embedded {min(i + batch_size, len(imgs))}/{len(imgs)}", end="\r", flush=True)
    print()
    return np.vstack(all_vecs)


def cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """a: (1, D)  b: (N, D)  → (N,)"""
    a = a / (np.linalg.norm(a) + 1e-8)
    b = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-8)
    return (b @ a.T).squeeze()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--top", type=int, default=5, help="Top-N candidates per set")
    parser.add_argument("--model", default="facebook/dinov2-small", help="HF model ID")
    args = parser.parse_args()

    device = "mps" if torch.backends.mps.is_available() else "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device: {device}")
    print(f"Loading model {args.model}…")
    processor = AutoImageProcessor.from_pretrained(args.model)
    model = AutoModel.from_pretrained(args.model).to(device).eval()

    # Load and embed MDI source icons
    print("\nLoading MDI icons…")
    mdi_slugs, mdi_imgs = load_images("mdi")
    if not mdi_slugs:
        sys.exit("No MDI icons found. Run fetch_svgs.py first.")
    print(f"  {len(mdi_slugs)} MDI icons")
    print("Embedding MDI…")
    mdi_vecs = embed_images(mdi_imgs, processor, model, device)

    # Load and embed each target set
    set_data = {}
    for prefix in SETS:
        print(f"\nLoading {prefix}…")
        slugs, imgs = load_images(prefix)
        if not slugs:
            print(f"  No icons found for {prefix}, skipping.")
            continue
        print(f"  {len(slugs)} icons")
        print(f"Embedding {prefix}…")
        vecs = embed_images(imgs, processor, model, device)
        set_data[prefix] = (slugs, vecs)

    # Find top-N matches for each MDI icon in each set
    print("\nFinding nearest neighbors…")
    matches = {}
    for i, mdi_slug in enumerate(mdi_slugs):
        entry = {}
        for prefix, (slugs, vecs) in set_data.items():
            sims = cosine_sim(mdi_vecs[i : i + 1], vecs)
            top_idx = np.argsort(sims)[::-1][: args.top]
            entry[prefix] = [
                {"icon": f"{prefix}:{slugs[j]}", "score": float(sims[j])}
                for j in top_idx
            ]
        matches[mdi_slug] = entry

    OUT.write_text(json.dumps(matches, indent=2))
    print(f"\nWrote {len(matches)} entries to {OUT}")


if __name__ == "__main__":
    main()
