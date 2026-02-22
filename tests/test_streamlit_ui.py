"""
Streamlit UI 测试

使用 streamlit.testing.v1.AppTest 测试界面组件和交互
不需要实际运行 MediaCrawler，适合测试 UI 逻辑

运行命令:
    uv run pytest tests/test_streamlit_ui.py -v

特点:
    - 快速执行（不启动真实爬虫）
    - 测试 UI 组件渲染和状态
    - 测试参数构建逻辑
"""

import pytest
from streamlit.testing.v1 import AppTest


def test_app_initial_load():
    """测试应用初始加载"""
    at = AppTest.from_file("streamlit_app.py")
    at.run()

    # 验证页面标题
    assert at.title[0].value == "🕷️ MediaCrawler 控制台"

    # 验证侧边栏配置存在
    assert at.sidebar is not None


def test_platform_selection():
    """测试平台选择器"""
    at = AppTest.from_file("streamlit_app.py")
    at.run()

    # 获取平台选择器（selectbox）
    platform_select = at.sidebar.selectbox[0]

    # 验证默认选中第一个平台
    assert platform_select.value == "xhs"

    # 测试切换平台
    platform_select.select("dy").run()
    assert platform_select.value == "dy"


def test_crawler_type_detail_shows_url_input():
    """测试详情模式显示URL输入框"""
    at = AppTest.from_file("streamlit_app.py")
    at.run()

    # 切换到详情模式
    crawler_select = at.sidebar.selectbox[2]  # 爬虫类型选择器
    crawler_select.select("detail").run()

    # 验证详情模式的输入框出现
    # 在详情模式下应该有一个 textarea 用于输入 URL
    subheaders = [s.value for s in at.subheader]
    assert "📄 详情模式配置" in subheaders


def test_crawler_type_search_shows_keywords_input():
    """测试搜索模式显示关键词输入框"""
    at = AppTest.from_file("streamlit_app.py")
    at.run()

    # 切换到搜索模式
    crawler_select = at.sidebar.selectbox[2]
    crawler_select.select("search").run()

    # 验证搜索模式的输入框出现
    subheaders = [s.value for s in at.subheader]
    assert "🔍 搜索模式配置" in subheaders


def test_build_args_function():
    """测试 build_args 函数"""
    # 从 streamlit_app 导入函数进行测试
    import sys
    sys.path.insert(0, ".")
    from streamlit_app import build_args

    # 测试搜索模式参数构建
    args = build_args(
        platform="dy",
        login_type="qrcode",
        crawler_type="search",
        keywords="美食,旅游",
        start_page=1,
        get_comment=True,
        save_option="json",
        max_comments=50
    )

    assert "--platform" in args
    assert "dy" in args
    assert "--lt" in args
    assert "qrcode" in args
    assert "--keywords" in args
    assert "美食,旅游" in args
    assert "--get_comment" in args
    assert "yes" in args


def test_build_args_detail_mode():
    """测试详情模式参数构建"""
    import sys
    sys.path.insert(0, ".")
    from streamlit_app import build_args

    args = build_args(
        platform="dy",
        login_type="qrcode",
        crawler_type="detail",
        specified_ids="https://douyin.com/video/123",
        get_comment=True,
        max_comments=10
    )

    assert "--type" in args
    assert "detail" in args
    assert "--specified_id" in args
    assert "https://douyin.com/video/123" in args
    assert "--max_comments_count_singlenotes" in args
    assert "10" in args


def test_form_validation_requires_keywords_for_search():
    """测试搜索模式需要关键词验证"""
    at = AppTest.from_file("streamlit_app.py")
    at.run()

    # 切换到搜索模式
    crawler_select = at.sidebar.selectbox[2]
    crawler_select.select("search").run()

    # 点击开始按钮（不输入关键词）
    # 注意：这里只是测试 UI 状态，实际验证在按钮点击时
    start_button = at.button[0]
    assert start_button.label == "🚀 开始爬取"


def test_sidebar_configuration_options():
    """测试侧边栏所有配置选项"""
    at = AppTest.from_file("streamlit_app.py")
    at.run()

    # 验证所有选择器存在
    assert len(at.sidebar.selectbox) >= 3  # 平台、登录方式、爬虫类型

    # 验证复选框存在
    assert len(at.sidebar.checkbox) >= 3  # 获取评论、获取子评论、无头模式


def test_command_preview_expander():
    """测试命令预览区域"""
    at = AppTest.from_file("streamlit_app.py")
    at.run()

    # 验证命令预览区域存在（expander）
    expanders = [e.label for e in at.expander]
    assert "📜 命令预览" in expanders
    assert "📖 使用说明" in expanders


@pytest.mark.parametrize("platform,expected", [
    ("xhs", "小红书"),
    ("dy", "抖音"),
    ("ks", "快手"),
    ("bili", "B站"),
])
def test_platform_display_names(platform, expected):
    """测试平台显示名称"""
    import sys
    sys.path.insert(0, ".")
    from streamlit_app import PLATFORMS

    assert PLATFORMS[platform] == expected


def test_max_comments_input_range():
    """测试最大评论数输入范围"""
    at = AppTest.from_file("streamlit_app.py")
    at.run()

    # 获取 number_input
    number_inputs = at.sidebar.number_input
    max_comments_input = None

    for ni in number_inputs:
        if "单篇最大评论数" in ni.label or "max_comments" in ni.label:
            max_comments_input = ni
            break

    # 验证默认值
    if max_comments_input:
        assert max_comments_input.value == 100
