"""
MediaCrawler Streamlit 界面

Functional Core, Imperative Shell 架构：
1. Core: 构建 CrawlerRequest 模型（纯函数）
2. Shell: CrawlerRunner 执行（副作用）
"""

import platform as _platform_module

import streamlit as st
from pathlib import Path

# 使用绝对导入（假设通过 pip install -e . 安装）
from media_analyst.core import (
    PLATFORMS,
    LOGIN_TYPES,
    CRAWLER_TYPES,
    SAVE_OPTIONS,
    Platform,
    LoginType,
    CrawlerType,
    SaveOption,
    SearchRequest,
    DetailRequest,
    CreatorRequest,
    CrawlerExecution,
    extract_douyin_links,
    format_link_for_display,
)
from media_analyst.core.params import preview_command
from media_analyst.shell import CrawlerRunner, CrawlerRunnerError
from media_analyst.ui.persistence import (
    load_preferences,
    save_from_form_values,
)

# 页面配置
st.set_page_config(
    page_title="MediaCrawler 控制台",
    page_icon="🕷️",
    layout="wide",
)

# MediaCrawler 路径
MEDIA_CRAWLER_PATH = Path("../MediaCrawler")


def render_sidebar() -> dict:
    """
    渲染侧边栏，返回通用配置

    Returns:
        包含通用配置的字典
    """
    # 加载用户偏好（用于设置默认值）
    prefs = load_preferences()

    # 计算各选项的索引
    platform_options = list(PLATFORMS.keys())
    platform_index = platform_options.index(prefs.platform) if prefs.platform in platform_options else 0

    login_options = list(LOGIN_TYPES.keys())
    login_index = login_options.index(prefs.login_type) if prefs.login_type in login_options else 0

    crawler_options = list(CRAWLER_TYPES.keys())
    crawler_index = crawler_options.index(prefs.crawler_type) if prefs.crawler_type in crawler_options else 0

    save_index = SAVE_OPTIONS.index(prefs.save_option) if prefs.save_option in SAVE_OPTIONS else 0

    with st.sidebar:
        st.header("⚙️ 基础配置")

        platform = st.selectbox(
            "选择平台",
            options=platform_options,
            index=platform_index,
            format_func=lambda x: f"{x} - {PLATFORMS[x]}",
            help="选择要爬取的平台",
        )

        login_type = st.selectbox(
            "登录方式",
            options=login_options,
            index=login_index,
            format_func=lambda x: LOGIN_TYPES[x],
            help="选择登录方式",
        )

        crawler_type = st.selectbox(
            "爬虫类型",
            options=crawler_options,
            index=crawler_index,
            format_func=lambda x: CRAWLER_TYPES[x],
            help="选择爬取模式",
        )

        st.divider()
        st.header("🔧 通用设置")

        save_option = st.selectbox(
            "保存格式",
            options=SAVE_OPTIONS,
            index=save_index,
            help="数据保存格式",
        )

        save_path = st.text_input(
            "保存路径 (可选)",
            value=prefs.save_path,
            placeholder="默认: MediaCrawler/data/",
            help="自定义数据保存路径，留空使用默认路径",
        )

        max_comments = st.number_input(
            "单篇最大评论数",
            min_value=0,
            max_value=10000,
            value=prefs.max_comments,
            help="每篇笔记/视频获取的最大评论数，0表示不限制",
        )

        col1, col2 = st.columns(2)
        with col1:
            get_comment = st.checkbox("获取评论", value=prefs.get_comment)
        with col2:
            get_sub_comment = st.checkbox("获取子评论", value=prefs.get_sub_comment)

        headless = st.checkbox("无头模式", value=prefs.headless, help="后台运行浏览器（不显示窗口）")

    return {
        "platform": platform,
        "login_type": login_type,
        "crawler_type": crawler_type,
        "save_option": save_option,
        "save_path": save_path or None,
        "max_comments": max_comments,
        "get_comment": get_comment,
        "get_sub_comment": get_sub_comment,
        "headless": headless,
    }


