"""scripts/fetch.py 의 순수 로직(RSS 파싱, 24시간 필터, 중복 제거) 테스트."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from fetch import parse_rss, filter_recent, dedupe, serialize_raw, rss_url, keyword_plan

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>"금리" - Google News</title>
  <item>
    <title>한은, 기준금리 동결 - 한국경제</title>
    <link>https://news.google.com/rss/articles/AAA111</link>
    <pubDate>Fri, 15 Aug 2026 01:00:00 GMT</pubDate>
    <description>&lt;a href="https://example.com/1"&gt;한은, 기준금리 동결&lt;/a&gt;&amp;nbsp;&lt;font color="#6f6f6f"&gt;한국경제&lt;/font&gt;</description>
    <source url="https://www.hankyung.com">한국경제</source>
  </item>
  <item>
    <title>코스피 사상 최고치 - 연합뉴스</title>
    <link>https://news.google.com/rss/articles/BBB222</link>
    <pubDate>Wed, 13 Aug 2026 01:00:00 GMT</pubDate>
    <description>코스피 사상 최고치</description>
    <source url="https://www.yna.co.kr">연합뉴스</source>
  </item>
</channel>
</rss>
"""


class TestParseRss(unittest.TestCase):
    def test_parses_items_with_fields(self):
        articles = parse_rss(SAMPLE_RSS)
        self.assertEqual(len(articles), 2)
        first = articles[0]
        self.assertEqual(first["title"], "한은, 기준금리 동결 - 한국경제")
        self.assertEqual(first["link"], "https://news.google.com/rss/articles/AAA111")
        self.assertEqual(first["source"], "한국경제")
        # pubDate 는 ISO 형식(UTC)으로 변환되어야 한다
        self.assertEqual(first["published"], "2026-08-15T01:00:00+00:00")

    def test_strips_html_from_description(self):
        articles = parse_rss(SAMPLE_RSS)
        self.assertNotIn("<", articles[0]["description"])
        self.assertIn("한은", articles[0]["description"])

    def test_empty_channel_returns_empty_list(self):
        empty = '<?xml version="1.0"?><rss version="2.0"><channel></channel></rss>'
        self.assertEqual(parse_rss(empty), [])


class TestFilterRecent(unittest.TestCase):
    def test_keeps_only_last_24_hours(self):
        now = datetime(2026, 8, 15, 7, 0, tzinfo=timezone.utc)
        articles = parse_rss(SAMPLE_RSS)
        recent = filter_recent(articles, now=now, hours=24)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["link"], "https://news.google.com/rss/articles/AAA111")

    def test_article_without_date_is_dropped(self):
        now = datetime(2026, 8, 15, 7, 0, tzinfo=timezone.utc)
        articles = [{"title": "t", "link": "l", "published": None}]
        self.assertEqual(filter_recent(articles, now=now, hours=24), [])


class TestDedupe(unittest.TestCase):
    def test_removes_same_link(self):
        a = {"title": "A", "link": "https://x/1", "source": "s1"}
        b = {"title": "B", "link": "https://x/1", "source": "s2"}
        self.assertEqual(dedupe([a, b]), [a])

    def test_removes_same_title_and_source(self):
        a = {"title": "같은 제목", "link": "https://x/1", "source": "s1"}
        b = {"title": "같은 제목", "link": "https://x/2", "source": "s1"}
        c = {"title": "같은 제목", "link": "https://x/3", "source": "s2"}
        self.assertEqual(dedupe([a, b, c]), [a, c])


class TestRssUrl(unittest.TestCase):
    def test_korean_edition_is_default(self):
        url = rss_url("환율")
        self.assertIn("hl=ko", url)
        self.assertIn("gl=KR", url)
        self.assertIn("ceid=KR%3Ako", url.replace("KR:ko", "KR%3Ako"))  # 인코딩 여부 무관

    def test_us_edition(self):
        url = rss_url("Hims & Hers", region="us")
        self.assertIn("hl=en-US", url)
        self.assertIn("gl=US", url)

    def test_keyword_is_url_encoded(self):
        url = rss_url("Hims & Hers", region="us")
        self.assertNotIn(" & ", url)
        self.assertIn("Hims%20%26%20Hers", url)


class TestKeywordPlan(unittest.TestCase):
    def test_combines_korean_and_us_keywords(self):
        config = {"keywords": ["환율"], "keywords_us": ["Hims & Hers"]}
        self.assertEqual(
            keyword_plan(config),
            [("환율", "kr"), ("Hims & Hers", "us")],
        )

    def test_missing_us_list_is_ok(self):
        config = {"keywords": ["환율"]}
        self.assertEqual(keyword_plan(config), [("환율", "kr")])


class TestSerializeRaw(unittest.TestCase):
    def test_one_article_per_line_and_valid_json(self):
        import json
        articles = [
            {"title": "제목1", "link": "https://x/1"},
            {"title": "제목2", "link": "https://x/2"},
        ]
        text = serialize_raw("2026-08-15", "2026-08-14T22:00:00+00:00", articles)
        parsed = json.loads(text)
        self.assertEqual(parsed["date"], "2026-08-15")
        self.assertEqual(parsed["articles"], articles)
        # 기사 한 건이 정확히 한 줄에 들어가야 AI가 읽기 쉽다
        lines_with_title = [l for l in text.splitlines() if '"title"' in l]
        self.assertEqual(len(lines_with_title), 2)
        for line in lines_with_title:
            self.assertIn('"link"', line)


if __name__ == "__main__":
    unittest.main()
