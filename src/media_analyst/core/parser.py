"""
数据解析模块（Functional Core）

将 MediaCrawler 抓取的 JSON 数据解析为统一的 Pydantic 模型。

设计原则：
- 纯函数：无副作用，相同输入产生相同输出
- 防御性：处理字段缺失、类型不一致等异常情况
- 可扩展：通过平台注册表支持新平台

数据流：
JSON文件 -> detect_platform() -> parse_post/parse_comment() -> Post/Comment模型
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from media_analyst.core.models import Comment, ParsedData, Platform, Post

# =============================================================================
# 平台检测
# =============================================================================

# 平台字段特征映射（用于自动检测）
PLATFORM_SIGNATURES = {
    Platform.DY: {"content_id_fields": ["aweme_id"], "user_id_fields": ["sec_uid"]},
    Platform.XHS: {"content_id_fields": ["note_id"], "user_id_fields": ["user_id"]},
    Platform.BILI: {"content_id_fields": ["bvid", "video_id"], "user_id_fields": ["mid", "owner_mid"]},
    Platform.KS: {"content_id_fields": ["photo_id", "work_id"], "user_id_fields": ["user_id", "author_id"]},
    Platform.WB: {"content_id_fields": ["mid", "weibo_id"], "user_id_fields": ["user_id", "uid"]},
    Platform.TIEBA: {"content_id_fields": ["thread_id", "post_id"], "user_id_fields": ["user_id"]},
    Platform.ZHIHU: {"content_id_fields": ["question_id", "answer_id"], "user_id_fields": ["id", "uid"]},
}


def detect_platform(data: Dict[str, Any]) -> Optional[Platform]:
    """
    根据字段特征自动检测数据所属平台

    Args:
        data: 单条数据记录

    Returns:
        检测到的平台，无法检测则返回 None

    Examples:
        >>> detect_platform({"aweme_id": "123", "sec_uid": "xxx"})
        Platform.DY
        >>> detect_platform({"note_id": "456", "title": "xxx"})
        Platform.XHS
    """
    if not isinstance(data, dict):
        return None

    data_keys = set(data.keys())

    # 优先检查评论特有字段（避免将评论误判为帖子）
    # 抖音评论有 comment_id 和 aweme_id，小红书评论有 comment_id 和 note_id
    if "comment_id" in data_keys:
        # 有 aweme_id 的是抖音评论，有 note_id 的是小红书评论
        if "aweme_id" in data_keys:
            return Platform.DY
        if "note_id" in data_keys:
            return Platform.XHS

    for platform, signatures in PLATFORM_SIGNATURES.items():
        # 检查内容ID字段
        for field in signatures["content_id_fields"]:
            if field in data_keys:
                return platform

    return None


def detect_platform_from_filename(filename: str) -> Optional[Platform]:
    """
    从文件名检测平台

    Args:
        filename: 文件名或路径

    Returns:
        检测到的平台，无法检测则返回 None
    """
    filename_lower = filename.lower()

    platform_map = {
        "douyin": Platform.DY,
        "dy": Platform.DY,
        "xiaohongshu": Platform.XHS,
        "xhs": Platform.XHS,
        "bilibili": Platform.BILI,
        "bili": Platform.BILI,
        "kuaishou": Platform.KS,
        "ks": Platform.KS,
        "weibo": Platform.WB,
        "wb": Platform.WB,
        "tieba": Platform.TIEBA,
        "zhihu": Platform.ZHIHU,
    }

    for key, platform in platform_map.items():
        if key in filename_lower:
            return platform

    return None


def extract_crawl_time_from_filename(filename: str) -> Optional[datetime]:
    """
    从文件名中提取抓取时间

    MediaCrawler 生成的文件名格式通常包含时间戳：
    - douyin_contents_2024_0222_143052.json
    - xhs_comments_2024_02_22_14_30_52.json
    - 支持多种日期分隔符：_、-、无分隔符

    Args:
        filename: 文件名

    Returns:
        解析到的 datetime，无法解析则返回 None
    """
    import re

    # 提取文件名（不含路径和扩展名）
    base_name = Path(filename).stem

    # 模式1: _2024_0222_143052 (下划线分隔，紧凑格式)
    pattern1 = r"_(\d{4})_?(\d{2})_?(\d{2})_?(\d{2})_?(\d{2})_?(\d{2})"
    # 模式2: _2024-02-22-14-30-52 (横线分隔)
    pattern2 = r"_(\d{4})-(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})"
    # 模式3: _20240222_143052 (日期紧凑，时间下划线)
    pattern3 = r"_(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})"

    for pattern in [pattern1, pattern2, pattern3]:
        match = re.search(pattern, base_name)
        if match:
            try:
                year, month, day, hour, minute, second = map(int, match.groups())
                return datetime(year, month, day, hour, minute, second)
            except (ValueError, TypeError):
                continue

    # 只有日期的格式（没有时间部分）
    # 模式4: _2024-02-22 或 _2024_02_22
    date_patterns = [
        r"_(\d{4})-(\d{2})-(\d{2})(?:\.|_|$)",  # _2024-02-22.json 或 _2024-02-22_
        r"_(\d{4})_(\d{2})_(\d{2})(?:\.|_|$)",  # _2024_02_22.json
    ]
    for pattern in date_patterns:
        match = re.search(pattern, base_name)
        if match:
            try:
                year, month, day = map(int, match.groups())
                return datetime(year, month, day, 0, 0, 0)
            except (ValueError, TypeError):
                continue

    # 尝试文件修改时间作为备选
    try:
        path = Path(filename)
        if path.exists():
            mtime = path.stat().st_mtime
            return datetime.fromtimestamp(mtime)
    except (OSError, ValueError):
        pass

    return None


# =============================================================================
# 字段提取器（平台特定）
# =============================================================================

def _get_field(data: Dict[str, Any], *field_names: str, default: Any = None) -> Any:
    """
    尝试从多个字段名中获取第一个存在的值

    Args:
        data: 数据字典
        field_names: 可能的字段名列表
        default: 默认值

    Returns:
        第一个存在的字段值，或默认值
    """
    for name in field_names:
        if name in data and data[name] is not None:
            return data[name]
    return default


def _extract_common_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    """提取各平台共通的字段"""
    return {
        "user_id": _get_field(data, "user_id", "uid", "author_id", default=""),
        "nickname": _get_field(data, "nickname", "user_name", "author_name", default=""),
        "avatar": _get_field(data, "avatar", "avatar_url", "user_avatar", default=""),
        "ip_location": _get_field(data, "ip_location", "ip_label", "location", default=""),
        "source_keyword": _get_field(data, "source_keyword", "keyword", default=""),
    }


# =============================================================================
# 平台特定解析器
# =============================================================================

def _parse_douyin_post(data: Dict[str, Any]) -> Post:
    """解析抖音帖子数据"""
    common = _extract_common_fields(data)

    # 构建媒体URL列表
    media_urls = []
    video_url = data.get("video_download_url", "")
    if video_url:
        media_urls.append(video_url)
    note_urls = data.get("note_download_url", "")
    if note_urls:
        media_urls.extend([url.strip() for url in note_urls.split(",") if url.strip()])

    return Post(
        content_id=_get_field(data, "aweme_id", default=""),
        platform=Platform.DY,
        content_type="video" if video_url else "note",
        title=data.get("title", ""),
        desc=data.get("desc", ""),
        content_url=data.get("aweme_url", ""),
        cover_url=data.get("cover_url", ""),
        media_urls=media_urls,
        create_time=data.get("create_time"),
        last_modify_ts=data.get("last_modify_ts"),
        sec_uid=data.get("sec_uid", ""),
        short_user_id=data.get("short_user_id", ""),
        user_unique_id=data.get("user_unique_id", ""),
        user_signature=data.get("user_signature", ""),
        liked_count=data.get("liked_count", 0),
        collected_count=data.get("collected_count", 0),
        comment_count=data.get("comment_count", 0),
        share_count=data.get("share_count", 0),
        raw_data=data,
        **common,
    )


def _parse_douyin_comment(data: Dict[str, Any]) -> Comment:
    """解析抖音评论数据"""
    common = _extract_common_fields(data)
    parent_id = data.get("parent_comment_id", "0")

    return Comment(
        comment_id=_get_field(data, "comment_id", "cid", default=""),
        content_id=_get_field(data, "aweme_id", default=""),
        platform=Platform.DY,
        content=data.get("content", ""),
        pictures=data.get("pictures", ""),
        create_time=data.get("create_time"),
        last_modify_ts=data.get("last_modify_ts"),
        sec_uid=data.get("sec_uid", ""),
        short_user_id=data.get("short_user_id", ""),
        user_unique_id=data.get("user_unique_id", ""),
        user_signature=data.get("user_signature"),
        like_count=data.get("like_count", 0),
        sub_comment_count=data.get("sub_comment_count", 0),
        parent_comment_id=parent_id if parent_id != "0" else None,
        is_sub_comment=parent_id is not None and parent_id != "0",
        raw_data=data,
        **common,
    )


def _parse_xhs_post(data: Dict[str, Any]) -> Post:
    """解析小红书帖子数据"""
    common = _extract_common_fields(data)

    # 构建媒体URL列表
    media_urls = []
    video_url = data.get("video_url", "")
    if video_url:
        media_urls.append(video_url)
    image_urls = data.get("image_list", "")
    if image_urls:
        media_urls.extend([url.strip() for url in image_urls.split(",") if url.strip()])

    # 时间字段处理（小红书使用 time 字段，Unix 时间戳）
    create_time = data.get("time")

    return Post(
        content_id=_get_field(data, "note_id", default=""),
        platform=Platform.XHS,
        content_type=data.get("type", "unknown"),
        title=data.get("title", ""),
        desc=data.get("desc", ""),
        content_url=data.get("note_url", ""),
        cover_url="",  # 小红书没有单独的封面字段
        media_urls=media_urls,
        create_time=create_time,
        last_modify_ts=data.get("last_modify_ts"),
        liked_count=data.get("liked_count", 0),
        collected_count=data.get("collected_count", 0),
        comment_count=data.get("comment_count", 0),
        share_count=data.get("share_count", 0),
        raw_data=data,
        **common,
    )


def _parse_xhs_comment(data: Dict[str, Any]) -> Comment:
    """解析小红书评论数据"""
    common = _extract_common_fields(data)
    parent_id = data.get("parent_comment_id", 0)

    return Comment(
        comment_id=_get_field(data, "comment_id", "id", default=""),
        content_id=_get_field(data, "note_id", default=""),
        platform=Platform.XHS,
        content=data.get("content", ""),
        pictures=data.get("pictures", ""),
        create_time=data.get("create_time"),
        last_modify_ts=data.get("last_modify_ts"),
        like_count=data.get("like_count", 0),
        sub_comment_count=data.get("sub_comment_count", 0),
        parent_comment_id=str(parent_id) if parent_id else None,
        is_sub_comment=parent_id is not None and parent_id != 0,
        raw_data=data,
        **common,
    )


def _parse_bilibili_post(data: Dict[str, Any]) -> Post:
    """解析B站视频数据"""
    common = _extract_common_fields(data)

    return Post(
        content_id=_get_field(data, "bvid", "video_id", default=""),
        platform=Platform.BILI,
        content_type="video",
        title=data.get("title", ""),
        desc=data.get("desc", ""),
        content_url=data.get("video_url", ""),
        cover_url=data.get("cover", ""),
        media_urls=[data.get("video_url", "")] if data.get("video_url") else [],
        create_time=data.get("create_time"),
        last_modify_ts=data.get("last_modify_ts"),
        user_id=_get_field(data, "mid", "owner_mid", default=""),
        liked_count=data.get("like_count", 0),
        collected_count=data.get("favorite_count", 0),
        comment_count=data.get("comment_count", 0),
        share_count=data.get("share_count", 0),
        raw_data=data,
        **common,
    )


def _parse_bilibili_comment(data: Dict[str, Any]) -> Comment:
    """解析B站评论数据"""
    common = _extract_common_fields(data)
    parent_id = data.get("parent_comment_id", 0)

    return Comment(
        comment_id=_get_field(data, "comment_id", "rpid", default=""),
        content_id=_get_field(data, "bvid", "video_id", default=""),
        platform=Platform.BILI,
        content=data.get("content", ""),
        pictures=data.get("pictures", []),
        create_time=data.get("create_time"),
        last_modify_ts=data.get("last_modify_ts"),
        user_id=_get_field(data, "mid", "member_id", default=""),
        like_count=data.get("like_count", 0),
        sub_comment_count=data.get("reply_count", 0),
        parent_comment_id=str(parent_id) if parent_id else None,
        is_sub_comment=parent_id is not None and parent_id != 0,
        raw_data=data,
        **common,
    )


# 平台解析器注册表
POST_PARSERS: Dict[Platform, Callable[[Dict[str, Any]], Post]] = {
    Platform.DY: _parse_douyin_post,
    Platform.XHS: _parse_xhs_post,
    Platform.BILI: _parse_bilibili_post,
}

COMMENT_PARSERS: Dict[Platform, Callable[[Dict[str, Any]], Comment]] = {
    Platform.DY: _parse_douyin_comment,
    Platform.XHS: _parse_xhs_comment,
    Platform.BILI: _parse_bilibili_comment,
}


# =============================================================================
# 公共解析接口
# =============================================================================

def parse_post(data: Dict[str, Any], platform: Optional[Platform] = None) -> Optional[Post]:
    """
    解析单条帖子数据

    Args:
        data: 原始数据字典
        platform: 指定平台（可选，会自动检测）

    Returns:
        Post 对象，解析失败返回 None
    """
    if not isinstance(data, dict):
        return None

    # 自动检测平台
    if platform is None:
        platform = detect_platform(data)

    if platform is None or platform not in POST_PARSERS:
        return None

    try:
        return POST_PARSERS[platform](data)
    except Exception:
        # 解析失败返回 None（防御性设计）
        return None


def parse_comment(data: Dict[str, Any], platform: Optional[Platform] = None) -> Optional[Comment]:
    """
    解析单条评论数据

    Args:
        data: 原始数据字典
        platform: 指定平台（可选，会自动检测）

    Returns:
        Comment 对象，解析失败返回 None
    """
    if not isinstance(data, dict):
        return None

    # 自动检测平台
    if platform is None:
        platform = detect_platform(data)

    if platform is None or platform not in COMMENT_PARSERS:
        return None

    try:
        return COMMENT_PARSERS[platform](data)
    except Exception:
        return None


def parse_json_file(file_path: Union[str, Path], deduplicate: bool = False) -> ParsedData:
    """
    解析 JSON 数据文件

    自动检测文件内容类型（帖子/评论）和平台

    Args:
        file_path: JSON 文件路径
        deduplicate: 是否自动去重（默认 False，单文件通常不需要去重）

    Returns:
        ParsedData 包含解析后的帖子和评论列表

    Raises:
        FileNotFoundError: 文件不存在
        json.JSONDecodeError: JSON 格式错误
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"文件不存在: {file_path}")

    # 读取并解析 JSON
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 确保是列表
    if isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        raise ValueError(f"不支持的 JSON 格式: {type(data)}")

    # 从文件名检测平台和抓取时间
    platform_from_name = detect_platform_from_filename(str(path))
    crawl_time = extract_crawl_time_from_filename(str(path))
    source_file = str(path)

    # 初始化结果
    posts: List[Post] = []
    comments: List[Comment] = []
    errors: List[str] = []
    detected_platform: Optional[Platform] = None

    # 解析每条记录
    for idx, record in enumerate(data):
        if not isinstance(record, dict):
            errors.append(f"第 {idx + 1} 条记录不是字典类型")
            continue

        # 先尝试自动检测平台
        detected = platform_from_name or detect_platform(record)

        # 根据字段特征判断是评论还是帖子
        # 评论通常有 comment_id 或 content + parent_comment_id
        is_comment = "comment_id" in record or ("content" in record and "parent_comment_id" in record)

        if is_comment:
            # 尝试解析为评论
            comment = parse_comment(record, detected)
            if comment:
                # 添加抓取时间和源文件信息
                if crawl_time or source_file:
                    comment = comment.model_copy(update={
                        "crawl_time": crawl_time,
                        "source_file": source_file,
                    })
                comments.append(comment)
                if detected_platform is None:
                    detected_platform = comment.platform
                continue
        else:
            # 尝试解析为帖子
            post = parse_post(record, detected)
            if post:
                # 添加抓取时间和源文件信息
                if crawl_time or source_file:
                    post = post.model_copy(update={
                        "crawl_time": crawl_time,
                        "source_file": source_file,
                    })
                posts.append(post)
                if detected_platform is None:
                    detected_platform = post.platform
                continue

        # 都无法解析
        errors.append(f"第 {idx + 1} 条记录无法识别平台或格式")

    result = ParsedData(
        posts=posts,
        comments=comments,
        platform=detected_platform,
        total_records=len(data),
        success_count=len(posts) + len(comments),
        error_count=len(errors),
        errors=errors,
    )

    # 单文件也可能包含重复数据（如多次抓取的合并文件）
    if deduplicate and (len(posts) > 0 or len(comments) > 0):
        return result.deduplicate()

    return result


