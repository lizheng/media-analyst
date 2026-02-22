"""
pytest 配置和共享 fixtures
"""

import sys
from pathlib import Path

import pytest

# 确保可以导入 src 模块
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))


# ==================== 路径 Fixtures ====================


@pytest.fixture
def project_root() -> Path:
    """项目根目录"""
    return Path(__file__).parent.parent


@pytest.fixture
def media_crawler_path() -> Path:
    """MediaCrawler 项目路径"""
    return Path('../MediaCrawler')


@pytest.fixture
def src_path(project_root: Path) -> Path:
    """src 目录路径"""
    return project_root / 'src'


# ==================== 数据 Fixtures ====================


@pytest.fixture
def sample_search_config() -> dict:
    """示例搜索配置"""
    return {
        'platform': 'dy',
        'login_type': 'qrcode',
        'crawler_type': 'search',
        'save_option': 'json',
        'save_path': None,
        'max_comments': 100,
        'get_comment': True,
        'get_sub_comment': False,
        'headless': True,
    }


@pytest.fixture
def sample_detail_config() -> dict:
    """示例详情配置"""
    return {
        'platform': 'dy',
        'login_type': 'qrcode',
        'crawler_type': 'detail',
        'save_option': 'json',
        'save_path': None,
        'max_comments': 10,
        'get_comment': True,
        'get_sub_comment': False,
        'headless': False,
    }


# ==================== Real Crawler Fixtures ====================


@pytest.fixture
def ensure_media_crawler(media_crawler_path: Path) -> Path:
    """
    确保 MediaCrawler 存在

    如果不存在则跳过测试
    """
    if not media_crawler_path.exists():
        pytest.skip(f'MediaCrawler 路径不存在: {media_crawler_path.absolute()}')

    main_py = media_crawler_path / 'main.py'
    if not main_py.exists():
        pytest.skip(f'找不到 main.py: {main_py}')

    return media_crawler_path


# ==================== pytest 配置 ====================


def pytest_configure(config):
    """pytest 配置钩子"""
    # 添加自定义标记
    config.addinivalue_line('markers', 'real_crawler: 标记需要真实执行 MediaCrawler 的测试')
    config.addinivalue_line('markers', 'human_interaction: 标记需要人类介入（如扫码）的测试')
    config.addinivalue_line('markers', 'slow: 标记执行时间较长的测试')


def pytest_collection_modifyitems(config, items):
    """修改测试项集合"""
    # 自动为真实爬虫测试添加 slow 标记
    for item in items:
        if 'real_crawler' in str(item.fspath):
            item.add_marker(pytest.mark.slow)