def render_search_form() -> dict:
    """渲染搜索模式表单"""
    st.subheader("🔍 搜索模式配置")
    keywords = st.text_area(
        "搜索关键词",
        placeholder="输入关键词，多个用逗号分隔，如：美食,旅游,穿搭",
        help="输入要搜索的关键词",
    )
    start_page = st.number_input("起始页码", min_value=1, value=1, help="从第几页开始爬取")

    return {
        "keywords": keywords,
        "start_page": start_page,
    }


def render_detail_form(platform: str) -> dict:
    """渲染详情模式表单"""
    st.subheader("📄 详情模式配置")

    # 根据平台显示不同的提示
    if platform == "dy":
        help_text = (
            "支持以下格式（自动识别）：\n"
            "• 抖音分享文本（自动提取链接）\n"
            "• 短链：https://v.douyin.com/xxxxx/\n"
            "• 视频页：https://www.douyin.com/video/xxxxx\n"
            "• 图文页：https://www.douyin.com/note/xxxxx\n"
            "• 多个链接用逗号分隔"
        )
        placeholder = "粘贴抖音分享文本或链接，多个用逗号分隔"
    else:
        help_text = "输入要爬取的笔记或视频链接/ID"
        placeholder = "输入 URL 或 ID，多个用逗号分隔"

    specified_ids = st.text_area(
        "笔记/视频 URL 或 ID",
        placeholder=placeholder,
        help=help_text,
    )

    # 抖音平台：实时预览解析结果
    parsed_links = []
    if platform == "dy" and specified_ids.strip():
        parsed_links = extract_douyin_links(specified_ids)
        if parsed_links:
            with st.expander(f"🔗 已识别 {len(parsed_links)} 个链接", expanded=True):
                for link in parsed_links:
                    st.text(format_link_for_display(link))
                    st.caption(f"标准化: {link.normalized}")
        elif specified_ids.strip():
            st.warning("⚠️ 未识别到有效的抖音链接")

    start_page = st.number_input("起始页码", min_value=1, value=1)

    return {
        "specified_ids": specified_ids,
        "start_page": start_page,
        "parsed_links": parsed_links,
    }


def render_creator_form() -> dict:
    """渲染创作者模式表单"""
    st.subheader("👤 创作者模式配置")
    creator_ids = st.text_area(
        "创作者主页 URL 或 ID",
        placeholder="输入创作者主页 URL 或 ID，多个用逗号分隔",
        help="输入创作者主页链接或ID",
    )
    start_page = st.number_input("起始页码", min_value=1, value=1)

    return {
        "creator_ids": creator_ids,
        "start_page": start_page,
    }


def build_request(common_config: dict, mode_config: dict) -> SearchRequest | DetailRequest | CreatorRequest:
    """
    构建爬虫请求模型（Core - 纯函数）

    Args:
        common_config: 通用配置
        mode_config: 模式特定配置

    Returns:
        具体的请求模型

    Raises:
        ValueError: 如果配置无效
    """
    # 转换枚举
    platform = Platform(common_config["platform"])
    login_type = LoginType(common_config["login_type"])
    save_option = SaveOption(common_config["save_option"])

    crawler_type = common_config["crawler_type"]

    # 通用参数字典
    common = {
        "platform": platform,
        "login_type": login_type,
        "get_comment": common_config["get_comment"],
        "get_sub_comment": common_config["get_sub_comment"],
        "headless": common_config["headless"],
        "save_option": save_option,
        "max_comments": common_config["max_comments"],
        "save_path": common_config["save_path"],
    }

    # 根据类型构建具体请求（不合法状态无法表示）
    if crawler_type == "search":
        keywords = mode_config.get("keywords", "").strip()
        if not keywords:
            raise ValueError("搜索模式必须填写关键词")
        return SearchRequest(
            **common,
            keywords=keywords,
            start_page=mode_config.get("start_page", 1),
        )

    elif crawler_type == "detail":
        # 如果存在解析后的链接（抖音平台），使用标准化后的链接
        parsed_links = mode_config.get("parsed_links", [])
        if parsed_links:
            # 使用标准化后的链接，逗号分隔
            normalized_urls = [link.normalized for link in parsed_links]
            specified_ids = ",".join(normalized_urls)
        else:
            specified_ids = mode_config.get("specified_ids", "").strip()

        if not specified_ids:
            raise ValueError("详情模式必须填写笔记/视频 URL 或 ID")
        return DetailRequest(
            **common,
            specified_ids=specified_ids,
            start_page=mode_config.get("start_page", 1),
        )

    elif crawler_type == "creator":
        creator_ids = mode_config.get("creator_ids", "").strip()
        if not creator_ids:
            raise ValueError("创作者模式必须填写创作者 ID")
        return CreatorRequest(
            **common,
            creator_ids=creator_ids,
            start_page=mode_config.get("start_page", 1),
        )

    else:
        raise ValueError(f"未知的爬虫类型: {crawler_type}")


