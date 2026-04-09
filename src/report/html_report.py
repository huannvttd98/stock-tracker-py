import os
from datetime import datetime, timedelta, timezone

import pandas as pd

import config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

VN_TZ = timezone(timedelta(hours=7))

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stock Tracker - Bao cao {date}</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: 'Segoe UI', Tahoma, sans-serif; background: #0f1117; color: #e1e4e8; padding: 20px; }}
  .header {{ text-align: center; padding: 20px 0 30px; }}
  .header h1 {{ font-size: 24px; color: #58a6ff; }}
  .header .time {{ color: #8b949e; margin-top: 6px; font-size: 14px; }}
  .stats {{ display: flex; gap: 16px; justify-content: center; flex-wrap: wrap; margin-bottom: 30px; }}
  .stat-card {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px 24px; text-align: center; min-width: 160px; }}
  .stat-card .value {{ font-size: 28px; font-weight: bold; }}
  .stat-card .label {{ color: #8b949e; font-size: 13px; margin-top: 4px; }}
  .green {{ color: #3fb950; }}
  .red {{ color: #f85149; }}
  .yellow {{ color: #d29922; }}
  .section {{ background: #161b22; border: 1px solid #30363d; border-radius: 8px; margin-bottom: 24px; overflow: hidden; }}
  .section-title {{ padding: 14px 20px; font-size: 16px; font-weight: 600; border-bottom: 1px solid #30363d; background: #1c2128; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
  th {{ background: #1c2128; padding: 10px 16px; text-align: left; font-weight: 600; color: #8b949e; border-bottom: 1px solid #30363d; position: sticky; top: 0; }}
  td {{ padding: 10px 16px; border-bottom: 1px solid #21262d; }}
  tr:hover td {{ background: #1c2128; }}
  .rank {{ color: #8b949e; font-size: 13px; }}
  .symbol {{ font-weight: 700; color: #58a6ff; }}
  .profit {{ font-weight: 700; font-size: 15px; }}
  .price {{ font-family: 'Consolas', monospace; }}
  .volume {{ color: #8b949e; }}
  .filter-bar {{ padding: 14px 20px; display: flex; gap: 12px; align-items: center; border-bottom: 1px solid #30363d; flex-wrap: wrap; }}
  .filter-bar input, .filter-bar select {{ background: #0d1117; border: 1px solid #30363d; color: #e1e4e8; padding: 6px 12px; border-radius: 6px; font-size: 13px; }}
  .filter-bar input {{ width: 200px; }}
  .filter-bar label {{ color: #8b949e; font-size: 13px; }}
  .no-data {{ text-align: center; padding: 60px 20px; color: #8b949e; }}
  .footer {{ text-align: center; color: #484f58; font-size: 12px; padding: 20px 0; }}
</style>
</head>
<body>

<div class="header">
  <h1>Vietnam Stock Tracker</h1>
  <div class="time">Cap nhat: {timestamp} (ICT) | Nguon: {source}</div>
</div>

<div class="stats">
  <div class="stat-card">
    <div class="value">{total_symbols}</div>
    <div class="label">Tong so ma</div>
  </div>
  <div class="stat-card">
    <div class="value green">{gainers}</div>
    <div class="label">Tang gia</div>
  </div>
  <div class="stat-card">
    <div class="value red">{losers}</div>
    <div class="label">Giam gia</div>
  </div>
  <div class="stat-card">
    <div class="value yellow">{above_threshold}</div>
    <div class="label">Tang &gt; {threshold}%</div>
  </div>
</div>

<div class="section">
  <div class="section-title">Co phieu tang &gt; {threshold}%</div>
  <div class="filter-bar">
    <input type="text" id="search" placeholder="Tim ma co phieu..." onkeyup="filterTable()">
    <label>Sap xep:</label>
    <select id="sortBy" onchange="sortTable()">
      <option value="profit_desc">% Loi nhuan (cao -&gt; thap)</option>
      <option value="profit_asc">% Loi nhuan (thap -&gt; cao)</option>
      <option value="volume_desc">Volume (cao -&gt; thap)</option>
      <option value="symbol_asc">Ma (A -&gt; Z)</option>
    </select>
  </div>
  {profitable_table}
</div>

<div class="section">
  <div class="section-title">Toan bo co phieu ({total_symbols} ma)</div>
  <div class="filter-bar">
    <input type="text" id="searchAll" placeholder="Tim ma co phieu..." onkeyup="filterTableAll()">
  </div>
  {all_table}
</div>

<div class="footer">
  Stock Tracker &bull; Du lieu chi mang tinh tham khao
</div>

<script>
function filterTable() {{
  const q = document.getElementById('search').value.toUpperCase();
  const rows = document.querySelectorAll('#tblProfit tbody tr');
  rows.forEach(r => {{
    const sym = r.cells[1].textContent.toUpperCase();
    r.style.display = sym.includes(q) ? '' : 'none';
  }});
}}

function filterTableAll() {{
  const q = document.getElementById('searchAll').value.toUpperCase();
  const rows = document.querySelectorAll('#tblAll tbody tr');
  rows.forEach(r => {{
    const sym = r.cells[1].textContent.toUpperCase();
    r.style.display = sym.includes(q) ? '' : 'none';
  }});
}}

function sortTable() {{
  const by = document.getElementById('sortBy').value;
  const tbody = document.querySelector('#tblProfit tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));

  rows.sort((a, b) => {{
    if (by === 'profit_desc') return parseFloat(b.dataset.profit) - parseFloat(a.dataset.profit);
    if (by === 'profit_asc') return parseFloat(a.dataset.profit) - parseFloat(b.dataset.profit);
    if (by === 'volume_desc') return parseFloat(b.dataset.volume) - parseFloat(a.dataset.volume);
    if (by === 'symbol_asc') return a.dataset.symbol.localeCompare(b.dataset.symbol);
    return 0;
  }});

  rows.forEach((r, i) => {{
    r.cells[0].textContent = i + 1;
    tbody.appendChild(r);
  }});
}}
</script>
</body>
</html>"""


def _format_number(val):
    try:
        return f"{val:,.0f}"
    except (ValueError, TypeError):
        return str(val)


def _profit_class(val):
    if val > 0:
        return "green"
    elif val < 0:
        return "red"
    return ""


def _build_table(df, table_id, show_rank=True):
    if df.empty:
        return '<div class="no-data">Khong co du lieu</div>'

    rows = []
    for i, (_, row) in enumerate(df.iterrows(), 1):
        symbol = row.get("symbol", "")
        profit = row.get("profit_pct", 0)
        open_p = row.get("open", 0)
        close_p = row.get("close", 0)
        high = row.get("high", 0)
        low = row.get("low", 0)
        volume = row.get("volume", 0)
        cls = _profit_class(profit)
        sign = "+" if profit > 0 else ""

        rows.append(
            f'<tr data-profit="{profit}" data-volume="{volume}" data-symbol="{symbol}">'
            f'<td class="rank">{i}</td>'
            f'<td class="symbol">{symbol}</td>'
            f'<td class="profit {cls}">{sign}{profit:.2f}%</td>'
            f'<td class="price">{_format_number(open_p)}</td>'
            f'<td class="price">{_format_number(close_p)}</td>'
            f'<td class="price">{_format_number(high)}</td>'
            f'<td class="price">{_format_number(low)}</td>'
            f'<td class="volume">{_format_number(volume)}</td>'
            f'</tr>'
        )

    return (
        f'<table id="{table_id}">'
        f'<thead><tr>'
        f'<th>#</th><th>Ma</th><th>% LN</th>'
        f'<th>Mo</th><th>Dong</th><th>Cao</th><th>Thap</th><th>KL</th>'
        f'</tr></thead>'
        f'<tbody>{"".join(rows)}</tbody>'
        f'</table>'
    )


def generate_html_report(price_df, filtered_df, output_path=None):
    now = datetime.now(VN_TZ)

    if output_path is None:
        output_path = os.path.join(config.BASE_DIR, "report.html")

    total = len(price_df) if not price_df.empty else 0
    gainers = len(price_df[price_df["profit_pct"] > 0]) if total else 0
    losers = len(price_df[price_df["profit_pct"] < 0]) if total else 0
    above = len(filtered_df) if not filtered_df.empty else 0

    # Sort all data by profit descending
    all_sorted = price_df.sort_values("profit_pct", ascending=False) if total else price_df

    html = HTML_TEMPLATE.format(
        date=now.strftime("%Y-%m-%d"),
        timestamp=now.strftime("%Y-%m-%d %H:%M:%S"),
        source=config.DATA_SOURCE,
        total_symbols=total,
        gainers=gainers,
        losers=losers,
        above_threshold=above,
        threshold=config.PROFIT_THRESHOLD,
        profitable_table=_build_table(filtered_df, "tblProfit"),
        all_table=_build_table(all_sorted, "tblAll"),
    )

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)

    logger.info(f"HTML report saved: {output_path}")
    return output_path
