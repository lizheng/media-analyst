"""
MediaCrawler Streamlit 界面
提供一个用户友好的 Web 界面来配置和运行 MediaCrawler
"""

import streamlit as st
import subprocess
import os
from pathlib import Path

# 页面配置
st.set_page_config(
    page_title="MediaCrawler 控制台",
    page_icon="🕷️",
    layout="wide",
)

# MediaCrawler 路径
MEDIA_CRAWLER_PATH = Path("../MediaCrawler")

# 平台配置
PLATFORMS = {
    "xhs": "小红书",
    "dy": "抖音",
    "ks": "快手",
    "bili": "B站",
    "wb": "微博",
    "tieba": "贴吧",
    "zhihu": "知乎",
}

# 登录方式
LOGIN_TYPES = {
    "qrcode": "扫码登录",
    "phone": "手机号登录",
    "cookie": "Cookie 登录",
}

# 爬虫类型
CRAWLER_TYPES = {
    "search": "搜索模式",
    "detail": "详情模式",
    "creator": "创作者模式",
}

# 保存格式
SAVE_OPTIONS = ["json", "csv", "excel", "sqlite", "db", "mongodb", "postgres"]


def run_crawler(args: list) -> subprocess.Popen:
    """运行 MediaCrawler"""
    cmd = ["uv", "run", "main.py"] + args
    return subprocess.Popen(
        cmd,
        cwd=MEDIA_CRAWLER_PATH,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def build_args(
    platform: str,
    login_type: str,
    crawler_type: str,
    keywords: str = "",
    specified_ids: str = "",
    creator_ids: str = "",
    start_page: int = 1,
    get_comment: bool = False,
    get_sub_comment: bool = False,
    headless: bool = True,
    save_option: str = "json",
    max_comments: int = 100,
    save_path: str = "",
) -> list:
    """构建命令行参数"""
    args = [
        "--platform", platform,
        "--lt", login_type,
        "--type", crawler_type,
        "--start", str(start_page),
        "--save_data_option", save_option,
        "--max_comments_count_singlenotes", str(max_comments),
    ]

    if crawler_type == "search" and keywords:
        args.extend(["--keywords", keywords])
    elif crawler_type == "detail" and specified_ids:
        args.extend(["--specified_id", specified_ids])
    elif crawler_type == "creator" and creator_ids:
        args.extend(["--creator_id", creator_ids])

    if get_comment:
        args.append("--get_comment")
        args.append("yes")
    else:
        args.append("--get_comment")
        args.append("no")

    if get_sub_comment:
        args.append("--get_sub_comment")
        args.append("yes")
    else:
        args.append("--get_sub_comment")
        args.append("no")

    if headless:
        args.append("--headless")
        args.append("yes")
    else:
        args.append("--headless")
        args.append("no")

    if save_path:
        args.extend(["--save_data_path", save_path])

    return args


# 页面标题
st.title("🕷️ MediaCrawler 控制台")
st.markdown("通过 Web 界面配置和运行 MediaCrawler，无需命令行操作")

# 侧边栏配置
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

# 主界面 - 动态表单
st.header("📋 爬取参数")

if crawler_type == "search":
    st.subheader("🔍 搜索模式配置")
    keywords = st.text_area(
        "搜索关键词",
        placeholder="输入关键词，多个用逗号分隔，如：美食,旅游,穿搭",
        help="输入要搜索的关键词",
    )
    start_page = st.number_input("起始页码", min_value=1, value=1, help="从第几页开始爬取")

elif crawler_type == "detail":
    st.subheader("📄 详情模式配置")
    specified_ids = st.text_area(
        "笔记/视频 URL 或 ID",
        placeholder="输入 URL 或 ID，多个用逗号分隔",
        help="输入要爬取的笔记或视频链接/ID",
    )
    start_page = st.number_input("起始页码", min_value=1, value=1)

elif crawler_type == "creator":
    st.subheader("👤 创作者模式配置")
    creator_ids = st.text_area(
        "创作者主页 URL 或 ID",
        placeholder="输入创作者主页 URL 或 ID，多个用逗号分隔",
        help="输入创作者主页链接或ID",
    )
    start_page = st.number_input("起始页码", min_value=1, value=1)

# 参数预览
st.divider()
with st.expander("📜 命令预览"):
    # 构建参数用于显示
    preview_args = build_args(
        platform=platform,
        login_type=login_type,
        crawler_type=crawler_type,
        keywords=locals().get("keywords", ""),
        specified_ids=locals().get("specified_ids", ""),
        creator_ids=locals().get("creator_ids", ""),
        start_page=start_page,
        get_comment=get_comment,
        get_sub_comment=get_sub_comment,
        headless=headless,
        save_option=save_option,
        max_comments=max_comments,
        save_path=save_path,
    )
    cmd_str = f"cd {MEDIA_CRAWLER_PATH} && uv run main.py " + " ".join(preview_args)
    st.code(cmd_str, language="bash")

# 运行按钮
st.divider()
if st.button("🚀 开始爬取", type="primary", use_container_width=True):
    # 验证必填参数
    if crawler_type == "search" and not keywords:
        st.error("❌ 搜索模式需要填写关键词")
    elif crawler_type == "detail" and not specified_ids:
        st.error("❌ 详情模式需要填写笔记/视频 URL 或 ID")
    elif crawler_type == "creator" and not creator_ids:
        st.error("❌ 创作者模式需要填写创作者 ID")
    else:
        # 构建参数
        run_args = build_args(
            platform=platform,
            login_type=login_type,
            crawler_type=crawler_type,
            keywords=locals().get("keywords", ""),
            specified_ids=locals().get("specified_ids", ""),
            creator_ids=locals().get("creator_ids", ""),
            start_page=start_page,
            get_comment=get_comment,
            get_sub_comment=get_sub_comment,
            headless=headless,
            save_option=save_option,
            max_comments=max_comments,
            save_path=save_path,
        )

        # 显示运行状态
        st.info("🔄 正在启动爬虫...")

        # 创建输出区域
        output_container = st.container()

        try:
            # 运行爬虫
            process = run_crawler(run_args)

            # 实时显示输出
            stdout_placeholder = output_container.empty()
            stderr_placeholder = output_container.empty()

            stdout_output = []
            stderr_output = []

            # 读取输出
            while True:
                stdout_line = process.stdout.readline()
                stderr_line = process.stderr.readline()

                if stdout_line:
                    stdout_output.append(stdout_line)
                    stdout_placeholder.code("".join(stdout_output[-50:]), language="text")

                if stderr_line:
                    stderr_output.append(stderr_line)
                    stderr_placeholder.error("".join(stderr_output[-20:]))

                if process.poll() is not None and not stdout_line and not stderr_line:
                    break

            # 等待进程结束
            return_code = process.wait()

            if return_code == 0:
                st.success("✅ 爬取完成！")
            else:
                st.error(f"❌ 爬取失败，返回码: {return_code}")

        except Exception as e:
            st.error(f"❌ 运行出错: {str(e)}")

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

    ### 注意事项

    - 首次使用需要先登录获取 Cookie
    - 建议开启无头模式（后台运行）
    - 爬取频率过高可能导致账号受限，请合理设置参数
    - 数据默认保存在 MediaCrawler/data/ 目录下

    ### 常见问题

    **Q: 如何获取 Cookie？**
    A: 首次使用选择"扫码登录"，扫码成功后 Cookie 会自动保存。

    **Q: 爬取的数据在哪里？**
    A: 默认保存在 MediaCrawler/data/ 目录下，可以在"保存路径"中自定义。

    **Q: 可以同时爬取多个平台吗？**
    A: 每次只能选择一个平台，需要多次运行来爬取不同平台。
    """)

# 页脚
st.divider()
st.caption("Powered by MediaCrawler | Streamlit 界面 v0.1.0")
