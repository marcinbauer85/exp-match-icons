#!/usr/bin/env python3
"""
Apply visual-match suggestions from matches.json back into index.html.

A suggestion is accepted only when ALL of these hold:
  1. Cosine similarity ≥ min_score (default 0.90)
  2. The current human mapping is NOT already in the model's top-N (top 5)
  3. The suggested icon slug shares ≥ 1 meaningful word with the MDI slug
     (semantic name overlap — prevents shape coincidences like sun→star)

Produces a summary of accepted vs rejected suggestions, then patches index.html.

Usage:
  python3 tools/apply_matches.py [--dry-run] [--min-score 0.90] [--top 5]
"""

import argparse
import json
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).parent
ROOT = TOOLS.parent
INDEX = ROOT / "index.html"
MATCHES = TOOLS / "matches.json"

# Short words that are too generic to count as meaningful overlap
STOPWORDS = {
    "a","an","the","of","and","or","in","on","at","to","for","with",
    "24","20","16","12","regular","filled","outline","small","large",
    "off","on","up","down","left","right","open","closed",
}

# Directional/state words — if MDI slug has one, suggestion must keep it
DIRECTIONAL = {"up","down","left","right","open","closed","on","off","top","bottom"}


def is_filled(icon: str) -> bool:
    s = icon.split(":")[-1]
    return s.endswith("-filled") or s.endswith("-fill") or s.endswith("-24-filled")


def same_fill_style(current: str, suggestion: str) -> bool:
    """Reject if suggestion adds or removes filled style."""
    return is_filled(current) == is_filled(suggestion)


WEATHER_TYPES = {"rainy","rain","snowy","snow","fog","foggy","sunny","sun","night","cloudy","cloud",
                 "hail","lightning","windy","wind","partly","pouring","thunder","thunderstorm","squalls"}

SINGLE_DIRS = {"up","down","left","right"}  # single-axis directions
# Generic shape words that appear in many unrelated icons — require extra score confidence
GENERIC_SHAPE_WORDS = {"circle","square","box","arrow","triangle","polygon"}
# Semantic words that critically change an icon's meaning — suggestion must also contain them if MDI does
SEMANTIC_CRITICAL = {"alert","warning","error","off","no","check","play","pause","stop","plus","minus","question"}

def preserves_direction(mdi_slug: str, suggestion: str) -> bool:
    """If the MDI icon has an explicit direction word, the suggestion should too.
    Also: single-directional arrows must not become bidirectional."""
    mdi_words = set(re.split(r"[-_]", mdi_slug.lower()))
    mdi_dirs = mdi_words & DIRECTIONAL
    if not mdi_dirs:
        return True
    sugg_slug = suggestion.split(":")[-1].lower()
    sugg_words = set(re.split(r"[-_]", sugg_slug))
    # Reject if suggestion is bidirectional but MDI only has ONE direction
    if "bidirectional" in sugg_words and len(mdi_dirs & SINGLE_DIRS) == 1 and not any(
        all(d in mdi_words for d in pair) for pair in [("up","down"), ("left","right")]
    ):
        return False
    return bool(mdi_dirs & sugg_words)


def preserves_weather_type(mdi_slug: str, suggestion: str) -> bool:
    """Weather icons must stay within the same weather category."""
    mdi_words = set(re.split(r"[-_]", mdi_slug.lower()))
    if not (mdi_words & WEATHER_TYPES):
        return True  # not a weather icon
    sugg_words = set(re.split(r"[-_]", suggestion.split(":")[-1].lower()))
    # Both must share a weather type word
    return bool((mdi_words & WEATHER_TYPES) & (sugg_words | {"weather"}))


def not_too_specific(mdi_slug: str, current: str, suggestion: str) -> bool:
    """Reject if suggestion adds context words not in MDI slug or current."""
    mdi_words = slug_words(mdi_slug)
    cur_words = slug_words(current.split(":")[-1]) if current else set()
    known = mdi_words | cur_words
    sugg_words = slug_words(suggestion.split(":")[-1])
    extra = sugg_words - known
    return len(extra) <= 1  # allow at most 1 new word


def slug_words(slug: str) -> set[str]:
    """Split a slug like 'door-open-24-regular' into meaningful words."""
    return {w for w in re.split(r"[-_]", slug.lower()) if w and w not in STOPWORDS and len(w) > 1}


def has_word_overlap(mdi_slug: str, suggested_slug: str) -> bool:
    """True if MDI and suggested slugs share at least one meaningful word."""
    mdi_words = slug_words(mdi_slug)
    # Extract just the slug part from "fluent:door-open-24-regular"
    suggested_bare = suggested_slug.split(":")[-1]
    sugg_words = slug_words(suggested_bare)
    return bool(mdi_words & sugg_words)


def parse_mappings(html: str):
    """Yield (match_object, groups) for each mapping dict in the JS array."""
    pattern = re.compile(
        r'\{\s*mat:\s*"([^"]+)"'
        r'(?:,\s*flu:\s*"([^"]*)")?'
        r'(?:,\s*tab:\s*"([^"]*)")?'
        r'(?:,\s*ph:\s*"([^"]*)")?'
        r'(?:,\s*note:\s*"([^"]*)")?'
        r'\s*\}',
        re.DOTALL,
    )
    return list(pattern.finditer(html))


