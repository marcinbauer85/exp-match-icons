#!/usr/bin/env python3
"""
Fetch icons from Iconify CDN and rasterize them to 224x224 PNG files.

Set filtering (to keep candidate pool manageable):
  fluent  → -24-regular and -24-filled variants only  (~4900 icons)
  tabler  → all icons                                 (~6100 icons)
  ph      → base slugs only (no -bold/-fill/etc.)     (~1500 icons)
  mdi     → only icons present in current mappings    (~380 icons)

Output:  tools/icons/{prefix}/{slug}.png
"""

import json
import os
import re
import sys
import time
import threading
import urllib.request
import urllib.error
from pathlib import Path
from io import BytesIO

try:
    import cairosvg
    from PIL import Image
except ImportError as e:
    sys.exit(f"Missing dep: {e}. Run: pip3 install cairosvg pillow")

ROOT = Path(__file__).parent.parent
TOOLS = Path(__file__).parent
OUT_DIR = TOOLS / "icons"
INDEX = ROOT / "index.html"

API_BASE = "https://api.iconify.design"
SIZE = 224
CONCURRENCY = 24

PH_SUFFIXES = {"-bold", "-duotone", "-fill", "-light", "-thin"}


# ── helpers ───────────────────────────────────────────────────────────────────

def get_json(url: str, retries: int = 4) -> dict:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "icon-matcher/1.0"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt)


def get_svg_bytes(url: str, retries: int = 3) -> bytes | None:
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "icon-matcher/1.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if attempt == retries - 1:
                return None
            time.sleep(1.5 ** attempt)
        except Exception:
            if attempt == retries - 1:
                return None
            time.sleep(1.5 ** attempt)
    return None


def svg_to_png(svg_bytes: bytes, size: int = SIZE) -> bytes | None:
    try:
        return cairosvg.svg2png(
            bytestring=svg_bytes,
            output_width=size,
            output_height=size,
            background_color="white",
        )
    except Exception:
        return None


def padded_png(png_bytes: bytes, size: int = SIZE) -> bytes:
    img = Image.open(BytesIO(png_bytes)).convert("RGBA")
    bg = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    off = ((size - img.width) // 2, (size - img.height) // 2)
    bg.paste(img, off, img)
    buf = BytesIO()
    bg.convert("RGB").save(buf, "PNG")
    return buf.getvalue()


def fetch_and_save(prefix: str, slug: str, out_path: Path) -> bool:
    if out_path.exists():
        return True
    url = f"{API_BASE}/{prefix}/{slug}.svg?width={SIZE}&height={SIZE}&color=%23000000"
    svg = get_svg_bytes(url)
    if not svg:
        return False
    png = svg_to_png(svg)
    if not png:
        return False
    out_path.write_bytes(padded_png(png))
    return True


# ── icon list fetchers ────────────────────────────────────────────────────────

def get_collection_icons(prefix: str) -> list[str]:
    url = f"{API_BASE}/collection?prefix={prefix}"
    print(f"  Fetching icon list for {prefix}…")
    data = get_json(url)
    return data.get("uncategorized", [])


def fluent_slugs() -> list[str]:
    icons = get_collection_icons("fluent")
    return [i for i in icons if i.endswith("-24-regular") or i.endswith("-24-filled")]


def tabler_slugs() -> list[str]:
    return get_collection_icons("tabler")


def ph_slugs() -> list[str]:
    icons = get_collection_icons("ph")
    return [i for i in icons if not any(i.endswith(s) for s in PH_SUFFIXES)]


def mdi_slugs_from_html() -> list[str]:
    html = INDEX.read_text()
    return sorted(set(re.findall(r'mat:\s*"mdi:([^"]+)"', html)))


# ── batch fetch ───────────────────────────────────────────────────────────────

def fetch_set(prefix: str, slugs: list[str]):
    out = OUT_DIR / prefix
    out.mkdir(parents=True, exist_ok=True)

    total = len(slugs)
    done = [0]
    failed = []
    lock = threading.Lock()

    def worker(batch):
        for slug in batch:
            ok = fetch_and_save(prefix, slug, out / f"{slug}.png")
            with lock:
                done[0] += 1
                if not ok:
                    failed.append(slug)
                if done[0] % 100 == 0 or done[0] == total:
                    pct = done[0] * 100 // total
                    print(f"    {prefix}: {done[0]}/{total} ({pct}%)", end="\r", flush=True)

    n = CONCURRENCY
    batch_size = max(1, (total + n - 1) // n)
    batches = [slugs[i : i + batch_size] for i in range(0, total, batch_size)]
    threads = [threading.Thread(target=worker, args=(b,), daemon=True) for b in batches]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print(f"\n    {prefix}: {total - len(failed)}/{total} saved, {len(failed)} failed")


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    print("=== fetch_svgs.py ===\n")

    sets = {
        "mdi": mdi_slugs_from_html(),
        "fluent": fluent_slugs(),
        "tabler": tabler_slugs(),
        "ph": ph_slugs(),
    }

    for prefix, slugs in sets.items():
        print(f"Fetching {prefix} ({len(slugs)} icons)…")
        fetch_set(prefix, slugs)

    print("\nDone.")


if __name__ == "__main__":
    main()
