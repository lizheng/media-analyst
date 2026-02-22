"""
MediaCrawler Streamlit 界面

Functional Core, Imperative Shell 架构：
1. Core: 构建 CrawlerRequest 模型（纯函数）
2. Shell: CrawlerRunner 执行（副作用）
"""

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
)
from media_analyst.core.params import preview_command
from media_analyst.shell import CrawlerRunner, CrawlerRunnerError

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
    with st.sidebar:
        st.header("⚙️ 基础配置")

        platform = st.selectbox(
            "选择平台",
            options=list(PLATFORMS.keys()),
            format_func=lambda x: f"{x} - {PLATFORMS[x]}",
            help="选择要爬取的平台",
        )

        login_type = st.selectbox(
            "登录方式",
            options=list(LOGIN_TYPES.keys()),
            format_func=lambda x: LOGIN_TYPES[x],
            help="选择登录方式",
        )

        crawler_type = st.selectbox(
            "爬虫类型",
            options=list(CRAWLER_TYPES.keys()),
            format_func=lambda x: CRAWLER_TYPES[x],
            help="选择爬取模式",
        )

        st.divider()
        st.header("🔧 通用设置")

        save_option = st.selectbox(
            "保存格式",
            options=SAVE_OPTIONS,
            index=0,
            help="数据保存格式",
        )

        save_path = st.text_input(
            "保存路径 (可选)",
            placeholder="默认: MediaCrawler/data/",
            help="自定义数据保存路径，留空使用默认路径",
        )

        max_comments = st.number_input(
            "单篇最大评论数",
            min_value=0,
            max_value=10000,
            value=100,
            help="每篇笔记/视频获取的最大评论数，0表示不限制",
        )

        col1, col2 = st.columns(2)
        with col1:
            get_comment = st.checkbox("获取评论", value=False)
        with col2:
            get_sub_comment = st.checkbox("获取子评论", value=False)

        headless = st.checkbox("无头模式", value=True, help="后台运行浏览器（不显示窗口）")

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


def render_detail_form() -> dict:
    """渲染详情模式表单"""
    st.subheader("📄 详情模式配置")
    specified_ids = st.text_area(
        "笔记/视频 URL 或 ID",
        placeholder="输入 URL 或 ID，多个用逗号分隔",
        help="输入要爬取的笔记或视频链接/ID",
    )
    start_page = st.number_input("起始页码", min_value=1, value=1)

    return {
        "specified_ids": specified_ids,
        "start_page": start_page,
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


def run_crawler_ui(request: SearchRequest | DetailRequest | CreatorRequest) -> None:
    """
    运行爬虫并显示结果（Shell - 副作用）
    """
    # 初始化 Runner
    try:
        runner = CrawlerRunner(MEDIA_CRAWLER_PATH)
    except CrawlerRunnerError as e:
        st.error(f"❌ {e}")
        return

    # 创建输出区域
    st.info("🔄 正在启动爬虫...")
    output_container = st.container()
    stdout_placeholder = output_container.empty()
    stderr_placeholder = output_container.empty()

    try:
        # 启动爬虫
        execution = runner.start(request)

        # 实时显示输出
        stdout_lines = []
        stderr_lines = []

        for line in runner.iter_output(execution, timeout=300):  # 5分钟超时
            if line.startswith("[stderr] "):
                stderr_lines.append(line[9:])
                # 只显示最后20行错误
                stderr_placeholder.error("\n".join(stderr_lines[-20:]))
            else:
                stdout_lines.append(line)
                # 只显示最后50行输出
                stdout_placeholder.code("\n".join(stdout_lines[-50:]), language="text")

        # 显示结果
        if execution.status.value == "completed":
            st.success(f"✅ 爬取完成！耗时 {execution.duration_seconds:.1f} 秒")

            # 显示输出文件
            if execution.output_files:
                with st.expander("📁 输出文件"):
                    for f in execution.output_files:
                        st.text(f)
        else:
            st.error(f"❌ 爬取失败: {execution.error_message or '未知错误'}")

    except TimeoutError:
        st.error("❌ 执行超时（5分钟）")
    except Exception as e:
        st.error(f"❌ 运行出错: {str(e)}")


# ========== 主应用 ==========

def main():
    """主应用入口"""
    # 页面标题
    st.title("🕷️ MediaCrawler 控制台")
    st.markdown("通过 Web 界面配置和运行 MediaCrawler，无需命令行操作")

    # 侧边栏配置
    common_config = render_sidebar()

    # 主界面 - 动态表单
    st.header("📋 爬取参数")

    crawler_type = common_config["crawler_type"]

    # 根据爬虫类型渲染不同表单
    if crawler_type == "search":
        mode_config = render_search_form()
    elif crawler_type == "detail":
        mode_config = render_detail_form()
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
    if st.button("🚀 开始爬取", type="primary", use_container_width=True):
        if not preview_valid:
            st.error(f"❌ 配置无效: {preview_error}")
            return

        # 运行爬虫（Shell - 副作用）
        run_crawler_ui(request)

    # 使用说明
    with st.expander("📖 使用说明"):
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

        ### 架构说明

        本项目采用 **Functional Core, Imperative Shell** 架构：

        - **Core（纯函数）**：数据模型（Pydantic）和参数构建逻辑，无副作用
        - **Shell（副作用）**：进程管理、文件系统操作
        - **UI（Streamlit）**：界面渲染和用户交互

        这种分离使代码更易测试、更易维护。

        ### 注意事项

        - 首次使用需要先登录获取 Cookie
        - 建议开启无头模式（后台运行）
        - 爬取频率过高可能导致账号受限，请合理设置参数
        - 数据默认保存在 MediaCrawler/data/ 目录下
        """)

    # 页脚
    st.divider()
    st.caption("Powered by MediaCrawler | Streamlit 界面 v0.2.0")


if __name__ == "__main__":
    main()
