"""
数据解析页面

与爬虫页面解耦，独立的数据解析功能：
- 选择本地 JSON 文件或目录
- 自动检测平台
- 解析为统一的数据模型
- 预览原始数据

路径基准：以 MediaCrawler 项目根目录为基准（../MediaCrawler）
"""

import json
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import streamlit as st

from media_analyst.core.models import ParsedData, Platform
from media_analyst.core.parser import (
    detect_platform_from_filename,
    parse_json_file,
    parse_json_files,
    posts_to_dataframe,
    comments_to_dataframe,
)
from media_analyst.ui.persistence import get_media_crawler_path

# MediaCrawler 根目录（作为路径基准）- 使用统一配置
MEDIA_CRAWLER_PATH = get_media_crawler_path()

# =============================================================================
# 页面配置
# =============================================================================

def init_page():
    """初始化页面状态"""
    if "parser_parsed_data" not in st.session_state:
        st.session_state.parser_parsed_data: Optional[ParsedData] = None
    if "parser_selected_files" not in st.session_state:
        st.session_state.parser_selected_files: List[str] = []
    if "parser_platform_filter" not in st.session_state:
        st.session_state.parser_platform_filter: Optional[Platform] = None


# =============================================================================
# 侧边栏配置
# =============================================================================

def find_json_files(directory: Path) -> List[Path]:
    """
    递归查找目录下所有 .json 文件

    Args:
        directory: 要搜索的目录

    Returns:
        找到的 JSON 文件路径列表
    """
    if not directory.exists():
        return []

    json_files = []
    try:
        # 递归查找所有 .json 文件，排除隐藏文件和目录
        for json_file in directory.rglob("*.json"):
            # 跳过隐藏文件（以 . 开头的文件/目录）
            if any(part.startswith(".") for part in json_file.parts):
                continue
            json_files.append(json_file)
    except PermissionError:
        st.error(f"权限错误：无法访问目录 {directory}")
        return []

    # 按修改时间排序（最新的在前）
    json_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return json_files


def render_sidebar() -> dict:
    """渲染侧边栏配置"""
    with st.sidebar:
        st.header("📂 数据文件")

        # 文件选择方式
        input_method = st.radio(
            "选择输入方式",
            ["上传文件", "输入目录"],
            help="上传本地文件或输入目录路径（递归查找 JSON 文件）"
        )

        file_paths: List[str] = []

        if input_method == "上传文件":
            uploaded_files = st.file_uploader(
                "选择 JSON 文件",
                type=["json"],
                accept_multiple_files=True,
                help="支持同时上传多个文件"
            )
            if uploaded_files:
                # 保存上传的文件到临时位置
                import tempfile
                import os

                temp_dir = tempfile.mkdtemp()
                for uploaded_file in uploaded_files:
                    temp_path = os.path.join(temp_dir, uploaded_file.name)
                    with open(temp_path, "wb") as f:
                        f.write(uploaded_file.getvalue())
                    file_paths.append(temp_path)
        else:
            # 输入目录方式
            st.caption(f"📍 路径基准: {MEDIA_CRAWLER_PATH.resolve()}")

            dir_input = st.text_input(
                "目录路径（相对于 MediaCrawler 根目录）",
                placeholder="data/douyin/json",
                help="输入目录路径，将递归查找该目录下所有 .json 文件"
            )

            if dir_input:
                # 构建绝对路径（基于 MediaCrawler 根目录）
                target_dir = MEDIA_CRAWLER_PATH / dir_input.strip()

                if target_dir.exists():
                    if target_dir.is_dir():
                        json_files = find_json_files(target_dir)
                        file_paths = [str(f) for f in json_files]

                        st.success(f"✅ 找到 {len(file_paths)} 个 JSON 文件")

                        # 显示找到的文件列表（可折叠）
                        if file_paths:
                            with st.expander(f"📄 文件列表（前20个）", expanded=False):
                                for i, f in enumerate(file_paths[:20], 1):
                                    # 显示相对路径
                                    rel_path = Path(f).relative_to(MEDIA_CRAWLER_PATH)
                                    st.text(f"{i}. {rel_path}")
                                if len(file_paths) > 20:
                                    st.caption(f"... 还有 {len(file_paths) - 20} 个文件")
                    else:
                        st.error(f"❌ {dir_input} 不是一个目录")
                else:
                    st.error(f"❌ 目录不存在: {target_dir}")

        return {
            "file_paths": file_paths,
        }


# =============================================================================
# 主界面
# =============================================================================

