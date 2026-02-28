"""
Generate a self-contained HTML dashboard for the Jetayu Gadgets price monitor.
Dark theme, amber accents, filters by competitor & change type.
"""

import json
import html
from datetime import datetime


def _fmt_price(val):
    if val is None:
        return "—"
    return f"\u20b9{val:,.0f}"


def generate_dashboard(snapshot_path: str, changes: list[dict], output_path: str):
    print("[*] Generating dashboard …")

    with open(snapshot_path, "r", encoding="utf-8") as f:
        snapshot = json.load(f)

    products = snapshot["products"]
    timestamp = snapshot.get("scraped_at", "unknown")

    competitors = sorted({p["competitor"] for p in products})
    change_types = sorted({c["type"] for c in changes}) if changes else []

    # Build product table rows
    product_rows = ""
    for p in products:
        sale_badge = ""
        if p["sale_pct"]:
            sale_badge = f'<span class="badge badge-sale">-{p["sale_pct"]}%</span>'

        stock_cls = "stock-in" if p["stock_status"] == "in_stock" else "stock-out"
        stock_text = "In Stock" if p["stock_status"] == "in_stock" else "Out of Stock"

        orig_display = _fmt_price(p["original_price"]) if p["original_price"] else ""
        if orig_display and p["original_price"] != p["current_price"]:
            orig_display = f'<span class="price-original">{orig_display}</span>'
        else:
            orig_display = ""

        link = f'<a href="{html.escape(p["url"] or "#")}" target="_blank" rel="noopener">{html.escape(p["name"])}</a>'

        product_rows += f"""
        <tr data-competitor="{html.escape(p['competitor'])}">
          <td>{html.escape(p['competitor'])}</td>
          <td>{link}</td>
          <td class="price-cell">{orig_display} {_fmt_price(p['current_price'])} {sale_badge}</td>
          <td><span class="{stock_cls}">{stock_text}</span></td>
        </tr>"""

    # Build change rows
    change_rows = ""
    type_icons = {
        "price_drop": "\u2193",
        "price_hike": "\u2191",
        "new_sale": "\u2605",
        "sale_ended": "\u2606",
        "new_product": "+",
        "removed_product": "\u2212",
        "back_in_stock": "\u2714",
        "out_of_stock": "\u2718",
    }
    type_classes = {
        "price_drop": "change-good",
        "price_hike": "change-bad",
        "new_sale": "change-good",
        "sale_ended": "change-bad",
        "new_product": "change-info",
        "removed_product": "change-warn",
        "back_in_stock": "change-good",
        "out_of_stock": "change-bad",
    }

    for c in changes:
        icon = type_icons.get(c["type"], "?")
        cls = type_classes.get(c["type"], "")
        details_parts = []
        d = c.get("details", {})

        if c["type"] == "price_drop":
            details_parts.append(
                f'{_fmt_price(d.get("old_price"))} &rarr; {_fmt_price(d.get("new_price"))} '
                f'(<span class="change-good">-{_fmt_price(d.get("diff"))} / -{d.get("diff_pct", 0)}%</span>)'
            )
        elif c["type"] == "price_hike":
            details_parts.append(
                f'{_fmt_price(d.get("old_price"))} &rarr; {_fmt_price(d.get("new_price"))} '
                f'(<span class="change-bad">+{_fmt_price(d.get("diff"))} / +{d.get("diff_pct", 0)}%</span>)'
            )
        elif c["type"] == "new_sale":
            details_parts.append(
                f'{_fmt_price(d.get("current_price"))} ({d.get("sale_pct")}% off)'
            )
        elif c["type"] == "sale_ended":
            details_parts.append(f'Was {d.get("old_sale_pct")}% off, now {_fmt_price(d.get("current_price"))}')
        elif c["type"] == "new_product":
            details_parts.append(f'{_fmt_price(d.get("current_price"))}')
            if d.get("sale_pct"):
                details_parts.append(f'{d["sale_pct"]}% off')
        elif c["type"] == "removed_product":
            details_parts.append(f'Last price: {_fmt_price(d.get("last_known_price"))}')
        elif c["type"] in ("back_in_stock", "out_of_stock"):
            details_parts.append(f'{_fmt_price(d.get("current_price") or d.get("last_known_price"))}')

        details_html = " &middot; ".join(details_parts)

        pname = html.escape(c.get("product_name", ""))
        purl = c.get("url") or "#"
        link = f'<a href="{html.escape(purl)}" target="_blank" rel="noopener">{pname}</a>'

        change_rows += f"""
        <tr data-competitor="{html.escape(c['competitor'])}" data-change-type="{c['type']}">
          <td><span class="change-icon {cls}">{icon}</span></td>
          <td>{html.escape(c['competitor'])}</td>
          <td class="type-label">{c['type'].replace('_', ' ').title()}</td>
          <td>{link}</td>
          <td>{details_html}</td>
        </tr>"""

    # Stats
    total_products = len(products)
    per_competitor = {}
    for p in products:
        per_competitor[p["competitor"]] = per_competitor.get(p["competitor"], 0) + 1
    on_sale = sum(1 for p in products if p["sale_pct"])
    out_of_stock_count = sum(1 for p in products if p["stock_status"] == "out_of_stock")

    stats_cards = f"""
    <div class="stat-card"><div class="stat-num">{total_products}</div><div class="stat-label">Total Products</div></div>
    <div class="stat-card"><div class="stat-num">{len(changes)}</div><div class="stat-label">Changes Detected</div></div>
    <div class="stat-card"><div class="stat-num">{on_sale}</div><div class="stat-label">On Sale</div></div>
    <div class="stat-card"><div class="stat-num">{out_of_stock_count}</div><div class="stat-label">Out of Stock</div></div>
    """

    competitor_options = "".join(
        f'<option value="{html.escape(c)}">{html.escape(c)} ({per_competitor.get(c, 0)})</option>'
        for c in competitors
    )
    change_type_options = "".join(
        f'<option value="{t}">{t.replace("_", " ").title()}</option>'
        for t in change_types
    )

    dashboard_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Jetayu Gadgets — Competitor Price Monitor</title>