def parse_json_files(file_paths: List[Union[str, Path]], deduplicate: bool = True) -> ParsedData:
    """
    批量解析多个 JSON 文件

    Args:
        file_paths: JSON 文件路径列表
        deduplicate: 是否自动去重（默认 True）

    Returns:
        合并的 ParsedData（已去重，如果 deduplicate=True）
    """
    all_posts: List[Post] = []
    all_comments: List[Comment] = []
    all_errors: List[str] = []
    total_records = 0
    detected_platform: Optional[Platform] = None

    for file_path in file_paths:
        try:
            result = parse_json_file(file_path)
            all_posts.extend(result.posts)
            all_comments.extend(result.comments)
            all_errors.extend(result.errors)
            total_records += result.total_records
            if detected_platform is None and result.platform:
                detected_platform = result.platform
        except Exception as e:
            all_errors.append(f"{file_path}: {str(e)}")

    merged_data = ParsedData(
        posts=all_posts,
        comments=all_comments,
        platform=detected_platform,
        total_records=total_records,
        success_count=len(all_posts) + len(all_comments),
        error_count=len(all_errors),
        errors=all_errors,
    )

    # 自动去重（默认启用）
    if deduplicate and (len(all_posts) > 0 or len(all_comments) > 0):
        return merged_data.deduplicate()

    return merged_data


