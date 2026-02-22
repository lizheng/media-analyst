"""
Core - Functional Core

纯函数，无副作用，包含：
- 数据模型（Pydantic）
- 业务逻辑（参数构建等）
- 配置常量
"""

from media_analyst.core.models import (
    CrawlerRequest,
    SearchRequest,
    DetailRequest,
    CreatorRequest,
    CrawlerExecution,
    ExecutionStatus,
    Platform,
    LoginType,
    CrawlerType,
    SaveOption,
)
from media_analyst.core.config import PLATFORMS, LOGIN_TYPES, CRAWLER_TYPES, SAVE_OPTIONS
from media_analyst.core.params import build_args
from media_analyst.core.url_parser import (
    ParsedLink,
    URLParseError,
    extract_urls_from_text,
    parse_douyin_url,
    extract_douyin_links,
    normalize_douyin_links,
    format_link_for_display,
)

__all__ = [
    "CrawlerRequest",
    "SearchRequest",
    "DetailRequest",
    "CreatorRequest",
    "CrawlerExecution",
    "ExecutionStatus",
    "Platform",
    "LoginType",
    "CrawlerType",
    "SaveOption",
    "PLATFORMS",
    "LOGIN_TYPES",
    "CRAWLER_TYPES",
    "SAVE_OPTIONS",
    "build_args",
    "ParsedLink",
    "URLParseError",
    "extract_urls_from_text",
    "parse_douyin_url",
    "extract_douyin_links",
    "normalize_douyin_links",
    "format_link_for_display",
]