def open_results_directory(save_path: str | None) -> None:
    """打开结果目录

    注意：路径是相对于 MediaCrawler 目录的，因为爬虫在那里运行
    """
    import subprocess

    # 确定要打开的目录路径（相对于 MEDIA_CRAWLER_PATH）
    if save_path:
        # 用户指定的路径是相对于 MediaCrawler 的
        target_path = MEDIA_CRAWLER_PATH / save_path
    else:
        target_path = MEDIA_CRAWLER_PATH / "data"

    # 解析为绝对路径并规范化
    target_path = target_path.resolve()

    if not target_path.exists():
        st.warning(f"目录不存在: {target_path}")
        return

    # 根据操作系统选择打开方式
    system = _platform_module.system()
    try:
        if system == "Darwin":  # macOS
            subprocess.Popen(["open", str(target_path)])
        elif system == "Windows":
            subprocess.Popen(["explorer", str(target_path)])
        else:  # Linux
            subprocess.Popen(["xdg-open", str(target_path)])
        st.toast(f"已打开目录: {target_path}")
    except Exception as e:
        st.error(f"无法打开目录: {e}")


def run_crawler_ui(request: SearchRequest | DetailRequest | CreatorRequest) -> CrawlerExecution | None:
    """
    运行爬虫并显示结果（Shell - 副作用）

    Returns:
        CrawlerExecution 对象，如果失败则返回 None
    """
    # 初始化 Runner
    try:
        runner = CrawlerRunner(MEDIA_CRAWLER_PATH)
    except CrawlerRunnerError as e:
        st.error(f"❌ {e}")
        return None

    # 创建输出区域
    st.info("🔄 正在启动爬虫...")
    output_container = st.container()
    output_placeholder = output_container.empty()

    try:
        # 启动爬虫
        execution = runner.start(request)

        # 实时显示输出（合并 stdout 和 stderr，使用普通文本样式）
        all_lines = []

        for line in runner.iter_output(execution, timeout=300):  # 5分钟超时
            if line.startswith("[stderr] "):
                all_lines.append(line[9:])
            else:
                all_lines.append(line)
            # 只显示最后100行，使用普通code样式（非红色）
            output_placeholder.code("\n".join(all_lines[-100:]), language="text")

        # 显示结果
        if execution.status.value == "completed":
            st.success(f"✅ 爬取完成！耗时 {execution.duration_seconds:.1f} 秒")
        else:
            st.error(f"❌ 爬取失败: {execution.error_message or '未知错误'}")

        return execution

    except TimeoutError:
        st.error("❌ 执行超时（5分钟）")
        return None
    except Exception as e:
        st.error(f"❌ 运行出错: {str(e)}")
        return None


# ========== 主应用 ==========

