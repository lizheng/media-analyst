"""
URL解析模块测试

测试 extract_urls_from_text, parse_douyin_url, extract_douyin_links 等纯函数
"""

import pytest
from media_analyst.core.url_parser import (
    ParsedLink,
    extract_urls_from_text,
    parse_douyin_url,
    extract_douyin_links,
    normalize_douyin_links,
    format_link_for_display,
)


# ========== extract_urls_from_text 测试 ==========

def test_extract_single_url_from_text():
    """从简单文本中提取单个URL"""
    text = "看这里 https://v.douyin.com/abc123/ 很有趣"
    urls = extract_urls_from_text(text)
    assert urls == ["https://v.douyin.com/abc123/"]


def test_extract_multiple_urls_from_text():
    """从文本中提取多个URL"""
    text = "视频1: https://v.douyin.com/abc/ 视频2: https://v.douyin.com/def/"
    urls = extract_urls_from_text(text)
    assert len(urls) == 2
    assert "https://v.douyin.com/abc/" in urls
    assert "https://v.douyin.com/def/" in urls


def test_extract_from_share_text():
    """从抖音分享文本中提取链接"""
    # 真实的抖音分享文本格式
    text = "6.61 w@f.bn 10/31 DUl:/ 1.21.11极限孤岛生存1~14天合集一口气看完！ # 我的世界中国版 https://v.douyin.com/awMri5tb7nw/ 复制此链接，打开Dou音搜索，直接观看视频！"
    urls = extract_urls_from_text(text)
    assert len(urls) == 1
    assert urls[0] == "https://v.douyin.com/awMri5tb7nw/"


def test_extract_urls_comma_separated():
    """提取逗号分隔的URL - 注意：逗号会被当作URL的一部分，实际处理在extract_douyin_links中按逗号分割"""
    text = "https://v.douyin.com/abc/,https://v.douyin.com/def/"
    urls = extract_urls_from_text(text)
    # 逗号被包含在URL中，extract_douyin_links会先按逗号分割再提取
    assert len(urls) == 1
    # 但 extract_douyin_links 会正确处理
    results = extract_douyin_links(text)
    assert len(results) == 2


def test_extract_empty_text():
    """空文本返回空列表"""
    assert extract_urls_from_text("") == []
    assert extract_urls_from_text("   ") == []
    assert extract_urls_from_text(None or "") == []


def test_extract_no_urls():
    """无URL文本返回空列表"""
    text = "这是一段普通文本，没有链接"
    assert extract_urls_from_text(text) == []


def test_extract_deduplicate_urls():
    """相同URL去重"""
    text = "https://v.douyin.com/abc/ https://v.douyin.com/abc/"
    urls = extract_urls_from_text(text)
    assert len(urls) == 1


# ========== parse_douyin_url 测试 ==========

def test_parse_short_link():
    """解析抖音短链"""
    url = "https://v.douyin.com/ci4JcA86h-g/"
    result = parse_douyin_url(url)
    assert result is not None
    assert result.link_type == "short"
    assert result.original == url
    assert result.video_id == "ci4JcA86h-g"  # 短链code


def test_parse_video_url():
    """解析视频页URL"""
    url = "https://www.douyin.com/video/7605333789232876826"
    result = parse_douyin_url(url)
    assert result is not None
    assert result.link_type == "video"
    assert result.video_id == "7605333789232876826"
    assert result.normalized == "https://www.douyin.com/video/7605333789232876826"


def test_parse_note_url():
    """解析图文页URL"""
    url = "https://www.douyin.com/note/7605333789232876826"
    result = parse_douyin_url(url)
    assert result is not None
    assert result.link_type == "note"
    assert result.video_id == "7605333789232876826"
    assert result.normalized == "https://www.douyin.com/video/7605333789232876826"


def test_parse_modal_url():
    """解析精选页URL（带modal_id）"""
    url = "https://www.douyin.com/jingxuan?modal_id=7605333789232876826"
    result = parse_douyin_url(url)
    assert result is not None
    assert result.link_type == "modal"
    assert result.video_id == "7605333789232876826"
    assert result.normalized == "https://www.douyin.com/video/7605333789232876826"


