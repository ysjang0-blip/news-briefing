"""구글 뉴스 RSS에서 관심 키워드별 최신 기사를 수집해 data/raw/에 저장한다.

사용법: python scripts/fetch.py
설정: config.json 의 keywords 목록 사용
"""
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

RSS_SEARCH_URL = "https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text):
    return html.unescape(_TAG_RE.sub(" ", text)).strip()


def parse_rss(xml_text):
    """RSS XML 문자열 → 기사 dict 목록 (title, link, published, source, description)."""
    root = ET.fromstring(xml_text)
    articles = []
    for item in root.iter("item"):
        published = None
        pub_date = item.findtext("pubDate")
        if pub_date:
            try:
                published = parsedate_to_datetime(pub_date).astimezone(timezone.utc).isoformat()
            except (ValueError, TypeError):
                published = None
        articles.append({
            "title": (item.findtext("title") or "").strip(),
            "link": (item.findtext("link") or "").strip(),
            "published": published,
            "source": (item.findtext("source") or "").strip(),
            "description": _strip_html(item.findtext("description") or ""),
        })
    return articles


def filter_recent(articles, now, hours=24):
    """published 가 now 기준 최근 hours 이내인 기사만 남긴다. 날짜 없는 기사는 버린다."""
    cutoff = now - timedelta(hours=hours)
    recent = []
    for article in articles:
        if not article.get("published"):
            continue
        published = datetime.fromisoformat(article["published"])
        if published >= cutoff:
            recent.append(article)
    return recent


def dedupe(articles):
    """같은 링크 또는 같은 (제목, 언론사) 조합의 기사를 한 번만 남긴다."""
    seen_links = set()
    seen_title_source = set()
    result = []
    for article in articles:
        link = article.get("link")
        title_source = (article.get("title"), article.get("source"))
        if link in seen_links or title_source in seen_title_source:
            continue
        seen_links.add(link)
        seen_title_source.add(title_source)
        result.append(article)
    return result


def serialize_raw(date, collected_at, articles):
    """수집 결과를 '기사 1건 = 1줄' JSON 문자열로 만든다 (AI가 한 번에 읽기 쉽도록)."""
    article_lines = ",\n    ".join(json.dumps(a, ensure_ascii=False) for a in articles)
    return (
        "{\n"
        f'  "date": {json.dumps(date)},\n'
        f'  "collected_at": {json.dumps(collected_at)},\n'
        '  "articles": [\n'
        f"    {article_lines}\n"
        "  ]\n"
        "}\n"
    ) if articles else json.dumps(
        {"date": date, "collected_at": collected_at, "articles": []}, ensure_ascii=False, indent=2
    )


def fetch_keyword(keyword):
    """키워드 하나에 대한 구글 뉴스 RSS를 받아 기사 목록으로 반환한다. (네트워크 사용)"""
    url = RSS_SEARCH_URL.format(query=urllib.parse.quote(keyword))
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (news-briefing-bot)"})
    with urllib.request.urlopen(request, timeout=30) as response:
        xml_text = response.read().decode("utf-8")
    articles = parse_rss(xml_text)
    for article in articles:
        article["keyword"] = keyword
    return articles


def main():
    config = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)
    all_articles = []
    for keyword in config["keywords"]:
        try:
            articles = fetch_keyword(keyword)
        except Exception as e:  # 키워드 하나가 실패해도 나머지는 계속
            print(f"[warn] '{keyword}' 수집 실패: {e}", file=sys.stderr)
            continue
        recent = filter_recent(articles, now=now, hours=config.get("hours", 24))
        print(f"[info] '{keyword}': {len(recent)}건 (최근 {config.get('hours', 24)}시간)")
        all_articles.extend(recent)

    all_articles = dedupe(all_articles)
    all_articles.sort(key=lambda a: a["published"], reverse=True)

    kst = now.astimezone(timezone(timedelta(hours=9)))
    out_path = ROOT / "data" / "raw" / f"{kst:%Y-%m-%d}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        serialize_raw(f"{kst:%Y-%m-%d}", now.isoformat(), all_articles),
        encoding="utf-8",
    )
    print(f"[info] 총 {len(all_articles)}건 저장 → {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