<style>
  :root {{
    --bg: #111111;
    --bg2: #1a1a1a;
    --bg3: #222222;
    --border: #333333;
    --text: #e0e0e0;
    --text-dim: #888888;
    --amber: #f59e0b;
    --amber-dim: #b45309;
    --green: #22c55e;
    --red: #ef4444;
    --blue: #3b82f6;
    --orange: #f97316;
  }}
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
  }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}

  /* Header */
  header {{
    background: var(--bg2);
    border-bottom: 2px solid var(--amber);
    padding: 20px 0;
    margin-bottom: 24px;
  }}
  header .container {{ display: flex; justify-content: space-between; align-items: center; }}
  .logo {{ font-size: 22px; font-weight: 700; color: var(--amber); }}
  .logo span {{ color: var(--text); font-weight: 400; }}
  .timestamp {{ color: var(--text-dim); font-size: 13px; }}

  /* Stats */
  .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 16px; margin-bottom: 28px; }}
  .stat-card {{
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 20px;
    text-align: center;
  }}
  .stat-num {{ font-size: 32px; font-weight: 700; color: var(--amber); }}
  .stat-label {{ font-size: 13px; color: var(--text-dim); margin-top: 4px; }}

  /* Filters */
  .filters {{
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    flex-wrap: wrap;
    align-items: center;
  }}
  .filters label {{ font-size: 13px; color: var(--text-dim); }}
  .filters select, .filters input {{
    background: var(--bg3);
    border: 1px solid var(--border);
    color: var(--text);
    padding: 8px 12px;
    border-radius: 6px;
    font-size: 14px;
  }}
  .filters select:focus, .filters input:focus {{ outline: none; border-color: var(--amber); }}

  /* Section headers */
  .section-title {{
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
    color: var(--amber);
  }}

  /* Tables */
  table {{ width: 100%; border-collapse: collapse; }}
  th {{
    background: var(--bg3);
    text-align: left;
    padding: 12px 14px;
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--amber);
    border-bottom: 2px solid var(--amber-dim);
    position: sticky;
    top: 0;
  }}
  td {{
    padding: 10px 14px;
    border-bottom: 1px solid var(--border);
    font-size: 14px;
    vertical-align: middle;
  }}
  tr:hover {{ background: var(--bg3); }}
  a {{ color: var(--amber); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}

  /* Badges & tags */
  .badge {{
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 11px;
    font-weight: 600;
  }}
  .badge-sale {{ background: var(--green); color: #000; }}
  .stock-in {{ color: var(--green); font-size: 13px; }}
  .stock-out {{ color: var(--red); font-size: 13px; }}
  .price-original {{ text-decoration: line-through; color: var(--text-dim); margin-right: 6px; }}
  .price-cell {{ white-space: nowrap; }}

  /* Change icons */
  .change-icon {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    font-size: 14px;
    font-weight: 700;
  }}
  .change-good {{ background: rgba(34,197,94,0.15); color: var(--green); }}
  .change-bad {{ background: rgba(239,68,68,0.15); color: var(--red); }}
  .change-info {{ background: rgba(59,130,246,0.15); color: var(--blue); }}
  .change-warn {{ background: rgba(249,115,22,0.15); color: var(--orange); }}
  .type-label {{ text-transform: capitalize; font-weight: 500; }}

  /* Table wrapper */
  .table-wrap {{
    background: var(--bg2);
    border: 1px solid var(--border);
    border-radius: 10px;
    overflow: hidden;
    margin-bottom: 32px;
  }}
  .table-scroll {{ overflow-x: auto; max-height: 600px; overflow-y: auto; }}

  /* No-data message */
  .no-data {{
    text-align: center;
    padding: 40px;
    color: var(--text-dim);
    font-size: 15px;
  }}

  /* Footer */
  footer {{
    text-align: center;
    padding: 24px;
    color: var(--text-dim);
    font-size: 12px;
    border-top: 1px solid var(--border);
    margin-top: 20px;
  }}

  @media (max-width: 768px) {{
    .filters {{ flex-direction: column; }}
    .stats {{ grid-template-columns: repeat(2, 1fr); }}
  }}
</style>
</head>
<body>

<header>
  <div class="container">
    <div class="logo">Jetayu Gadgets <span>/ Price Monitor</span></div>
    <div class="timestamp">Scraped: {html.escape(timestamp)}</div>
  </div>
</header>

<div class="container">

  <!-- Stats -->
  <div class="stats">{stats_cards}</div>

  <!-- Changes Section -->
  <div class="section-title">Changes Detected</div>
  <div class="filters">
    <label>Competitor:</label>
    <select id="filterCompetitorChange" onchange="applyChangeFilters()">
      <option value="">All</option>
      {competitor_options}
    </select>
    <label>Change Type:</label>
    <select id="filterChangeType" onchange="applyChangeFilters()">
      <option value="">All</option>
      {change_type_options}
    </select>
  </div>
  <div class="table-wrap">
    <div class="table-scroll">
      <table id="changesTable">
        <thead>
          <tr>
            <th style="width:40px"></th>
            <th>Competitor</th>
            <th>Type</th>
            <th>Product</th>
            <th>Details</th>
          </tr>
        </thead>
        <tbody>
          {change_rows if change_rows else '<tr><td colspan="5" class="no-data">No changes detected (first run or no differences)</td></tr>'}
        </tbody>
      </table>
    </div>
  </div>

  <!-- All Products Section -->
  <div class="section-title">All Tracked Products</div>
  <div class="filters">
    <label>Competitor:</label>
    <select id="filterCompetitorProduct" onchange="applyProductFilters()">
      <option value="">All</option>
      {competitor_options}
    </select>
    <label>Search:</label>
    <input type="text" id="searchProduct" placeholder="Search products\u2026" oninput="applyProductFilters()">
  </div>
  <div class="table-wrap">
    <div class="table-scroll">
      <table id="productsTable">
        <thead>
          <tr>
            <th>Competitor</th>
            <th>Product</th>
            <th>Price</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {product_rows if product_rows else '<tr><td colspan="4" class="no-data">No products found</td></tr>'}
        </tbody>
      </table>
    </div>
  </div>

</div>

<footer>
  Jetayu Gadgets Competitor Price Monitor &mdash; Generated {html.escape(datetime.now().strftime('%Y-%m-%d %H:%M'))}
</footer>

<script>
function applyChangeFilters() {{
  const comp = document.getElementById('filterCompetitorChange').value;
  const type = document.getElementById('filterChangeType').value;
  const rows = document.querySelectorAll('#changesTable tbody tr[data-competitor]');
  rows.forEach(row => {{
    const matchComp = !comp || row.dataset.competitor === comp;
    const matchType = !type || row.dataset.changeType === type;
    row.style.display = (matchComp && matchType) ? '' : 'none';
  }});
}}

function applyProductFilters() {{
  const comp = document.getElementById('filterCompetitorProduct').value;
  const search = document.getElementById('searchProduct').value.toLowerCase();
  const rows = document.querySelectorAll('#productsTable tbody tr[data-competitor]');
  rows.forEach(row => {{
    const matchComp = !comp || row.dataset.competitor === comp;
    const text = row.textContent.toLowerCase();
    const matchSearch = !search || text.includes(search);
    row.style.display = (matchComp && matchSearch) ? '' : 'none';
  }});
}}
</script>

</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(dashboard_html)

    print(f"[✓] Dashboard saved → {output_path}")
