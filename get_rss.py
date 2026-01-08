#!/usr/bin/env python3
import json
import socket
import sys
import time
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

import requests


FEED_URL = "https://rss.app/feeds/v1.1/tIRm3Gbe3dWdpD3Z.json"  # RSS.app生成的JSON Feed
OUT_PATH = "reuters_rss.jsonl"
TIMEOUT_SEC = 15
MAX_RETRIES = 3
RETRY_DELAY = 2


def _text(el, tag_names):
    """Try multiple tag names and return stripped text."""
    for tag in tag_names:
        found = el.find(tag)
        if found is not None and found.text:
            return found.text.strip()
    return None


def parse_json_feed(json_data):
    """
    Parse JSON Feed format (https://jsonfeed.org/).
    Returns list[dict] with: title, link, pub_date, guid
    """
    # 处理bytes输入
    if isinstance(json_data, bytes):
        json_data = json_data.decode('utf-8')
    # 处理字符串输入
    if isinstance(json_data, str):
        json_data = json.loads(json_data)
    # 现在应该是dict
    if not isinstance(json_data, dict):
        raise ValueError("Invalid JSON Feed format")

    if "version" not in json_data or "items" not in json_data:
        raise ValueError("Not a valid JSON Feed (missing version or items)")

    items = []
    for item in json_data.get("items", []):
        # JSON Feed格式: id, url, title, date_published, content_text, content_html等
        items.append(
            {
                "title": item.get("title"),
                "link": item.get("url"),  # JSON Feed使用"url"而不是"link"
                "pub_date": item.get("date_published"),
                "guid": item.get("id"),
                "content_text": item.get("content_text"),
                "content_html": item.get("content_html"),
                "authors": item.get("authors", []),
                "image": item.get("image"),
                "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )

    return items


def parse_rss(xml_bytes):
    """
    Parse RSS 2.0-ish XML.
    Returns list[dict] with: title, link, pub_date, guid
    """
    root = ET.fromstring(xml_bytes)

    # RSS 2.0: <rss><channel><item>...</item></channel></rss>
    channel = root.find("channel")
    if channel is None:
        raise ValueError("Not an RSS feed (missing <channel>)")

    items = []
    for item in channel.findall("item"):
        title = _text(item, ["title"])
        link = _text(item, ["link"])
        pub_date = _text(item, ["pubDate"])
        guid = _text(item, ["guid"])

        items.append(
            {
                "title": title,
                "link": link,
                "pub_date": pub_date,
                "guid": guid,
                "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )

    return items


def parse_feed(content, content_type=None):
    """
    自动检测并解析RSS XML或JSON Feed格式
    """
    # 尝试检测格式
    content_str = content[:100].decode('utf-8', errors='ignore').strip()

    # 检查是否是JSON Feed
    if content_str.startswith('{') or '.json' in (content_type or '').lower():
        try:
            return parse_json_feed(content)
        except (json.JSONDecodeError, ValueError) as e:
            raise ValueError(f"JSON Feed解析失败: {e}")

    # 检查是否是RSS XML
    elif content_str.startswith('<') or 'xml' in (content_type or '').lower():
        try:
            return parse_rss(content)
        except (ET.ParseError, ValueError) as e:
            raise ValueError(f"RSS XML解析失败: {e}")

    else:
        # 尝试JSON Feed
        try:
            return parse_json_feed(content)
        except:
            # 尝试RSS XML
            try:
                return parse_rss(content)
            except:
                raise ValueError("无法识别feed格式，既不是有效的JSON Feed也不是RSS XML")


def test_dns_resolution(hostname):
    """测试DNS解析"""
    try:
        ip = socket.gethostbyname(hostname)
        print(f"DNS解析成功: {hostname} -> {ip}")
        return True
    except socket.gaierror as e:
        print(f"DNS解析失败: {hostname}")
        print(f"  错误: {e}")
        return False


def test_url(url, quick_test=True):
    """快速测试URL是否可用（支持RSS XML和JSON Feed）"""
    headers = {
        "User-Agent": "rss-demo-fetcher/0.1 (+https://example.local)",
        "Accept": "application/json, application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    }
    try:
        resp = requests.get(url, timeout=5 if quick_test else TIMEOUT_SEC, headers=headers, allow_redirects=True)
        if resp.status_code == 200:
            # 检查是否是有效的feed（RSS XML或JSON Feed）
            content = resp.content[:500].decode('utf-8', errors='ignore').strip()
            content_lower = content.lower()

            # 检查JSON Feed
            if content.startswith('{') and ('"version"' in content or '"items"' in content):
                return True, resp
            # 检查RSS XML
            elif '<rss' in content_lower or '<feed' in content_lower or 'xml' in content_lower:
                return True, resp
        return False, None
    except Exception as e:
        return False, None


def find_working_url():
    """尝试多个可能的URL，找到可用的"""
    candidate_urls = [
        # 优先使用RSS.app生成的JSON Feed
        "https://rss.app/feeds/v1.1/tIRm3Gbe3dWdpD3Z.json",
        # 常见的路透社RSS feed URL格式（可能已不可用）
        "https://feeds.reuters.com/reuters/topNews",
        "http://feeds.reuters.com/reuters/topNews",
        "https://feeds.reuters.com/Reuters/worldNews",
        "http://feeds.reuters.com/Reuters/worldNews",
        "https://feeds.reuters.com/Reuters/domesticNews",
        "http://feeds.reuters.com/Reuters/domesticNews",
        "https://feeds.reuters.com/reuters/businessNews",
        "http://feeds.reuters.com/reuters/businessNews",
        "https://www.reuters.com/rssFeed/worldNews",
        "https://www.reuters.com/rssFeed/topNews",
        "https://www.reuters.com/rssFeed/businessNews",
        "http://www.reuters.com/rssFeed/worldNews",
        "http://www.reuters.com/rssFeed/topNews",
    ]

    print("[测试] 正在测试多个可能的URL...\n")
    for url in candidate_urls:
        print(f"  测试: {url}")
        is_valid, resp = test_url(url, quick_test=True)
        if is_valid:
            feed_type = "JSON Feed" if url.endswith('.json') or resp.content[:1] == b'{' else "RSS XML"
            print(f"  ✓ 找到可用的URL ({feed_type}): {url}\n")
            return url, resp
        else:
            print(f"  ✗ 不可用\n")

    return None, None


def fetch_with_retry(url, max_retries=MAX_RETRIES, retry_delay=RETRY_DELAY):
    """带重试机制的HTTP请求"""
    headers = {
        "User-Agent": "rss-demo-fetcher/0.1 (+https://example.local)",
        "Accept": "application/json, application/rss+xml, application/xml;q=0.9, */*;q=0.8",
    }

    for attempt in range(1, max_retries + 1):
        try:
            print(f"尝试 {attempt}/{max_retries}...")
            resp = requests.get(url, timeout=TIMEOUT_SEC, headers=headers, allow_redirects=True)
            resp.raise_for_status()
            return resp
        except requests.exceptions.Timeout:
            print(f"  超时 (>{TIMEOUT_SEC}秒)")
            if attempt < max_retries:
                print(f"  {retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                raise
        except requests.exceptions.ConnectionError as e:
            print(f"  连接错误: {e}")
            if attempt < max_retries:
                print(f"  {retry_delay}秒后重试...")
                time.sleep(retry_delay)
            else:
                raise
        except requests.exceptions.RequestException as e:
            print(f"  请求错误: {e}")
            raise

    return None


def main():
    from urllib.parse import urlparse

    # 如果FEED_URL已设置且不是默认的路透社URL，直接使用它
    use_direct_url = FEED_URL and not FEED_URL.startswith("https://feeds.reuters.com")

    if use_direct_url:
        print(f"[使用] 直接使用指定的URL: {FEED_URL}")
        working_url = FEED_URL
        cached_resp = None
    else:
        # 首先尝试找到可用的URL
        working_url, cached_resp = find_working_url()

        if working_url is None:
            print("\n[错误] 未找到可用的路透社RSS feed URL")
            print("\n[建议]")
            print("1. 检查网络连接")
            print("2. 访问 https://www.reuters.com 查看最新的RSS feed链接")
            print("3. 如果在受限网络环境，可能需要配置代理")
            print("4. 尝试使用其他DNS服务器 (如 8.8.8.8 或 1.1.1.1)")
            print("5. 考虑使用RSS.app等第三方服务创建feed")
            sys.exit(1)

    # 如果快速测试已经获取了响应，直接使用；否则重新获取完整内容
    if cached_resp is not None:
        print(f"[使用] 使用找到的URL: {working_url}")
        resp = cached_resp
        # 如果只是快速测试，需要重新获取完整内容
        if len(resp.content) < 1000:
            print("[获取] 获取完整内容...")
            resp = fetch_with_retry(working_url)
    else:
        if not use_direct_url:
            print(f"[使用] 使用找到的URL: {working_url}")
        print(f"[获取] 开始获取RSS feed...")
        try:
            resp = fetch_with_retry(working_url)
        except Exception as e:
            print(f"\n[错误] 获取失败: {e}")
            print("\n[建议]")
            print("1. 检查网络连接和防火墙设置")
            print("2. 如果在受限网络环境，可能需要配置代理")
            print("   例如: export https_proxy=http://proxy.example.com:8080")
            sys.exit(1)

    print(f"✓ 成功获取 (状态码: {resp.status_code})")

    # 检测feed类型
    content_type = resp.headers.get('Content-Type', '').lower()
    feed_type = "JSON Feed" if working_url.endswith('.json') or resp.content[:1] == b'{' else "RSS XML"
    print(f"✓ 检测到格式: {feed_type}")

    # 解析feed（自动检测格式）
    try:
        items = parse_feed(resp.content, content_type)
        print(f"✓ 解析成功，共 {len(items)} 条")
    except Exception as e:
        print(f"\n[错误] Feed解析失败: {e}")
        print(f"响应内容预览 (前500字符):")
        print(resp.content[:500].decode('utf-8', errors='ignore'))
        sys.exit(1)

    # 打印前 10 条
    print("\n[预览] 前10条新闻:")
    for i, it in enumerate(items[:10], start=1):
        print(f"\n[{i}] {it.get('title')}")
        print(f"    pubDate: {it.get('pub_date')}")
        print(f"    link:    {it.get('link')}")

    # 追加写入 jsonl（便于后续 replay 成 Kafka 事件流）
    with open(OUT_PATH, "a", encoding="utf-8") as f:
        for it in items:
            # 更新feed_url为实际使用的URL
            it['feed_url'] = working_url
            f.write(json.dumps(it, ensure_ascii=False) + "\n")

    print(f"\n✓ 已追加到: {OUT_PATH}")
    print(f"✓ 使用的URL: {working_url}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
