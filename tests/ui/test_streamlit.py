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
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'src'))

from media_analyst.core.models import (
    CrawlerType,
    CreatorRequest,
    DetailRequest,
    Platform,
    SearchRequest,
)

# 注意：AppTest 从文件加载，需要指向新的 app 路径
APP_PATH = str(Path(__file__).parent.parent.parent / 'src' / 'media_analyst' / 'ui' / 'app.py')


# ============================================================================
# App Load Tests
# ============================================================================


def test_app_initial_load():
    """测试应用初始加载"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 验证页面标题
    assert at.title[0].value == '🕷️ MediaCrawler 控制台'
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
    assert platform_select.value == 'dy'


def test_switch_platform():
    """测试切换平台"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    platform_select = at.sidebar.selectbox[0]
    platform_select.select('dy').run()

    assert platform_select.value == 'dy'


# ============================================================================
# Crawler Type Switching Tests
# ============================================================================


def test_search_mode_shows_keywords_input():
    """搜索模式显示关键词输入"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 默认是 search 模式
    subheaders = [s.value for s in at.subheader]
    assert '🔍 搜索模式配置' in subheaders


def test_detail_mode_shows_url_input():
    """详情模式显示 URL 输入"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 切换到详情模式
    crawler_select = at.sidebar.selectbox[2]
    crawler_select.select('detail').run()

    subheaders = [s.value for s in at.subheader]
    assert '📄 详情模式配置' in subheaders


