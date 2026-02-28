"""
Compare the latest two snapshots and return structured changes.

Change types:
  - price_drop      : current_price decreased
  - price_hike      : current_price increased
  - new_sale        : product now has a sale_pct that it didn't before
  - sale_ended      : product had a sale_pct that is now gone
  - new_product     : product URL appears for the first time
  - removed_product : product URL no longer present
  - back_in_stock   : was out_of_stock, now in_stock
  - out_of_stock    : was in_stock, now out_of_stock
"""

from __future__ import annotations

import glob
import json
import os


def _load_snapshot(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _latest_two(snapshots_dir: str) -> tuple[str | None, str | None]:
    """Return (previous_path, latest_path) or (None, latest) if only one."""
    files = sorted(glob.glob(os.path.join(snapshots_dir, "snapshot_*.json")))
    if len(files) == 0:
        return None, None
    if len(files) == 1:
        return None, files[0]
    return files[-2], files[-1]


def _index_by_url(products: list[dict]) -> dict[str, dict]:
    idx = {}
    for p in products:
        key = p.get("url") or p.get("name")
        if key:
            idx[key] = p
    return idx


def compare_snapshots(snapshots_dir: str) -> list[dict]:
    """
    Compare latest two snapshots.
    Returns a list of change dicts:
      { type, competitor, product_name, url, details:{...} }
    """
    prev_path, curr_path = _latest_two(snapshots_dir)

    if curr_path is None:
        print("[!] No snapshots found — nothing to compare.")
        return []

    curr_snap = _load_snapshot(curr_path)
    curr_products = curr_snap["products"]

    if prev_path is None:
        print("[*] First run — no previous snapshot to compare against.")
        # Mark every product as "new_product"
        changes = []
        for p in curr_products:
            changes.append({
                "type": "new_product",
                "competitor": p["competitor"],
                "product_name": p["name"],
                "url": p.get("url"),
                "details": {
                    "current_price": p["current_price"],
                    "original_price": p["original_price"],
                    "sale_pct": p["sale_pct"],
                    "stock_status": p["stock_status"],
                },
            })
        print(f"[✓] {len(changes)} new products catalogued.\n")
        return changes

    prev_snap = _load_snapshot(prev_path)
    prev_products = prev_snap["products"]

    prev_idx = _index_by_url(prev_products)
    curr_idx = _index_by_url(curr_products)

    changes = []

    # ── products in both snapshots ───────────────────────────────────────
    for key, curr in curr_idx.items():
        if key not in prev_idx:
            continue
        prev = prev_idx[key]

        cp = curr.get("current_price")
        pp = prev.get("current_price")

        # price drop
        if cp is not None and pp is not None and cp < pp:
            changes.append({
                "type": "price_drop",
                "competitor": curr["competitor"],
                "product_name": curr["name"],
                "url": curr.get("url"),
                "details": {
                    "old_price": pp,
                    "new_price": cp,
                    "diff": round(pp - cp, 2),
                    "diff_pct": round((1 - cp / pp) * 100, 1) if pp else None,
                },
            })

        # price hike
        if cp is not None and pp is not None and cp > pp:
            changes.append({
                "type": "price_hike",
                "competitor": curr["competitor"],
                "product_name": curr["name"],
                "url": curr.get("url"),
                "details": {
                    "old_price": pp,
                    "new_price": cp,
                    "diff": round(cp - pp, 2),
                    "diff_pct": round((cp / pp - 1) * 100, 1) if pp else None,
                },
            })

        # new sale
        if curr.get("sale_pct") and not prev.get("sale_pct"):
            changes.append({
                "type": "new_sale",
                "competitor": curr["competitor"],
                "product_name": curr["name"],
                "url": curr.get("url"),
                "details": {
                    "sale_pct": curr["sale_pct"],
                    "current_price": cp,
                    "original_price": curr.get("original_price"),
                },
            })

        # sale ended
        if prev.get("sale_pct") and not curr.get("sale_pct"):
            changes.append({
                "type": "sale_ended",
                "competitor": curr["competitor"],
                "product_name": curr["name"],
                "url": curr.get("url"),
                "details": {
                    "old_sale_pct": prev["sale_pct"],
                    "current_price": cp,
                },
            })

        # stock changes
        if prev.get("stock_status") == "out_of_stock" and curr.get("stock_status") == "in_stock":
            changes.append({
                "type": "back_in_stock",
                "competitor": curr["competitor"],
                "product_name": curr["name"],
                "url": curr.get("url"),
                "details": {"current_price": cp},
            })
        if prev.get("stock_status") == "in_stock" and curr.get("stock_status") == "out_of_stock":
            changes.append({
                "type": "out_of_stock",
                "competitor": curr["competitor"],
                "product_name": curr["name"],
                "url": curr.get("url"),
                "details": {"last_known_price": pp},
            })

    # ── new products ─────────────────────────────────────────────────────
    for key, curr in curr_idx.items():
        if key not in prev_idx:
            changes.append({
                "type": "new_product",
                "competitor": curr["competitor"],
                "product_name": curr["name"],
                "url": curr.get("url"),
                "details": {
                    "current_price": curr["current_price"],
                    "original_price": curr["original_price"],
                    "sale_pct": curr["sale_pct"],
                    "stock_status": curr["stock_status"],
                },
            })

    # ── removed products ─────────────────────────────────────────────────
    for key, prev in prev_idx.items():
        if key not in curr_idx:
            changes.append({
                "type": "removed_product",
                "competitor": prev["competitor"],
                "product_name": prev["name"],
                "url": prev.get("url"),
                "details": {
                    "last_known_price": prev["current_price"],
                },
            })

    print(f"[*] Comparison: {prev_path}")
    print(f"             vs {curr_path}")
    type_counts = {}
    for c in changes:
        type_counts[c["type"]] = type_counts.get(c["type"], 0) + 1
    for t, n in sorted(type_counts.items()):
        print(f"    {t}: {n}")
    print(f"[✓] {len(changes)} total changes detected.\n")

    return changes