def render_statistics(parsed_data: ParsedData, raw_stats: dict | None = None):
    """渲染统计信息卡片"""
    st.subheader("📊 数据统计")

    # 去重统计
    dedup_stats = parsed_data.deduplication_stats
    has_duplicates = dedup_stats["total_duplicates"] > 0

    # 获取原始记录数（优先使用传入的 raw_stats）
    if raw_stats:
        original_count = raw_stats.get("total_records", parsed_data.total_records)
        original_success = raw_stats.get("success_count", parsed_data.success_count)
    else:
        original_count = parsed_data.total_records
        original_success = parsed_data.success_count

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        if has_duplicates:
            st.metric("帖子数", len(parsed_data.posts), delta=f"- {dedup_stats['duplicate_posts']}", delta_color="inverse")
        else:
            st.metric("帖子数", len(parsed_data.posts))
    with col2:
        if has_duplicates:
            st.metric("评论数", len(parsed_data.comments), delta=f"- {dedup_stats['duplicate_comments']}", delta_color="inverse")
        else:
            st.metric("评论数", len(parsed_data.comments))
    with col3:
        total_users = len(set(
            [(p.platform.value, p.user_id) for p in parsed_data.posts if p.user_id] +
            [(c.platform.value, c.user_id) for c in parsed_data.comments if c.user_id]
        ))
        st.metric("用户数", total_users)
    with col4:
        # 显示原始记录数，避免误解为"成功率"
        if has_duplicates:
            st.metric("原始记录", original_count)
        else:
            st.metric("解析记录", original_success)

    # 显示去重提示
    if has_duplicates:
        st.info(f"🔄 已自动去重：过滤了 {dedup_stats['total_duplicates']} 条重复数据（以最新抓取时间为准）")


def render_posts_table(parsed_data: ParsedData):
    """渲染帖子数据表格"""
    if not parsed_data.posts:
        st.info("📭 没有解析到帖子数据")
        return

    st.subheader(f"📝 帖子数据 ({len(parsed_data.posts)} 条)")

    # 转换为 DataFrame
    try:
        df = posts_to_dataframe(parsed_data.posts)

        # 选择要显示的列
        display_columns = [
            "content_id", "platform", "content_type", "title", "nickname",
            "liked_count", "collected_count", "comment_count", "share_count",
            "create_time", "crawl_time", "content_url"
        ]
        available_columns = [c for c in display_columns if c in df.columns]
        df_display = df[available_columns]

        # 显示表格
        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "content_id": st.column_config.TextColumn("内容ID", width="small"),
                "platform": st.column_config.TextColumn("平台", width="small"),
                "content_type": st.column_config.TextColumn("类型", width="small"),
                "title": st.column_config.TextColumn("标题", width="large"),
                "nickname": st.column_config.TextColumn("作者", width="medium"),
                "liked_count": st.column_config.NumberColumn("点赞", width="small"),
                "collected_count": st.column_config.NumberColumn("收藏", width="small"),
                "comment_count": st.column_config.NumberColumn("评论", width="small"),
                "share_count": st.column_config.NumberColumn("分享", width="small"),
                "create_time": st.column_config.TextColumn("发布时间", width="medium"),
                "crawl_time": st.column_config.DatetimeColumn("抓取时间", width="medium", format="YYYY-MM-DD HH:mm:ss"),
                "content_url": st.column_config.LinkColumn("链接", width="medium"),
            }
        )

    except ImportError:
        st.error("需要安装 pandas: uv add pandas")
    except Exception as e:
        st.error(f"表格渲染失败: {e}")


def render_comments_table(parsed_data: ParsedData):
    """渲染评论数据表格"""
    if not parsed_data.comments:
        st.info("📭 没有解析到评论数据")
        return

    st.subheader(f"💬 评论数据 ({len(parsed_data.comments)} 条)")

    try:
        df = comments_to_dataframe(parsed_data.comments)

        display_columns = [
            "comment_id", "content_id", "platform", "content", "nickname",
            "like_count", "sub_comment_count", "create_time", "crawl_time", "is_sub_comment"
        ]
        available_columns = [c for c in display_columns if c in df.columns]
        df_display = df[available_columns]

        st.dataframe(
            df_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                "comment_id": st.column_config.TextColumn("评论ID", width="small"),
                "content_id": st.column_config.TextColumn("内容ID", width="small"),
                "platform": st.column_config.TextColumn("平台", width="small"),
                "content": st.column_config.TextColumn("内容", width="large"),
                "nickname": st.column_config.TextColumn("用户", width="medium"),
                "like_count": st.column_config.NumberColumn("点赞", width="small"),
                "sub_comment_count": st.column_config.NumberColumn("回复", width="small"),
                "create_time": st.column_config.TextColumn("评论时间", width="medium"),
                "crawl_time": st.column_config.DatetimeColumn("抓取时间", width="medium", format="YYYY-MM-DD HH:mm:ss"),
                "is_sub_comment": st.column_config.CheckboxColumn("子评论", width="small"),
            }
        )

    except ImportError:
        st.error("需要安装 pandas: uv add pandas")
    except Exception as e:
        st.error(f"表格渲染失败: {e}")