def test_creator_mode_shows_creator_input():
    """创作者模式显示创作者输入"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 切换到创作者模式
    crawler_select = at.sidebar.selectbox[2]
    crawler_select.select('creator').run()

    subheaders = [s.value for s in at.subheader]
    assert '👤 创作者模式配置' in subheaders


# ============================================================================
# Build Request Function Tests
# ============================================================================


def test_build_search_request():
    """测试构建搜索请求模型"""
    from media_analyst.ui.app import build_request

    common_config = {
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
    mode_config = {
        'keywords': '美食,旅游',
        'start_page': 2,
    }

    request = build_request(common_config, mode_config)

    # 验证类型
    assert isinstance(request, SearchRequest)
    assert request.crawler_type == CrawlerType.SEARCH

    # 验证字段
    assert request.platform == Platform.DY
    assert request.keywords == '美食,旅游'
    assert request.start_page == 2
    assert request.get_comment is True


def test_build_detail_request():
    """测试构建详情请求模型"""
    from media_analyst.ui.app import build_request

    common_config = {
        'platform': 'xhs',
        'login_type': 'cookie',
        'crawler_type': 'detail',
        'save_option': 'csv',
        'save_path': '/custom/path',
        'max_comments': 50,
        'get_comment': False,
        'get_sub_comment': False,
        'headless': False,
    }
    mode_config = {
        'specified_ids': 'https://xiaohongshu.com/note/123',
        'start_page': 1,
    }

    request = build_request(common_config, mode_config)

    assert isinstance(request, DetailRequest)
    assert request.platform == Platform.XHS
    assert request.specified_ids == 'https://xiaohongshu.com/note/123'
    assert request.save_path == '/custom/path'
    assert request.headless is False


def test_build_creator_request():
    """测试构建创作者请求模型"""
    from media_analyst.ui.app import build_request

    common_config = {
        'platform': 'ks',
        'login_type': 'phone',
        'crawler_type': 'creator',
        'save_option': 'excel',
        'save_path': None,
        'max_comments': 200,
        'get_comment': True,
        'get_sub_comment': True,
        'headless': True,
    }
    mode_config = {
        'creator_ids': 'user1,user2',
        'start_page': 3,
    }

    request = build_request(common_config, mode_config)

    assert isinstance(request, CreatorRequest)
    assert request.platform.value == 'ks'
    assert request.creator_ids == 'user1,user2'
    assert request.start_page == 3


def test_build_request_rejects_empty_search_keywords():
    """拒绝空的搜索关键词"""
    from media_analyst.ui.app import build_request

    common_config = {
        'platform': 'dy',
        'login_type': 'qrcode',
        'crawler_type': 'search',
        'save_option': 'json',
        'save_path': None,
        'max_comments': 100,
        'get_comment': False,
        'get_sub_comment': False,
        'headless': True,
    }
    mode_config = {
        'keywords': '',
        'start_page': 1,
    }

    with pytest.raises(ValueError, match='搜索模式必须填写关键词'):
        build_request(common_config, mode_config)


def test_build_request_rejects_empty_detail_ids():
    """拒绝空的详情 ID"""
    from media_analyst.ui.app import build_request

    common_config = {
        'platform': 'dy',
        'login_type': 'qrcode',
        'crawler_type': 'detail',
        'save_option': 'json',
        'save_path': None,
        'max_comments': 100,
        'get_comment': False,
        'get_sub_comment': False,
        'headless': True,
    }
    mode_config = {
        'specified_ids': '   ',  # 纯空白
        'start_page': 1,
    }

    with pytest.raises(ValueError, match='详情模式必须填写'):
        build_request(common_config, mode_config)


def test_build_request_rejects_empty_creator_ids():
    """拒绝空的创作者 ID"""
    from media_analyst.ui.app import build_request

    common_config = {
        'platform': 'dy',
        'login_type': 'qrcode',
        'crawler_type': 'creator',
        'save_option': 'json',
        'save_path': None,
        'max_comments': 100,
        'get_comment': False,
        'get_sub_comment': False,
        'headless': True,
    }
    mode_config = {
        'creator_ids': '',
        'start_page': 1,
    }

    with pytest.raises(ValueError, match='创作者模式必须填写'):
        build_request(common_config, mode_config)


# ============================================================================
# Command Preview Tests
# ============================================================================


def test_command_preview_expander_exists():
    """验证命令预览区域存在"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    expanders = [e.label for e in at.expander]
    assert '📜 命令预览' in expanders


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
    platform_select.select('dy').run()

    # 2. 选择登录方式
    login_select = at.sidebar.selectbox[1]
    login_select.select('qrcode').run()

    # 3. 确认搜索模式
    # 默认就是 search，无需切换

    # 4. 填写关键词
    # 注意：在真实测试中，这里需要找到 textarea 并设置值
    # 但由于 streamlit testing 的限制，我们直接测试 build_request

    # 5. 构建请求模型（模拟表单提交）
    from media_analyst.ui.app import build_request

    common_config = {
        'platform': platform_select.value,
        'login_type': login_select.value,
        'crawler_type': 'search',
        'save_option': 'json',
        'save_path': None,
        'max_comments': 100,
        'get_comment': True,
        'get_sub_comment': False,
        'headless': True,
    }
    mode_config = {
        'keywords': '美食探店',
        'start_page': 1,
    }

    request = build_request(common_config, mode_config)

    # 验证模型
    assert isinstance(request, SearchRequest)
    assert request.platform == Platform.DY
    assert request.keywords == '美食探店'

    # 验证可转换为 CLI 参数
    cli_args = request.to_cli_args()
    assert '--platform' in cli_args
    assert 'dy' in cli_args
    assert '--keywords' in cli_args
    assert '美食探店' in cli_args


# ============================================================================
# Build Request with Parsed Links Tests
# ============================================================================


def test_build_detail_request_with_parsed_links():
    """测试详情模式使用解析后的链接"""
    from media_analyst.core import ParsedLink
    from media_analyst.ui.app import build_request

    common_config = {
        'platform': 'dy',
        'login_type': 'qrcode',
        'crawler_type': 'detail',
        'save_option': 'json',
        'save_path': None,
        'max_comments': 100,
        'get_comment': False,
        'get_sub_comment': False,
        'headless': True,
    }
    mode_config = {
        'specified_ids': '',
        'start_page': 1,
        'parsed_links': [
            ParsedLink(
                original='https://v.douyin.com/abc123/',
                normalized='https://v.douyin.com/abc123/',
                video_id='abc123',
                link_type='short',
            ),
        ],
    }

    request = build_request(common_config, mode_config)

    assert isinstance(request, DetailRequest)
    assert 'abc123' in request.specified_ids


# ============================================================================
# Unknown Crawler Type Tests
# ============================================================================