# =============================================================================
# 数据导出
# =============================================================================

def posts_to_dataframe(posts: List[Post]) -> Any:
    """
    将 Post 列表转换为 pandas DataFrame

    Args:
        posts: Post 列表

    Returns:
        pandas DataFrame
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("需要安装 pandas: uv add pandas")

    if not posts:
        return pd.DataFrame()

    # 转换为字典列表（排除 raw_data）
    data = []
    for post in posts:
        d = post.model_dump(exclude={"raw_data"})
        # 转换 datetime 为字符串
        if d.get("create_time"):
            d["create_time"] = d["create_time"].isoformat() if isinstance(d["create_time"], datetime) else d["create_time"]
        data.append(d)

    return pd.DataFrame(data)


def comments_to_dataframe(comments: List[Comment]) -> Any:
    """
    将 Comment 列表转换为 pandas DataFrame

    Args:
        comments: Comment 列表

    Returns:
        pandas DataFrame
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("需要安装 pandas: uv add pandas")

    if not comments:
        return pd.DataFrame()

    # 转换为字典列表（排除 raw_data）
    data = []
    for comment in comments:
        d = comment.model_dump(exclude={"raw_data"})
        # 转换 datetime 为字符串
        if d.get("create_time"):
            d["create_time"] = d["create_time"].isoformat() if isinstance(d["create_time"], datetime) else d["create_time"]
        data.append(d)

    return pd.DataFrame(data)