def build_replacement(
    mat: str, flu: str, tab: str, ph: str, note: str,
    suggestions: dict, min_score: float, top_n: int,
    accepted: list, rejected: list,
) -> str:
    slug = mat.removeprefix("mdi:")
    sugg = suggestions.get(slug, {})

    new_flu, new_tab, new_ph = flu, tab, ph

    for field, current in [("fluent", flu), ("tabler", tab), ("ph", ph)]:
        cands = sugg.get(field, [])
        if not cands:
            continue
        top1 = cands[0]
        if top1["score"] < min_score:
            rejected.append((mat, field, current, top1["icon"], top1["score"], "score too low"))
            continue
        # Skip if human pick is already in top-N
        top_icons = {c["icon"] for c in cands[:top_n]}
        if current and current in top_icons:
            continue
        # Require semantic name overlap
        if not has_word_overlap(slug, top1["icon"]):
            rejected.append((mat, field, current, top1["icon"], top1["score"], "no name overlap"))
            continue
        # Keep fill-style consistency
        if current and not same_fill_style(current, top1["icon"]):
            rejected.append((mat, field, current, top1["icon"], top1["score"], "style mismatch"))
            continue
        # Keep directional integrity
        if not preserves_direction(slug, top1["icon"]):
            rejected.append((mat, field, current, top1["icon"], top1["score"], "direction mismatch"))
            continue
        # Keep weather type
        if not preserves_weather_type(slug, top1["icon"]):
            rejected.append((mat, field, current, top1["icon"], top1["score"], "weather mismatch"))
            continue
        # Don't add unrelated context words
        if not not_too_specific(slug, current, top1["icon"]):
            rejected.append((mat, field, current, top1["icon"], top1["score"], "too specific"))
            continue
        # Preserve critical semantic words (alert, off, check, play, etc.)
        mdi_critical = set(re.split(r"[-_]", slug.lower())) & SEMANTIC_CRITICAL
        sugg_critical = set(re.split(r"[-_]", top1["icon"].split(":")[-1].lower())) & SEMANTIC_CRITICAL
        if mdi_critical and not (mdi_critical & sugg_critical):
            rejected.append((mat, field, current, top1["icon"], top1["score"], "critical word missing"))
            continue
        # If shared words are only generic shapes, require higher confidence
        mdi_kw = slug_words(slug)
        sugg_kw = slug_words(top1["icon"].split(":")[-1])
        overlap = mdi_kw & sugg_kw
        if overlap and overlap <= GENERIC_SHAPE_WORDS and top1["score"] < 0.97:
            rejected.append((mat, field, current, top1["icon"], top1["score"], "generic overlap only"))
            continue
        # Accept
        accepted.append((mat, field, current, top1["icon"], top1["score"]))
        if field == "fluent":
            new_flu = top1["icon"]
        elif field == "tabler":
            new_tab = top1["icon"]
        elif field == "ph":
            new_ph = top1["icon"]

    parts = [f'mat: "{mat}"']
    if new_flu:
        parts.append(f'flu: "{new_flu}"')
    if new_tab:
        parts.append(f'tab: "{new_tab}"')
    if new_ph:
        parts.append(f'ph: "{new_ph}"')
    if note:
        parts.append(f'note: "{note}"')
    return "{ " + ", ".join(parts) + " }"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--min-score", type=float, default=0.90)
    parser.add_argument("--top", type=int, default=5)
    args = parser.parse_args()

    if not MATCHES.exists():
        sys.exit("matches.json not found. Run embed_and_match.py first.")

    suggestions = json.loads(MATCHES.read_text())
    html = INDEX.read_text()
    mapping_matches = parse_mappings(html)

    if not mapping_matches:
        sys.exit("No mapping objects found in index.html.")

    accepted, rejected = [], []
    result = html

    for m in reversed(mapping_matches):
        mat, flu, tab, ph, note = (m.group(i) or "" for i in range(1, 6))
        replacement = build_replacement(
            mat, flu, tab, ph, note,
            suggestions, args.min_score, args.top,
            accepted, rejected,
        )
        result = result[: m.start()] + replacement + result[m.end() :]

    print(f"Mappings checked : {len(mapping_matches)}")
    print(f"Fields accepted  : {len(accepted)}")
    print(f"Fields rejected  : {len(rejected)}")

    if accepted:
        print("\n── Accepted changes ──")
        for mat, field, cur, new, score in sorted(accepted, key=lambda x: -x[4]):
            print(f"  {mat:40s} {field:7s} {cur!r:50s} → {new!r} ({score:.3f})")

    # Show top rejections by reason
    no_overlap = [r for r in rejected if "name overlap" in r[5]]
    print(f"\n── Rejected (no name overlap): {len(no_overlap)} ──")
    for mat, field, cur, new, score, reason in sorted(no_overlap, key=lambda x: -x[4])[:10]:
        print(f"  {mat:35s} {field:7s} {new!r} ({score:.3f})")

    if args.dry_run:
        print("\n[dry-run] No files written.")
        return

    INDEX.write_text(result)
    print(f"\nWrote updated index.html  ({len(accepted)} fields improved)")


if __name__ == "__main__":
    main()