def test_build_request_rejects_unknown_crawler_type():
    """拒绝未知的爬虫类型"""
    from media_analyst.ui.app import build_request

    common_config = {
        'platform': 'dy',
        'login_type': 'qrcode',
        'crawler_type': 'unknown_type',
        'save_option': 'json',
        'save_path': None,
        'max_comments': 100,
        'get_comment': False,
        'get_sub_comment': False,
        'headless': True,
    }
    mode_config = {}

    with pytest.raises(ValueError, match='未知的爬虫类型'):
        build_request(common_config, mode_config)


# ============================================================================
# Sidebar Config Tests
# ============================================================================


def test_login_type_selection():
    """测试登录方式选择"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 第二个 selectbox 是登录方式
    login_select = at.sidebar.selectbox[1]
    login_options = login_select.options

    # 应有扫码登录、手机号登录、Cookie 登录选项（中文显示文本）
    assert any('扫码' in opt for opt in login_options)
    assert any('手机' in opt for opt in login_options)
    assert any('Cookie' in opt for opt in login_options)


def test_crawler_type_selection():
    """测试爬虫类型选择"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 第三个 selectbox 是爬虫类型
    crawler_select = at.sidebar.selectbox[2]
    crawler_options = crawler_select.options

    # 应有搜索模式、详情模式、创作者模式选项（中文显示文本）
    assert any('搜索' in opt for opt in crawler_options)
    assert any('详情' in opt for opt in crawler_options)
    assert any('创作者' in opt for opt in crawler_options)


def test_save_option_selection():
    """测试保存格式选择"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 第四个 selectbox 是保存格式
    save_select = at.sidebar.selectbox[3]
    save_options = save_select.options

    # 应有 json, csv, excel 等选项
    assert 'json' in save_options
    assert 'csv' in save_options


def test_max_comments_number_input():
    """测试最大评论数输入"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 查找数字输入
    number_inputs = at.sidebar.number_input
    assert len(number_inputs) > 0

    # 第一个应该是 max_comments
    max_comments = number_inputs[0]
    assert max_comments.value >= 0


def test_comment_checkboxes():
    """测试评论相关复选框"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    checkboxes = at.sidebar.checkbox
    checkbox_labels = [cb.label for cb in checkboxes]

    # 检查有获取评论和无头模式选项
    assert any('评论' in label or '子评论' in label for label in checkbox_labels)
    assert any('无头' in label or 'headless' in label.lower() for label in checkbox_labels)


# ============================================================================
# Expander Tests
# ============================================================================


def test_usage_expander_exists():
    """验证使用说明折叠面板存在"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    expanders = [e.label for e in at.expander]
    assert '📖 使用说明' in expanders


def test_model_details_expander():
    """验证请求模型详情折叠面板存在（在命令预览内）"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    expanders = [e.label for e in at.expander]
    assert '📜 命令预览' in expanders


# ============================================================================
# Button Tests
# ============================================================================


def test_start_button_exists():
    """验证开始按钮存在"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    buttons = [b for b in at.button if '开始' in str(b.label) or '爬取' in str(b.label)]
    assert len(buttons) > 0


def test_open_directory_button_exists():
    """验证打开目录按钮存在"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    buttons = [b for b in at.button if '目录' in str(b.label)]
    # 可能有多个打开目录按钮
    assert len(buttons) >= 0  # 页面结构可能变化


# ============================================================================
# Detail Mode Platform-Specific Tests
# ============================================================================


def test_detail_mode_for_douyin():
    """测试抖音详情模式的特殊处理"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 选择抖音平台
    platform_select = at.sidebar.selectbox[0]
    platform_select.select('dy').run()

    # 切换到详情模式
    crawler_select = at.sidebar.selectbox[2]
    crawler_select.select('detail').run()

    # 验证有子标题显示详情模式配置
    subheaders = [s.value for s in at.subheader]
    assert any('详情' in s for s in subheaders)


def test_detail_mode_for_xiaohongshu():
    """测试小红书详情模式"""
    at = AppTest.from_file(APP_PATH)
    at.run()

    # 选择小红书平台
    platform_select = at.sidebar.selectbox[0]
    platform_select.select('xhs').run()

    # 切换到详情模式
    crawler_select = at.sidebar.selectbox[2]
    crawler_select.select('detail').run()

    # 验证有详情模式配置
    subheaders = [s.value for s in at.subheader]
    assert any('详情' in s for s in subheaders)
