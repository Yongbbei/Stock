import json
import os
import re
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / "docs"
CONFIG_PATH = ROOT / "config.json"
KST = timezone(timedelta(hours=9))

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36"
SSL_CONTEXT = ssl._create_unverified_context()


def fetch_url(url: str, headers=None, timeout=15) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
        return resp.read()


def parse_int(text):
    if text is None:
        return None
    s = re.sub(r"[^0-9.-]", "", str(text))
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def get_naver_latest_close(code: str):
    """Fetch latest daily close from Naver Finance daily quote page."""
    url = f"https://finance.naver.com/item/sise_day.naver?code={code}"
    raw = fetch_url(url)
    # Naver Finance pages are usually EUC-KR/CP949.
    text = raw.decode("euc-kr", errors="ignore")
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", text, flags=re.S | re.I)
    for row in rows:
        if "tah p10 gray03" not in row:
            continue
        date_m = re.search(r"(\d{4}\.\d{2}\.\d{2})", row)
        if not date_m:
            continue
        nums = re.findall(r"<td class=\"num\">\s*<span[^>]*>(.*?)</span>", row, flags=re.S | re.I)
        if not nums:
            nums = re.findall(r"<td class=\"num\"[^>]*>\s*([^<]+)", row, flags=re.S | re.I)
        if len(nums) >= 1:
            close = parse_int(re.sub(r"<.*?>", "", nums[0]))
            if close:
                return {
                    "date": date_m.group(1).replace(".", "-"),
                    "close": close,
                    "source": "네이버금융"
                }
    raise RuntimeError(f"Could not parse latest close for {code}")


def naver_news_api(query: str, client_id: str, client_secret: str, display: int = 5):
    params = urllib.parse.urlencode({"query": query, "display": display, "sort": "date"})
    url = f"https://openapi.naver.com/v1/search/news.json?{params}"
    headers = {
        "X-Naver-Client-Id": client_id,
        "X-Naver-Client-Secret": client_secret,
    }
    raw = fetch_url(url, headers=headers)
    data = json.loads(raw.decode("utf-8"))
    out = []
    for item in data.get("items", []):
        title = re.sub(r"<.*?>", "", item.get("title", ""))
        desc = re.sub(r"<.*?>", "", item.get("description", ""))
        out.append({
            "title": title,
            "description": desc,
            "link": item.get("originallink") or item.get("link"),
            "pubDate": item.get("pubDate", "")
        })
    return out


def news_fallback_links(stock):
    kw = " ".join(stock.get("news_keywords", [stock["name"]])[:2])
    q = urllib.parse.quote(kw)
    return [{
        "title": f"{stock['name']} 관련 뉴스 검색",
        "description": "네이버 뉴스 검색 결과로 이동합니다. NAVER_CLIENT_ID / NAVER_CLIENT_SECRET을 GitHub Secrets에 넣으면 최신 기사 제목이 자동 표시됩니다.",
        "link": f"https://search.naver.com/search.naver?where=news&query={q}&sort=1",
        "pubDate": ""
    }]


def fmt_price(n):
    if n is None:
        return "-"
    return f"{n:,}원"


def fmt_pct(x):
    if x is None:
        return "-"
    sign = "+" if x > 0 else ""
    return f"{sign}{x:.2f}%"


def badge_class(x):
    if x is None:
        return "flat"
    if x > 0:
        return "up"
    if x < 0:
        return "down"
    return "flat"


