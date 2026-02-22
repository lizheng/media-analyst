"""
抖音链接解析与标准化模块

纯函数：将各种形式的抖音链接正则化为统一的视频页格式
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Callable
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class ParsedLink:
    """解析后的链接对象"""
    original: str          # 原始链接/文本
    normalized: str        # 标准化后的链接
    video_id: str          # 提取的视频ID
    link_type: str         # 原始类型: short, video, note, modal, text


class URLParseError(Exception):
    """URL解析错误"""
    pass


# ========== 正则表达式模式 ==========

# 从文本中提取URL
URL_PATTERN = re.compile(
    r'https?://'           # http:// 或 https://
    r'[^\s<>"{}|\\^`\[\]]+'  # 非空白和特殊字符
    r'[^\s<>"{}|\\^`\[\](),;.?!]'  # 不以标点结尾
)

# 抖音域名模式
DOUYIN_PATTERNS = {
    # 短链: https://v.douyin.com/xxxxx/
    'short': re.compile(
        r'https?://v\.douyin\.com/(?P<code>[a-zA-Z0-9_-]+)/?'
    ),
    # 视频页: https://www.douyin.com/video/xxxxx
    'video': re.compile(
        r'https?://(?:www\.)?douyin\.com/video/(?P<id>\d+)'
    ),
    # 图文页: https://www.douyin.com/note/xxxxx
    'note': re.compile(
        r'https?://(?:www\.)?douyin\.com/note/(?P<id>\d+)'
    ),
    # 精选页: https://www.douyin.com/jingxuan?modal_id=xxxxx
    'modal': re.compile(
        r'https?://(?:www\.)?douyin\.com/\w+\?modal_id=(?P<id>\d+)'
    ),
    # 移动端分享: https://m.douyin.com/share/video/xxxxx
    'mobile': re.compile(
        r'https?://m\.douyin\.com/share/video/(?P<id>\d+)'
    ),
}

# 标准化视频页模板
VIDEO_URL_TEMPLATE = "https://www.douyin.com/video/{video_id}"


def extract_urls_from_text(text: str) -> List[str]:
    """
    从文本中提取所有URL

    支持从抖音分享文本中提取链接，如：
    "6.61 w@f.bn 10/31 DUl:/ 1.21.11极限孤岛... https://v.douyin.com/xxxxx/ 复制此链接..."

    Args:
        text: 可能包含链接的文本

    Returns:
        提取到的URL列表（去重，保持顺序）

    Example:
        >>> extract_urls_from_text("看这里 https://v.douyin.com/abc/ 很有趣")
        ['https://v.douyin.com/abc/']
    """
    if not text or not text.strip():
        return []

    # 找到所有URL
    urls = URL_PATTERN.findall(text)

    # 去重但保持顺序
    seen = set()
    unique_urls = []
    for url in urls:
        # 清理可能的尾随标点
        url = url.rstrip('.,;:!?')
        if url not in seen:
            seen.add(url)
            unique_urls.append(url)

    return unique_urls


def parse_douyin_url(url: str) -> Optional[ParsedLink]:
    """
    解析单个抖音URL，提取视频ID

    支持的格式：
    - 短链: https://v.douyin.com/xxxxx/ (需要后续resolve)
    - 视频页: https://www.douyin.com/video/xxxxx
    - 图文页: https://www.douyin.com/note/xxxxx
    - 精选页: https://www.douyin.com/jingxuan?modal_id=xxxxx
    - 移动端: https://m.douyin.com/share/video/xxxxx

    Args:
        url: 抖音URL

    Returns:
        ParsedLink对象，如果无法解析则返回None

    Raises:
        URLParseError: 短链无法解析（需要外部resolve）
    """
    if not url:
        return None

    url = url.strip()

    # 尝试匹配各种模式
    for link_type, pattern in DOUYIN_PATTERNS.items():
        match = pattern.match(url)
        if match:
            if link_type == 'short':
                # 短链需要特殊处理 - 返回原始形式，标记为short
                # 实际ID需要通过HTTP请求获取Location头
                return ParsedLink(
                    original=url,
                    normalized=url,  # 暂时保持原样
                    video_id=match.group('code'),  # 短链code，不是真实ID
                    link_type='short'
                )
            else:
                # 其他类型直接提取ID
                video_id = match.group('id')
                return ParsedLink(
                    original=url,
                    normalized=VIDEO_URL_TEMPLATE.format(video_id=video_id),
                    video_id=video_id,
                    link_type=link_type
                )

    # 无法识别
    return None


def extract_douyin_links(
    input_text: str,
    short_link_resolver: Optional[Callable[[str], str]] = None
) -> List[ParsedLink]:
    """
    从用户输入中提取抖音链接

    流程：
    1. 从文本中提取所有URL（支持分享文本、逗号分隔链接等）
    2. 解析每个URL，识别类型（短链、视频页、图文页等）
    3. 非短链直接标准化为视频页格式
    4. 短链可选择性resolve（如有resolver传入）

    注意：短链（v.douyin.com）默认不会自动resolve，需要传入resolver函数

    Args:
        input_text: 用户输入，可能是：
                   - 分享文本（包含链接）
                   - 单个URL
                   - 逗号分隔的URL列表
        short_link_resolver: 可选的短链解析函数，接收短链URL，返回真实URL

    Returns:
        解析后的链接列表（1-N个）

    Example:
        >>> text = "6.61 w@f.bn https://v.douyin.com/abc/ 复制此链接..."
        >>> links = extract_douyin_links(text)
        >>> # 短链返回 link_type='short'，normalized与原链接相同
        >>> # 如需resolve，传入resolver函数：
        >>> def resolve(url):
        ...     import requests
        ...     return requests.head(url, allow_redirects=True).url
        >>> links = extract_douyin_links(text, resolve)
    """
    if not input_text or not input_text.strip():
        return []

    # 步骤1：提取URL（处理逗号分隔和分享文本）
    # 先按逗号分割，再分别提取
    all_urls = []
    for part in input_text.split(','):
        urls = extract_urls_from_text(part)
        all_urls.extend(urls)

    if not all_urls:
        return []

    # 步骤2：解析每个URL
    results = []
    for url in all_urls:
        parsed = parse_douyin_url(url)
        if parsed:
            # 如果是短链且有resolver，尝试resolve
            if parsed.link_type == 'short' and short_link_resolver:
                try:
                    real_url = short_link_resolver(url)
                    # 重新解析真实URL
                    real_parsed = parse_douyin_url(real_url)
                    if real_parsed and real_parsed.link_type != 'short':
                        results.append(real_parsed)
                    else:
                        # resolve后还是短链或无法解析，保留原始
                        results.append(parsed)
                except Exception:
                    # resolve失败，保留原始短链信息
                    results.append(parsed)
            else:
                results.append(parsed)

    return results


def normalize_douyin_links(
    input_text: str,
    short_link_resolver: Optional[Callable[[str], str]] = None
) -> List[str]:
    """
    简化版：预处理并返回标准化链接列表

    Args:
        input_text: 用户输入（分享文本或链接列表）
        short_link_resolver: 可选的短链解析函数

    Returns:
        标准化后的视频页链接列表

    Example:
        >>> text = "https://v.douyin.com/abc/, https://www.douyin.com/note/123/"
        >>> normalize_douyin_links(text)
        ['https://www.douyin.com/video/abc', 'https://www.douyin.com/video/123']
    """
    parsed_list = extract_douyin_links(input_text, short_link_resolver)
    return [link.normalized for link in parsed_list]


def format_link_for_display(parsed: ParsedLink) -> str:
    """
    格式化解析结果用于UI展示

    Example:
        >>> parsed = ParsedLink(..., video_id="123456", link_type="video")
        >>> format_link_for_display(parsed)
        '视频ID: 123456 (视频页)'
    """
    type_names = {
        'short': '短链',
        'video': '视频页',
        'note': '图文页',
        'modal': '精选页',
        'mobile': '移动端',
    }
    type_name = type_names.get(parsed.link_type, '未知')
    return f"视频ID: {parsed.video_id} ({type_name})"
