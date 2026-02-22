"""
配置常量

所有 UI 显示文本和选项映射集中管理
"""
from typing import Dict, List

# 平台配置
PLATFORMS: Dict[str, str] = {
    "xhs": "小红书",
    "dy": "抖音",
    "ks": "快手",
    "bili": "B站",
    "wb": "微博",
    "tieba": "贴吧",
    "zhihu": "知乎",
}

# 登录方式
LOGIN_TYPES: Dict[str, str] = {
    "qrcode": "扫码登录",
    "phone": "手机号登录",
    "cookie": "Cookie 登录",
}

# 爬虫类型
CRAWLER_TYPES: Dict[str, str] = {
    "search": "搜索模式",
    "detail": "详情模式",
    "creator": "创作者模式",
}

# 保存格式
SAVE_OPTIONS: List[str] = ["json", "csv", "excel", "sqlite", "db", "mongodb", "postgres"]

# MediaCrawler 路径（相对于项目根目录）
DEFAULT_MEDIA_CRAWLER_PATH = "../MediaCrawler"
