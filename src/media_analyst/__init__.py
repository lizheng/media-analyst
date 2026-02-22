"""
Media Analyst - 基于 MediaCrawler 的媒体分析工具

Functional Core, Imperative Shell 架构：
- core: 纯函数，无副作用，包含业务逻辑和数据模型
- shell: 副作用（IO、进程管理）
- ui: Streamlit 界面
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
from media_analyst.shell.runner import CrawlerRunner

__version__ = "0.2.0"

__all__ = [
    # Models
    "CrawlerRequest",
    "SearchRequest",
    "DetailRequest",
    "CreatorRequest",
    "CrawlerExecution",
    "ExecutionStatus",
    # Enums
    "Platform",
    "LoginType",
    "CrawlerType",
    "SaveOption",
    # Config
    "PLATFORMS",
    "LOGIN_TYPES",
    "CRAWLER_TYPES",
    "SAVE_OPTIONS",
    # Shell
    "CrawlerRunner",
]
