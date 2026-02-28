"""
Scrapers for each competitor site.
Each scraper returns a list of product dicts:
  { name, current_price, original_price, sale_pct, stock_status, url, competitor }
"""
from __future__ import annotations

import json
import os
import re
import time
from datetime import datetime
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TIMEOUT = 30


# ── helpers ──────────────────────────────────────────────────────────────

def _get(url: str) -> BeautifulSoup | None:
    """Fetch a page and return a BeautifulSoup object, or None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"  [!] Failed to fetch {url}: {e}")
        return None


def _parse_price(text: str | None) -> float | None:
    """Extract numeric price from text like '₹1,23,456.00'."""
    if not text:
        return None
    digits = re.sub(r"[^\d.]", "", text.strip())
    if not digits:
        return None
    try:
        return float(digits)
    except ValueError:
        return None


def _calc_sale_pct(original: float | None, current: float | None) -> float | None:
    if original and current and original > current:
        return round((1 - current / original) * 100, 1)
    return None


def _dedup(products: list[dict]) -> list[dict]:
    """Remove duplicates by URL, keeping first occurrence."""
    seen = set()
    out = []
    for p in products:
        key = p["url"]
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


# ── WooCommerce generic parser ──────────────────────────────────────────

def _parse_woo_page(soup: BeautifulSoup, base_url: str, competitor: str) -> list[dict]:
    """Parse a typical WooCommerce product-listing page."""
    products = []
    items = soup.select("li.product, li.type-product, div.product-grid-item")
    if not items:
        items = soup.select(".products .product")
    for item in items:
        # name
        name_el = (
            item.select_one(".woocommerce-loop-product__title")
            or item.select_one("h2")
            or item.select_one("h3")
            or item.select_one(".product-title")
        )
        name = name_el.get_text(strip=True) if name_el else None
        if not name:
            continue

        # url
        link_el = item.select_one("a[href]")
        url = link_el["href"] if link_el else None
        if url:
            url = urljoin(base_url, url)

        # prices
        price_block = item.select_one(".price")
        original_price = None
        current_price = None

        if price_block:
            del_el = price_block.select_one("del .woocommerce-Price-amount, del .amount, del")
            ins_el = price_block.select_one("ins .woocommerce-Price-amount, ins .amount, ins")

            if del_el and ins_el:
                original_price = _parse_price(del_el.get_text())
                current_price = _parse_price(ins_el.get_text())
            else:
                amounts = price_block.select(".woocommerce-Price-amount, .amount")
                if len(amounts) >= 2:
                    original_price = _parse_price(amounts[0].get_text())
                    current_price = _parse_price(amounts[-1].get_text())
                elif len(amounts) == 1:
                    current_price = _parse_price(amounts[0].get_text())
                else:
                    current_price = _parse_price(price_block.get_text())

        # stock
        stock_status = "in_stock"
        out_badge = item.select_one(".out-of-stock, .sold-out, .stock.out-of-stock")
        if out_badge:
            stock_status = "out_of_stock"

        products.append({
            "name": name,
            "current_price": current_price,
            "original_price": original_price,
            "sale_pct": _calc_sale_pct(original_price, current_price),
            "stock_status": stock_status,
            "url": url,
            "competitor": competitor,
        })

    return products


# ── Xboom ────────────────────────────────────────────────────────────────

XBOOM_URLS = [
    "https://www.xboom.in/dji-drones-and-accessories/",
    "https://www.xboom.in/dji-mini/",
    "https://www.xboom.in/dji-air-series/",
    "https://www.xboom.in/product-category/brands/dji/dji-drone/",
]


def _scrape_woo_paginated(url: str, competitor: str) -> list[dict]:
    """Scrape a WooCommerce listing URL plus all its pagination pages."""
    all_products = []
    next_url = url
    pages_seen = 0
    while next_url and pages_seen < 20:
        soup = _get(next_url)
        if soup is None:
            break
        products = _parse_woo_page(soup, next_url, competitor)
        if not products:
            break
        all_products.extend(products)
        pages_seen += 1
        # Follow the actual next-page link href
        next_el = soup.select_one("a.next.page-numbers, a.woocommerce-pagination-next")
        next_url = next_el["href"] if next_el and next_el.get("href") else None
    return all_products


def scrape_xboom() -> list[dict]:
    print("[*] Scraping Xboom …")
    all_products = []
    for url in XBOOM_URLS:
        products = _scrape_woo_paginated(url, "Xboom")
        print(f"    {url}  → {len(products)} products")
        all_products.extend(products)
    all_products = _dedup(all_products)
    print(f"    Total (deduped): {len(all_products)}")
    return all_products


# ── Designinfo ───────────────────────────────────────────────────────────

DESIGNINFO_URLS = [
    "https://www.designinfo.in/drones/",
]


def scrape_designinfo() -> list[dict]:
    print("[*] Scraping Designinfo …")
    all_products = []
    for url in DESIGNINFO_URLS:
        products = _scrape_woo_paginated(url, "Designinfo")
        print(f"    {url}  → {len(products)} products")
        all_products.extend(products)
    all_products = _dedup(all_products)
    print(f"    Total (deduped): {len(all_products)}")
    return all_products


# ── Everse ───────────────────────────────────────────────────────────────

EVERSE_URLS = [
    "https://everse.in/category/dji-camera-drones",
    "https://everse.in/category/dji-fpv-series",
    "https://everse.in/category/dji",
]


def _parse_everse_page(html_text: str) -> list[dict]:
    """
    Parse an Everse category page by extracting product data from the
    Next.js RSC streaming payload. Data uses escaped quotes (\") inside
    JS string literals.
    """
    products = []

    # In the raw HTML, keys/values are escaped as: \"key\":\"value\"
    # Python reads the file as-is, so the two-char sequence is \ + "
    product_pattern = re.compile(
        r'\\"product\\":\{\\"id\\":(\d+).*?'
        r'\\"handle\\":\\"([^\\]+)\\".*?'
        r'\\"seo_title\\":\\"((?:[^\\]|\\[^"])*)\\".*?'
        r'\\"variant\\":\{(.*?)\}'
    )

    for m in product_pattern.finditer(html_text):
        handle = m.group(2)
        title = m.group(3)
        variant_raw = m.group(4)

        price_m = re.search(r'\\"price\\":(\d+)', variant_raw)
        compare_m = re.search(r'\\"compare_at_price\\":(\d+)', variant_raw)
        avail_m = re.search(r'\\"available\\":(\d+)', variant_raw)

        current_price = float(price_m.group(1)) if price_m else None
        original_price = float(compare_m.group(1)) if compare_m else None
        available = int(avail_m.group(1)) if avail_m else 0

        stock_status = "in_stock" if available > 0 else "out_of_stock"

        products.append({
            "name": title,
            "current_price": current_price,
            "original_price": original_price,
            "sale_pct": _calc_sale_pct(original_price, current_price),
            "stock_status": stock_status,
            "url": f"https://everse.in/product/{handle}",
            "competitor": "Everse",
        })

    return products


def scrape_everse() -> list[dict]:
    print("[*] Scraping Everse …")
    all_products = []
    for url in EVERSE_URLS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [!] Failed to fetch {url}: {e}")
            continue

        products = _parse_everse_page(resp.text)
        print(f"    {url}  → {len(products)} products")
        all_products.extend(products)

    all_products = _dedup(all_products)
    print(f"    Total (deduped): {len(all_products)}")
    return all_products


# ── orchestration ────────────────────────────────────────────────────────

def run_all_scrapers(snapshots_dir: str) -> str:
    """Run every scraper, save snapshot, return path to the JSON file."""
    print()
    all_products = []
    all_products.extend(scrape_xboom())
    print()
    all_products.extend(scrape_everse())
    print()
    all_products.extend(scrape_designinfo())
    print()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    snapshot = {
        "timestamp": timestamp,
        "scraped_at": datetime.now().isoformat(),
        "product_count": len(all_products),
        "products": all_products,
    }

    filename = f"snapshot_{timestamp}.json"
    path = os.path.join(snapshots_dir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, ensure_ascii=False)

    print(f"[✓] Snapshot saved → {path}")
    print(f"    {len(all_products)} products across all competitors\n")
    return path
