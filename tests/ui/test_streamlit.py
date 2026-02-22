"""
Streamlit UI 测试

使用 streamlit.testing.v1.AppTest 测试：
1. 页面加载和组件渲染
2. 用户交互
3. build_request 函数输出正确的 Pydantic 模型

使用函数形式编写测试
"""

import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

# 确保可以导入 src 模块
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from media_analyst.core.models import (
    CrawlerType,
    DetailRequest,
    CreatorRequest,
    Platform,
    SearchRequest,
)

# 注意：AppTest 从文件加载，需要指向新的 app 路径
APP_PATH = str(Path(__file__).parent.parent.parent / "src" / "media_analyst" / "ui" / "app.py")


# ============================================================================
# App Load Tests
# ============================================================================

def test_app_initial_load():
    """测试应用初始加载"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 验证页面标题
    assert at.title[0].value == "🕷️ MediaCrawler 控制台"
    assert at.sidebar is not None


# ============================================================================
# Platform Selection Tests
# ============================================================================

def test_default_platform():
    """测试默认选中平台（受持久化偏好影响，默认是dy抖音）"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    platform_select = at.sidebar.selectbox[0]
    # 持久化模块默认选择 dy（抖音）
    assert platform_select.value == "dy"


def test_switch_platform():
    """测试切换平台"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    platform_select = at.sidebar.selectbox[0]
    platform_select.select("dy").run()

    assert platform_select.value == "dy"


# ============================================================================
# Crawler Type Switching Tests
# ============================================================================

def test_search_mode_shows_keywords_input():
    """搜索模式显示关键词输入"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 默认是 search 模式
    subheaders = [s.value for s in at.subheader]
    assert "🔍 搜索模式配置" in subheaders


def test_detail_mode_shows_url_input():
    """详情模式显示 URL 输入"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 切换到详情模式
    crawler_select = at.sidebar.selectbox[2]
    crawler_select.select("detail").run()

    subheaders = [s.value for s in at.subheader]
    assert "📄 详情模式配置" in subheaders


def test_creator_mode_shows_creator_input():
    """创作者模式显示创作者输入"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 切换到创作者模式
    crawler_select = at.sidebar.selectbox[2]
    crawler_select.select("creator").run()

    subheaders = [s.value for s in at.subheader]
    assert "👤 创作者模式配置" in subheaders


# ============================================================================
# Build Request Function Tests
# ============================================================================

def test_build_search_request():
    """测试构建搜索请求模型"""
    from media_analyst.ui.app import build_request

    common_config = {
        "platform": "dy",
        "login_type": "qrcode",
        "crawler_type": "search",
        "save_option": "json",
        "save_path": None,
        "max_comments": 100,
        "get_comment": True,
        "get_sub_comment": False,
        "headless": True,
    }
    mode_config = {
        "keywords": "美食,旅游",
        "start_page": 2,
    }

    request = build_request(common_config, mode_config)

    # 验证类型
    assert isinstance(request, SearchRequest)
    assert request.crawler_type == CrawlerType.SEARCH

    # 验证字段
    assert request.platform == Platform.DY
    assert request.keywords == "美食,旅游"
    assert request.start_page == 2
    assert request.get_comment is True


def test_build_detail_request():
    """测试构建详情请求模型"""
    from media_analyst.ui.app import build_request

    common_config = {
        "platform": "xhs",
        "login_type": "cookie",
        "crawler_type": "detail",
        "save_option": "csv",
        "save_path": "/custom/path",
        "max_comments": 50,
        "get_comment": False,
        "get_sub_comment": False,
        "headless": False,
    }
    mode_config = {
        "specified_ids": "https://xiaohongshu.com/note/123",
        "start_page": 1,
    }

    request = build_request(common_config, mode_config)

    assert isinstance(request, DetailRequest)
    assert request.platform == Platform.XHS
    assert request.specified_ids == "https://xiaohongshu.com/note/123"
    assert request.save_path == "/custom/path"
    assert request.headless is False