def build_html(config, records, updated_at):
    title = escape(config.get("title", "관심종목 대시보드"))
    subtitle = escape(config.get("subtitle", ""))
    baseline_date = escape(config.get("baseline_date", ""))

    cards = []
    for r in records:
        news_items = "".join(
            f"<li><a href=\"{escape(n['link'])}\" target=\"_blank\" rel=\"noreferrer\">{escape(n['title'])}</a><p>{escape(n.get('description',''))}</p></li>"
            for n in r.get("news", [])[:5]
        )
        ret = r.get("return_pct")
        cards.append(f"""
        <article class=\"card\">
          <div class=\"card-head\">
            <div>
              <h2>{escape(r['name'])}</h2>
              <p class=\"code\">{escape(r['code'])} · {escape(r.get('market',''))}</p>
            </div>
            <div class=\"badge {badge_class(ret)}\">{fmt_pct(ret)}</div>
          </div>
          <div class=\"metrics\">
            <div><span>최신 종가</span><strong>{fmt_price(r.get('latest_close'))}</strong></div>
            <div><span>조회 기준일</span><strong>{escape(r.get('latest_date') or '-')}</strong></div>
            <div><span>{baseline_date} 종가</span><strong>{fmt_price(r.get('baseline_close'))}</strong></div>
          </div>
          <h3>관련 뉴스</h3>
          <ul class=\"news\">{news_items}</ul>
        </article>
        """)
    cards_html = "\n".join(cards)

    data_json = json.dumps(records, ensure_ascii=False)
    return f"""<!doctype html>
<html lang=\"ko\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1, viewport-fit=cover\" />
  <meta name=\"theme-color\" content=\"#111827\" />
  <meta name=\"apple-mobile-web-app-capable\" content=\"yes\" />
  <meta name=\"apple-mobile-web-app-status-bar-style\" content=\"black-translucent\" />
  <meta name=\"apple-mobile-web-app-title\" content=\"관심종목\" />
  <link rel=\"manifest\" href=\"./manifest.json\" />
  <link rel=\"apple-touch-icon\" href=\"./icons/icon-192.png\" />
  <title>{title}</title>
  <style>
    :root {{ --bg:#f4f6f8; --card:#fff; --text:#111827; --muted:#6b7280; --line:#e5e7eb; --up:#dc2626; --down:#2563eb; --flat:#4b5563; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans KR', Arial, sans-serif; background:var(--bg); color:var(--text); }}
    header {{ padding: 28px 18px 18px; background: linear-gradient(135deg, #111827, #374151); color:white; }}
    .wrap {{ max-width: 1100px; margin: 0 auto; }}
    h1 {{ margin:0; font-size: clamp(24px, 5vw, 40px); letter-spacing:-0.04em; }}
    .sub {{ margin:10px 0 0; color:#d1d5db; line-height:1.5; }}
    .updated {{ margin-top:10px; font-size:14px; color:#e5e7eb; }}
    main {{ padding: 18px; }}
    .grid {{ display:grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap:16px; }}
    .card {{ background:var(--card); border:1px solid var(--line); border-radius:20px; padding:18px; box-shadow: 0 8px 24px rgba(17,24,39,.06); }}
    .card-head {{ display:flex; justify-content:space-between; gap:14px; align-items:flex-start; }}
    h2 {{ margin:0; font-size:22px; letter-spacing:-0.04em; }}
    .code {{ margin:6px 0 0; color:var(--muted); font-size:14px; }}
    .badge {{ flex:0 0 auto; border-radius:999px; padding:8px 12px; color:white; font-weight:700; font-size:16px; }}
    .badge.up {{ background:var(--up); }} .badge.down {{ background:var(--down); }} .badge.flat {{ background:var(--flat); }}
    .metrics {{ display:grid; grid-template-columns: repeat(3,1fr); gap:10px; margin:18px 0; }}
    .metrics div {{ background:#f9fafb; border:1px solid var(--line); border-radius:14px; padding:12px; }}
    .metrics span {{ display:block; color:var(--muted); font-size:12px; margin-bottom:6px; }}
    .metrics strong {{ font-size:18px; letter-spacing:-0.03em; }}
    h3 {{ margin:16px 0 10px; font-size:16px; }}
    .news {{ padding-left:18px; margin:0; }}
    .news li {{ margin:10px 0; }}
    .news a {{ color:#111827; font-weight:700; text-decoration:none; }}
    .news p {{ margin:4px 0 0; color:var(--muted); font-size:13px; line-height:1.45; }}
    footer {{ padding: 8px 18px 28px; color:var(--muted); font-size:13px; text-align:center; }}
    .install-tip {{ margin: 14px 0 0; padding: 12px 14px; border: 1px solid rgba(255,255,255,.2); border-radius: 14px; background: rgba(255,255,255,.08); color:#f9fafb; font-size:14px; line-height:1.5; }}
    @media (max-width: 760px) {{ .grid {{ grid-template-columns:1fr; }} .metrics {{ grid-template-columns:1fr; }} .card {{ border-radius:18px; }} }}
  </style>
</head>
<body>
  <header>
    <div class=\"wrap\">
      <h1>{title}</h1>
      <p class=\"sub\">{subtitle}</p>
      <div class=\"updated\">마지막 업데이트: {escape(updated_at)} · 기준일: {baseline_date}</div>
      <div class=\"install-tip\">모바일 앱처럼 쓰기: 아이폰은 Safari 공유 버튼 → 홈 화면에 추가, 안드로이드는 Chrome 메뉴 → 홈 화면에 추가/앱 설치</div>
    </div>
  </header>
  <main><div class=\"wrap grid\">{cards_html}</div></main>
  <footer>가격은 네이버금융 일별시세 기준 최신 종가입니다. 투자 판단의 책임은 이용자에게 있습니다.</footer>
  <script id=\"dashboard-data\" type=\"application/json\">{escape(data_json)}</script>
  <script>
    if ('serviceWorker' in navigator) {{
      window.addEventListener('load', () => navigator.serviceWorker.register('./service-worker.js'));
    }}
  </script>
</body>
</html>
"""


def main():
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    client_id = os.environ.get("NAVER_CLIENT_ID")
    client_secret = os.environ.get("NAVER_CLIENT_SECRET")

    records = []
    for stock in config["stocks"]:
        print(f"Fetching price: {stock['name']} ({stock['code']})")
        latest_close = None
        latest_date = None
        error = None
        try:
            p = get_naver_latest_close(stock["code"])
            latest_close = p["close"]
            latest_date = p["date"]
        except Exception as e:
            error = str(e)
            print(f"  price failed: {error}", file=sys.stderr)

        baseline = stock["baseline_close"]
        return_pct = None
        if latest_close and baseline:
            return_pct = (latest_close / baseline - 1) * 100

        query = " ".join(stock.get("news_keywords") or [stock["name"]])
        try:
            news = naver_news_api(query, client_id, client_secret) if client_id and client_secret else news_fallback_links(stock)
        except Exception as e:
            print(f"  news failed: {e}", file=sys.stderr)
            news = news_fallback_links(stock)

        records.append({
            "name": stock["name"],
            "code": stock["code"],
            "market": stock.get("market", ""),
            "baseline_close": baseline,
            "latest_close": latest_close,
            "latest_date": latest_date,
            "return_pct": return_pct,
            "news": news,
            "error": error,
        })

    DOCS.mkdir(exist_ok=True)
    updated_at = datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")
    (DOCS / "data.json").write_text(json.dumps({"updated_at": updated_at, "records": records}, ensure_ascii=False, indent=2), encoding="utf-8")
    (DOCS / "index.html").write_text(build_html(config, records, updated_at), encoding="utf-8")
    print("Done. Site written to docs/index.html")


if __name__ == "__main__":
    main()
