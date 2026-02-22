"""
pytest配置和共享fixtures
"""

import pytest
from pathlib import Path


@pytest.fixture
def media_crawler_path() -> Path:
    """返回MediaCrawler项目路径"""
    return Path("../MediaCrawler")


@pytest.fixture
def douyin_detail_command(media_crawler_path: Path) -> list:
    """
    抖音详情模式的测试命令配置

    使用指定的视频URL进行测试：
    https://www.douyin.com/jingxuan?modal_id=7605333789232876826
    """
    return [
        "uv", "run", "main.py",
        "--platform", "dy",
        "--lt", "qrcode",
        "--type", "detail",
        "--specified_id", "https://www.douyin.com/jingxuan?modal_id=7605333789232876826",
        "--get_comment", "yes",
        "--max_comments_count_singlenotes", "10",
        "--headless", "no",  # 非无头模式，让用户能看到二维码
    ]


def pytest_configure(config):
    """pytest配置钩子"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers", "real_crawler: 标记需要真实执行MediaCrawler的测试"
    )
    config.addinivalue_line(
        "markers", "human_interaction: 标记需要人类介入（如扫码）的测试"
    )