def test_build_creator_request():
    """测试构建创作者请求模型"""
    from media_analyst.ui.app import build_request

    common_config = {
        "platform": "ks",
        "login_type": "phone",
        "crawler_type": "creator",
        "save_option": "excel",
        "save_path": None,
        "max_comments": 200,
        "get_comment": True,
        "get_sub_comment": True,
        "headless": True,
    }
    mode_config = {
        "creator_ids": "user1,user2",
        "start_page": 3,
    }

    request = build_request(common_config, mode_config)

    assert isinstance(request, CreatorRequest)
    assert request.platform.value == "ks"
    assert request.creator_ids == "user1,user2"
    assert request.start_page == 3


def test_build_request_rejects_empty_search_keywords():
    """拒绝空的搜索关键词"""
    from media_analyst.ui.app import build_request

    common_config = {
        "platform": "dy",
        "login_type": "qrcode",
        "crawler_type": "search",
        "save_option": "json",
        "save_path": None,
        "max_comments": 100,
        "get_comment": False,
        "get_sub_comment": False,
        "headless": True,
    }
    mode_config = {
        "keywords": "",
        "start_page": 1,
    }

    with pytest.raises(ValueError, match="搜索模式必须填写关键词"):
        build_request(common_config, mode_config)


def test_build_request_rejects_empty_detail_ids():
    """拒绝空的详情 ID"""
    from media_analyst.ui.app import build_request

    common_config = {
        "platform": "dy",
        "login_type": "qrcode",
        "crawler_type": "detail",
        "save_option": "json",
        "save_path": None,
        "max_comments": 100,
        "get_comment": False,
        "get_sub_comment": False,
        "headless": True,
    }
    mode_config = {
        "specified_ids": "   ",  # 纯空白
        "start_page": 1,
    }

    with pytest.raises(ValueError, match="详情模式必须填写"):
        build_request(common_config, mode_config)


def test_build_request_rejects_empty_creator_ids():
    """拒绝空的创作者 ID"""
    from media_analyst.ui.app import build_request

    common_config = {
        "platform": "dy",
        "login_type": "qrcode",
        "crawler_type": "creator",
        "save_option": "json",
        "save_path": None,
        "max_comments": 100,
        "get_comment": False,
        "get_sub_comment": False,
        "headless": True,
    }
    mode_config = {
        "creator_ids": "",
        "start_page": 1,
    }

    with pytest.raises(ValueError, match="创作者模式必须填写"):
        build_request(common_config, mode_config)


# ============================================================================
# Command Preview Tests
# ============================================================================

def test_command_preview_expander_exists():
    """验证命令预览区域存在"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    expanders = [e.label for e in at.expander]
    assert "📜 命令预览" in expanders


# ============================================================================
# Sidebar Configuration Tests
# ============================================================================

def test_all_selectboxes_present():
    """验证所有选择器存在"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 侧边栏应有：平台、登录方式、爬虫类型、保存格式
    assert len(at.sidebar.selectbox) >= 4


def test_checkboxes_present():
    """验证复选框存在"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 至少应有：获取评论、获取子评论、无头模式
    assert len(at.sidebar.checkbox) >= 3


# ============================================================================
# Model In UI Context Tests
# ============================================================================

def test_full_search_workflow_model():
    """完整搜索流程的模型验证"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 1. 选择平台
    platform_select = at.sidebar.selectbox[0]
    platform_select.select("dy").run()

    # 2. 选择登录方式
    login_select = at.sidebar.selectbox[1]
    login_select.select("qrcode").run()

    # 3. 确认搜索模式
    # 默认就是 search，无需切换

    # 4. 填写关键词
    # 注意：在真实测试中，这里需要找到 textarea 并设置值
    # 但由于 streamlit testing 的限制，我们直接测试 build_request

    # 5. 构建请求模型（模拟表单提交）
    from media_analyst.ui.app import build_request

    common_config = {
        "platform": platform_select.value,
        "login_type": login_select.value,
        "crawler_type": "search",
        "save_option": "json",
        "save_path": None,
        "max_comments": 100,
        "get_comment": True,
        "get_sub_comment": False,
        "headless": True,
    }
    mode_config = {
        "keywords": "美食探店",
        "start_page": 1,
    }

    request = build_request(common_config, mode_config)

    # 验证模型
    assert isinstance(request, SearchRequest)
    assert request.platform == Platform.DY
    assert request.keywords == "美食探店"

    # 验证可转换为 CLI 参数
    cli_args = request.to_cli_args()
    assert "--platform" in cli_args
    assert "dy" in cli_args
    assert "--keywords" in cli_args
    assert "美食探店" in cli_args
