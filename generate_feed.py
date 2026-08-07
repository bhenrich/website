#!/usr/bin/env python3

from __future__ import annotations

from bs4 import BeautifulSoup
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
from urllib.parse import urljoin
import re
import xml.etree.ElementTree as ET


# =========================
# Editable feed settings
# =========================

SITE_URL = "https://netcat.systems/"
BLOG_PATH = "blog.html"
FEED_PATH = "feed.xml"

FEED_TITLE = "a netcat's rambles"
FEED_LINK = urljoin(SITE_URL, BLOG_PATH)
FEED_DESCRIPTION = (
    "Welcome traveller, to this little place in the ever-growing internet. "
    "This is a dumping place for topics that interest me, sidequests I've been on and a place for me to publish anything I make."
)
FEED_LANGUAGE = "en-gb"
FEED_MANAGING_EDITOR = ""
FEED_WEBMASTER = "critter.cafe/@lunatiq"
FEED_COPYRIGHT = ""
FEED_CATEGORY = ""
FEED_DOCS = "https://www.rssboard.org/rss-specification"
FEED_GENERATOR = ""
FEED_TTL = "60"

# Maximum number of items to emit; set to None to include all posts.
MAX_ITEMS = None


ROOT = Path(__file__).resolve().parent
BLOG_FILE = ROOT / BLOG_PATH
OUTPUT_FILE = ROOT / FEED_PATH


def collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def parse_html(path: Path) -> BeautifulSoup:
    return BeautifulSoup(path.read_text(encoding="utf-8"), "html.parser")


def absolute_url(href: str) -> str:
    return urljoin(SITE_URL, href.strip())


def iso_to_rfc2822(value: str) -> str:
    dt = datetime.fromisoformat(value)
    return format_datetime(dt)


def text_or_none(node) -> str | None:
    if not node:
        return None
    text = collapse_ws(node.get_text(" ", strip=True))
    return text or None


def meta_content(soup: BeautifulSoup, *, prop: str | None = None, name: str | None = None) -> str | None:
    if prop:
        tag = soup.find("meta", attrs={"property": prop})
        if tag and tag.get("content"):
            return collapse_ws(tag["content"])
    if name:
        tag = soup.find("meta", attrs={"name": name})
        if tag and tag.get("content"):
            return collapse_ws(tag["content"])
    return None


def local_path_from_url(url: str) -> Path:
    rel = url.replace(SITE_URL, "", 1).lstrip("/")
    return ROOT / rel


def first_article_paragraph(article: BeautifulSoup) -> str | None:
    for p in article.find_all("p"):
        text = text_or_none(p)
        if text:
            return text
    return None


def get_post_metadata(post_url: str) -> tuple[str | None, str | None]:
    post_path = local_path_from_url(post_url)
    if not post_path.exists():
        return None, None

    soup = parse_html(post_path)
    article = soup.find("article")

    title = None
    if article:
        title = text_or_none(article.find("h1")) or text_or_none(article.find("h2"))

    if not title and soup.title and soup.title.string:
        raw = collapse_ws(soup.title.string)
        title = re.sub(r"\s*-\s*netcat\.systems\s*$", "", raw, flags=re.IGNORECASE)

    description = (
        meta_content(soup, prop="og:description")
        or meta_content(soup, name="description")
    )

    if not description and article:
        description = first_article_paragraph(article)

    return title, description


def build_item_data() -> list[dict[str, str]]:
    soup = parse_html(BLOG_FILE)
    items: list[dict[str, str]] = []

    for post in soup.select("section.posts article.post"):
        link_el = post.select_one("a[href]")
        time_el = post.select_one("time[datetime]")
        summary_el = post.select_one("p")

        if not link_el or not time_el:
            continue

        href = link_el["href"]
        post_url = absolute_url(href)

        list_title = text_or_none(link_el)
        list_summary = text_or_none(summary_el) or ""
        pub_date = iso_to_rfc2822(time_el["datetime"])

        post_title, post_description = get_post_metadata(post_url)

        final_title = post_title or list_title or post_url
        final_description = post_description or list_summary or final_title

        item = {
            "title": final_title,
            "link": post_url,
            "guid": post_url,
            "pubDate": pub_date,
            "description": final_description,
        }
        items.append(item)

    if MAX_ITEMS is not None:
        items = items[:MAX_ITEMS]

    return items


def add_text_element(parent: ET.Element, tag: str, text: str) -> ET.Element:
    el = ET.SubElement(parent, tag)
    el.text = text
    return el


def indent_tree(elem: ET.Element, level: int = 0) -> None:
    indent = "\n" + ("  " * level)
    child_indent = "\n" + ("  " * (level + 1))

    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = child_indent
        for child in elem:
            indent_tree(child, level + 1)
        if not elem[-1].tail or not elem[-1].tail.strip():
            elem[-1].tail = indent
    if level and (not elem.tail or not elem.tail.strip()):
        elem.tail = indent


def build_feed_xml(items: list[dict[str, str]]) -> ET.ElementTree:
    rss = ET.Element(
        "rss",
        {
            "version": "2.0",
            "xmlns:atom": "http://www.w3.org/2005/Atom",
        },
    )

    channel = ET.SubElement(rss, "channel")

    add_text_element(channel, "title", FEED_TITLE)
    add_text_element(channel, "link", FEED_LINK)
    add_text_element(channel, "description", FEED_DESCRIPTION)
    add_text_element(channel, "language", FEED_LANGUAGE)
    add_text_element(channel, "docs", FEED_DOCS)
    add_text_element(channel, "generator", FEED_GENERATOR)
    add_text_element(channel, "ttl", FEED_TTL)

    if FEED_MANAGING_EDITOR:
        add_text_element(channel, "managingEditor", FEED_MANAGING_EDITOR)
    if FEED_WEBMASTER:
        add_text_element(channel, "webMaster", FEED_WEBMASTER)
    if FEED_COPYRIGHT:
        add_text_element(channel, "copyright", FEED_COPYRIGHT)
    if FEED_CATEGORY:
        add_text_element(channel, "category", FEED_CATEGORY)

    last_build = items[0]["pubDate"] if items else format_datetime(datetime.now(timezone.utc))
    add_text_element(channel, "lastBuildDate", last_build)

    ET.SubElement(
        channel,
        "{http://www.w3.org/2005/Atom}link",
        {
            "href": urljoin(SITE_URL, FEED_PATH),
            "rel": "self",
            "type": "application/rss+xml",
        },
    )

    for item in items:
        item_el = ET.SubElement(channel, "item")
        add_text_element(item_el, "title", item["title"])
        add_text_element(item_el, "link", item["link"])
        guid_el = add_text_element(item_el, "guid", item["guid"])
        guid_el.set("isPermaLink", "true")
        add_text_element(item_el, "pubDate", item["pubDate"])
        add_text_element(item_el, "description", item["description"])

    tree = ET.ElementTree(rss)
    indent_tree(rss)
    return tree


def main() -> None:
    items = build_item_data()

    if not items:
        print("No posts found in blog.html; generating an empty feed.")
    else:
        print(f"Found {len(items)} post(s) for feed generation:")
        for index, item in enumerate(items, start=1):
            print(f"  [{index}] {item['title']} -> {item['link']}")

    tree = build_feed_xml(items)
    tree.write(OUTPUT_FILE, encoding="utf-8", xml_declaration=True)

    print(f"Wrote pretty-printed RSS feed to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()