def render_raw_preview(file_paths: List[str]):
    """渲染原始数据预览"""
    with st.expander("🔍 原始 JSON 预览", expanded=False):
        if not file_paths:
            st.info("请先选择文件或目录")
            return

        # 格式化显示函数：显示相对路径
        def format_path(path_str: str) -> str:
            try:
                path = Path(path_str)
                # 尝试显示相对于 MediaCrawler 的路径
                if MEDIA_CRAWLER_PATH in path.parents or path == MEDIA_CRAWLER_PATH:
                    rel_path = path.relative_to(MEDIA_CRAWLER_PATH)
                    return str(rel_path)
                return path.name
            except ValueError:
                return Path(path_str).name

        # 选择要预览的文件
        preview_file = st.selectbox(
            "选择文件预览",
            file_paths,
            format_func=format_path
        )

        if preview_file and Path(preview_file).exists():
            try:
                with open(preview_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # 显示完整路径
                full_path = Path(preview_file)
                try:
                    rel_path = full_path.relative_to(MEDIA_CRAWLER_PATH)
                    st.caption(f"📁 {rel_path}")
                except ValueError:
                    st.caption(f"📁 {full_path}")

                # 限制预览大小
                if isinstance(data, list) and len(data) > 5:
                    st.caption(f"共 {len(data)} 条记录，显示前 5 条")
                    data = data[:5]

                st.json(data)
            except Exception as e:
                st.error(f"无法预览文件: {e}")


def render_errors(parsed_data: ParsedData):
    """渲染错误信息"""
    if not parsed_data.errors:
        return

    with st.expander(f"⚠️ 解析错误 ({len(parsed_data.errors)} 个)", expanded=False):
        for error in parsed_data.errors[:20]:  # 最多显示20个
            st.warning(error)
        if len(parsed_data.errors) > 20:
            st.caption(f"... 还有 {len(parsed_data.errors) - 20} 个错误")


# =============================================================================
# 主函数
# =============================================================================

def main():
    """数据解析页面主函数"""
    st.set_page_config(
        page_title="Media Analyst - 数据解析",
        page_icon="📊",
        layout="wide"
    )

    init_page()

    # 页面标题
    st.title("📊 数据解析")
    st.caption("解析 MediaCrawler 抓取的 JSON 数据，转换为统一格式")

    # 侧边栏配置
    config = render_sidebar()

    # 主界面
    if not config["file_paths"]:
        st.info("👈 请在侧边栏选择或上传 JSON 数据文件")

        # 显示支持的格式说明
        with st.expander("📖 支持的文件格式"):
            st.markdown("""
            ### 自动检测平台
            系统会根据 JSON 字段自动检测数据所属平台：
            - **抖音** (`aweme_id`): 视频、评论数据
            - **小红书** (`note_id`): 笔记、评论数据
            - **B站** (`bvid`): 视频、评论数据

            ### 文件命名建议
            文件名中包含平台名称可以帮助更快识别：
            - `douyin_contents_2024.json`
            - `xhs_comments_2024.json`
            - `bilibili_data.json`

            ### 数据格式
            支持以下 JSON 格式：
            - 对象列表: `[{...}, {...}]`
            - 单个对象: `{...}`
            """)
        return

    # 解析按钮
    col1, col2 = st.columns([1, 4])
    with col1:
        parse_clicked = st.button("🔍 开始解析", type="primary", use_container_width=True)

    # 执行解析
    if parse_clicked:
        with st.spinner("正在解析数据..."):
            try:
                if len(config["file_paths"]) == 1:
                    raw_result = parse_json_file(config["file_paths"][0], deduplicate=False)
                else:
                    raw_result = parse_json_files(config["file_paths"], deduplicate=False)

                # 计算去重统计
                dedup_stats = raw_result.deduplication_stats
                has_duplicates = dedup_stats["total_duplicates"] > 0

                # 执行去重
                if has_duplicates:
                    result = raw_result.deduplicate()
                else:
                    result = raw_result

                st.session_state.parser_parsed_data = result
                st.session_state.parser_raw_stats = {
                    "total_records": raw_result.total_records,
                    "success_count": raw_result.success_count,
                    "duplicate_count": dedup_stats["total_duplicates"],
                    "has_duplicates": has_duplicates,
                }

                # 构建详细的成功提示
                if has_duplicates:
                    st.success(
                        f"✅ 解析完成！"
                        f"原始记录: {raw_result.total_records} 条 | "
                        f"成功解析: {raw_result.success_count} 条 | "
                        f"去重后: {len(result.posts) + len(result.comments)} 条 "
                        f"(过滤重复: {dedup_stats['total_duplicates']} 条)"
                    )
                else:
                    st.success(f"✅ 解析完成！成功 {result.success_count}/{result.total_records} 条")
            except Exception as e:
                st.error(f"❌ 解析失败: {e}")
                return

    # 显示解析结果
    parsed_data = st.session_state.parser_parsed_data
    if parsed_data:
        # 统计信息（传入原始统计数据以正确显示）
        raw_stats = st.session_state.get("parser_raw_stats")
        render_statistics(parsed_data, raw_stats)

        st.divider()

        # 数据表格
        tab1, tab2, tab3 = st.tabs(["📝 帖子", "💬 评论", "⚠️ 错误"])

        with tab1:
            render_posts_table(parsed_data)

        with tab2:
            render_comments_table(parsed_data)

        with tab3:
            render_errors(parsed_data)

        st.divider()

        # 原始数据预览
        render_raw_preview(config["file_paths"])


if __name__ == "__main__":
    main()