def main():
    """主应用入口"""
    # 页面标题
    st.title("🕷️ MediaCrawler 控制台")
    st.markdown("通过 Web 界面配置和运行 MediaCrawler，无需命令行操作")

    # 使用说明 - 折叠状态，放在页面顶部便于查看
    with st.expander("📖 使用说明", expanded=False):
        st.markdown("""
        ### 快速开始

        1. **选择平台**：在侧边栏选择要爬取的平台（小红书、抖音、B站等）
        2. **选择登录方式**：
           - **扫码登录**：会弹出二维码，用手机扫码
           - **手机号登录**：输入手机号和验证码
           - **Cookie 登录**：使用已保存的 Cookie（需要提前配置）
        3. **选择爬虫类型**：
           - **搜索模式**：按关键词搜索内容
           - **详情模式**：爬取指定笔记/视频的详情
           - **创作者模式**：爬取指定创作者的所有内容
        4. **配置参数**：根据爬虫类型填写相应的参数
        5. **点击开始**：点击"开始爬取"按钮运行

        ### 注意事项

        - 首次使用需要先登录获取 Cookie
        - 建议开启无头模式（后台运行）
        - 爬取频率过高可能导致账号受限，请合理设置参数
        - 数据默认保存在 MediaCrawler/data/ 目录下
        """)

    st.divider()

    # 初始化 session state
    if "is_running" not in st.session_state:
        st.session_state.is_running = False

    # 侧边栏配置
    common_config = render_sidebar()

    # 主界面 - 动态表单
    st.header("📋 爬取参数")

    crawler_type = common_config["crawler_type"]

    # 根据爬虫类型渲染不同表单
    if crawler_type == "search":
        mode_config = render_search_form()
    elif crawler_type == "detail":
        mode_config = render_detail_form(common_config["platform"])
    elif crawler_type == "creator":
        mode_config = render_creator_form()
    else:
        st.error(f"未知的爬虫类型: {crawler_type}")
        return

    # 参数预览
    st.divider()

    # 尝试构建请求（用于预览）
    try:
        request = build_request(common_config, mode_config)
        preview_valid = True
    except ValueError as e:
        request = None
        preview_valid = False
        preview_error = str(e)

    with st.expander("📜 命令预览"):
        if preview_valid and request:
            cmd_str = preview_command(request, str(MEDIA_CRAWLER_PATH))
            st.code(cmd_str, language="bash")

            # 显示模型详情
            with st.expander("🔍 请求模型详情"):
                st.json(request.model_dump())
        else:
            st.warning(f"⏳ {preview_error}")

    # 运行按钮
    st.divider()

    # 使用 columns 布局，让开始按钮和打开目录按钮并排
    col1, col2 = st.columns([3, 1])

    with col1:
        start_button = st.button(
            "🚀 开始爬取",
            type="primary",
            use_container_width=True,
            disabled=st.session_state.is_running,
        )

    with col2:
        # 打开目录按钮（始终可用）
        if st.button("📂 打开结果目录", use_container_width=True):
            # 获取当前配置的保存路径
            save_path = common_config.get("save_path")
            open_results_directory(save_path)

    if start_button:
        if not preview_valid:
            st.error(f"❌ 配置无效: {preview_error}")
        else:
            # 保存用户偏好设置
            save_from_form_values(
                platform=common_config["platform"],
                login_type=common_config["login_type"],
                crawler_type=common_config["crawler_type"],
                save_option=common_config["save_option"],
                max_comments=common_config["max_comments"],
                get_comment=common_config["get_comment"],
                get_sub_comment=common_config["get_sub_comment"],
                headless=common_config["headless"],
                save_path=common_config.get("save_path", ""),
            )
            # 设置运行状态并重新运行以禁用按钮
            st.session_state.is_running = True
            st.rerun()

    # 如果处于运行状态，执行爬虫
    if st.session_state.is_running:
        if preview_valid and request:
            execution = run_crawler_ui(request)

            # 运行完成后，显示打开目录按钮（如果成功）
            if execution and execution.status.value == "completed":
                st.divider()
                result_col1, result_col2 = st.columns([2, 1])

                with result_col1:
                    # 显示输出文件
                    if execution.output_files:
                        with st.expander("📁 输出文件列表"):
                            for f in execution.output_files:
                                st.text(f)

                with result_col2:
                    # 快捷打开目录按钮
                    save_path = common_config.get("save_path")
                    if st.button("📂 打开结果目录", type="primary", use_container_width=True):
                        open_results_directory(save_path)

        # 重置运行状态
        st.session_state.is_running = False

    # 页脚
    st.divider()
    st.caption("Powered by MediaCrawler | Streamlit 界面 v0.2.0")


if __name__ == "__main__":
    main()