def test_parse_mobile_url():
    """解析移动端分享URL"""
    url = "https://m.douyin.com/share/video/7605333789232876826"
    result = parse_douyin_url(url)
    assert result is not None
    assert result.link_type == "mobile"
    assert result.video_id == "7605333789232876826"
    assert result.normalized == "https://www.douyin.com/video/7605333789232876826"


def test_parse_video_url_without_www():
    """解析不带www的视频URL"""
    url = "https://douyin.com/video/7605333789232876826"
    result = parse_douyin_url(url)
    assert result is not None
    assert result.video_id == "7605333789232876826"


def test_parse_invalid_url():
    """无效URL返回None"""
    assert parse_douyin_url("https://example.com/video/123") is None
    assert parse_douyin_url("") is None
    assert parse_douyin_url("not a url") is None


# ========== extract_douyin_links 测试 ==========

def test_extract_share_text():
    """从分享文本中提取链接"""
    text = "6.61 w@f.bn https://v.douyin.com/awMri5tb7nw/ 复制此链接"
    results = extract_douyin_links(text)
    assert len(results) == 1
    assert results[0].link_type == "short"
    assert results[0].video_id == "awMri5tb7nw"


def test_extract_comma_separated_urls():
    """提取逗号分隔的URL"""
    text = "https://www.douyin.com/video/123,https://www.douyin.com/note/456"
    results = extract_douyin_links(text)
    assert len(results) == 2
    assert results[0].video_id == "123"
    assert results[1].video_id == "456"


def test_extract_mixed_urls():
    """提取混合类型的URL"""
    text = "https://v.douyin.com/short/, https://www.douyin.com/video/123, https://www.douyin.com/jingxuan?modal_id=456"
    results = extract_douyin_links(text)
    assert len(results) == 3


def test_extract_with_resolver():
    """提取时使用短链解析器"""
    def mock_resolver(url):
        # 模拟短链解析，返回视频页URL
        return "https://www.douyin.com/video/123456"

    text = "https://v.douyin.com/abc123/"
    results = extract_douyin_links(text, mock_resolver)

    assert len(results) == 1
    assert results[0].link_type == "video"  # resolve后变为video类型
    assert results[0].video_id == "123456"
    assert results[0].normalized == "https://www.douyin.com/video/123456"


def test_extract_resolver_failure():
    """短链解析失败时保留原始短链"""
    def failing_resolver(url):
        raise Exception("网络错误")

    text = "https://v.douyin.com/abc123/"
    results = extract_douyin_links(text, failing_resolver)

    assert len(results) == 1
    assert results[0].link_type == "short"  # 保留短链类型


def test_extract_empty_input():
    """空输入返回空列表"""
    assert extract_douyin_links("") == []
    assert extract_douyin_links("   ") == []
    assert extract_douyin_links("没有链接的文本") == []


# ========== normalize_douyin_links 测试 ==========

def test_normalize_simple():
    """标准化链接"""
    text = "https://www.douyin.com/note/123"
    links = normalize_douyin_links(text)
    assert links == ["https://www.douyin.com/video/123"]


def test_normalize_multiple():
    """标准化多个链接"""
    text = "https://www.douyin.com/video/123,https://www.douyin.com/note/456"
    links = normalize_douyin_links(text)
    assert len(links) == 2
    assert "https://www.douyin.com/video/123" in links
    assert "https://www.douyin.com/video/456" in links


# ========== format_link_for_display 测试 ==========

def test_format_display():
    """格式化显示"""
    link = ParsedLink(
        original="https://v.douyin.com/abc/",
        normalized="https://www.douyin.com/video/123",
        video_id="123",
        link_type="video"
    )
    display = format_link_for_display(link)
    assert "视频ID: 123" in display
    assert "视频页" in display


def test_format_display_all_types():
    """格式化所有类型"""
    types = ["short", "video", "note", "modal", "mobile"]
    for link_type in types:
        link = ParsedLink(
            original="test",
            normalized="test",
            video_id="123",
            link_type=link_type
        )
        display = format_link_for_display(link)
        assert "视频ID: 123" in display
