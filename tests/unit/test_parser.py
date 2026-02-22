"""
数据解析模块单元测试

测试目标：
- 平台自动检测逻辑
- 字段提取和转换
- 异常数据处理

测试数据基于 MediaCrawler 实际输出格式
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from media_analyst.core.models import Comment, ParsedData, Platform, Post
from media_analyst.core.parser import (
    detect_platform,
    detect_platform_from_filename,
    parse_comment,
    parse_json_file,
    parse_post,
    posts_to_dataframe,
)

# =============================================================================
# Fixtures - 测试数据
# =============================================================================

@pytest.fixture
def douyin_post_data():
    """抖音帖子样本数据"""
    return {
        "aweme_id": "7605333789232876826",
        "aweme_type": "0",
        "title": "测试标题",
        "desc": "测试描述 #话题",
        "create_time": 1770770520,
        "user_id": "4323725741947923",
        "sec_uid": "MS4wLjABAAAAM1dmeDLgQJseNEne5Y4Wk9KMXFG2j2vYHJ56EfJyKYERo2Ss8DhJQw_GjVoTks_M",
        "short_user_id": "83423785151",
        "user_unique_id": "TestUser",
        "user_signature": "测试签名",
        "nickname": "测试用户",
        "avatar": "https://example.com/avatar.jpg",
        "liked_count": "15057",
        "collected_count": "11502",
        "comment_count": "373",
        "share_count": "578",
        "ip_location": "北京",
        "last_modify_ts": 1771725359615,
        "aweme_url": "https://www.douyin.com/video/7605333789232876826",
        "cover_url": "https://example.com/cover.jpg",
        "video_download_url": "https://example.com/video.mp4",
        "music_download_url": "https://example.com/music.mp3",
        "note_download_url": "",
        "source_keyword": "测试关键词",
    }


@pytest.fixture
def douyin_comment_data():
    """抖音评论样本数据"""
    return {
        "comment_id": "7609314008492311337",
        "create_time": 1771681480,
        "ip_location": "山东",
        "aweme_id": "7605333789232876826",
        "content": "这是一条测试评论",
        "user_id": "4265734384134286",
        "sec_uid": "MS4wLjABAAAAeSaODM7g4805b75As8cv5hyWsRnLD2X8T2FL4GkEB93onXRDrFaA7pQIIET3Vpiz",
        "short_user_id": "3862647330",
        "user_unique_id": "test_user",
        "user_signature": None,
        "nickname": "评论用户",
        "avatar": "https://example.com/avatar.jpg",
        "sub_comment_count": "5",
        "like_count": 10,
        "last_modify_ts": 1771725361056,
        "parent_comment_id": "0",
        "pictures": "https://example.com/pic1.jpg,https://example.com/pic2.jpg",
    }


@pytest.fixture
def xhs_post_data():
    """小红书帖子样本数据"""
    return {
        "note_id": "65a1b2c3d4e5f67890123456",
        "type": "video",
        "title": "小红书测试标题",
        "desc": "小红书测试描述",
        "video_url": "https://example.com/xhs_video.mp4",
        "time": 1704067200,
        "last_update_time": 1704153600,
        "user_id": "5f1a2b3c4d5e6f7890123456",
        "nickname": "小红书用户",
        "avatar": "https://example.com/xhs_avatar.jpg",
        "liked_count": 1000,
        "collected_count": 500,
        "comment_count": 200,
        "share_count": 50,
        "ip_location": "上海",
        "image_list": "https://example.com/img1.jpg,https://example.com/img2.jpg",
        "tag_list": "美妆,护肤",
        "last_modify_ts": 1704153600000,
        "note_url": "https://www.xiaohongshu.com/explore/65a1b2c3d4e5f67890123456",
        "source_keyword": "小红书测试",
        "xsec_token": "token123",
    }


@pytest.fixture
def xhs_comment_data():
    """小红书评论样本数据"""
    return {
        "comment_id": "comment123",
        "create_time": 1704067200,
        "ip_location": "广州",
        "note_id": "65a1b2c3d4e5f67890123456",
        "content": "小红书评论内容",
        "user_id": "user123",
        "nickname": "评论者",
        "avatar": "https://example.com/comment_avatar.jpg",
        "sub_comment_count": 3,
        "pictures": "https://example.com/comment_pic.jpg",
        "parent_comment_id": 0,
        "last_modify_ts": 1704153600000,
        "like_count": 20,
    }


@pytest.fixture
def invalid_data():
    """无效数据"""
    return {"unknown_field": "value", "foo": "bar"}


# =============================================================================
# 平台检测测试
# =============================================================================

def test_detect_platform_douyin(douyin_post_data):
    """测试抖音平台检测"""
    result = detect_platform(douyin_post_data)
    assert result == Platform.DY


def test_detect_platform_xhs(xhs_post_data):
    """测试小红书平台检测"""
    result = detect_platform(xhs_post_data)
    assert result == Platform.XHS


def test_detect_platform_unknown(invalid_data):
    """测试无法识别的平台"""
    result = detect_platform(invalid_data)
    assert result is None


def test_detect_platform_from_filename():
    """测试从文件名检测平台"""
    assert detect_platform_from_filename("douyin_data.json") == Platform.DY
    assert detect_platform_from_filename("xhs_comments.json") == Platform.XHS
    assert detect_platform_from_filename("bilibili_videos.json") == Platform.BILI
    assert detect_platform_from_filename("unknown_file.json") is None


# =============================================================================
# 帖子解析测试
# =============================================================================

def test_parse_douyin_post(douyin_post_data):
    """测试解析抖音帖子"""
    post = parse_post(douyin_post_data, Platform.DY)

    assert isinstance(post, Post)
    assert post.content_id == "7605333789232876826"
    assert post.platform == Platform.DY
    assert post.title == "测试标题"
    assert post.nickname == "测试用户"
    assert post.liked_count == 15057
    assert post.collected_count == 11502
    assert isinstance(post.create_time, datetime)


def test_parse_xhs_post(xhs_post_data):
    """测试解析小红书帖子"""
    post = parse_post(xhs_post_data, Platform.XHS)

    assert isinstance(post, Post)
    assert post.content_id == "65a1b2c3d4e5f67890123456"
    assert post.platform == Platform.XHS
    assert post.content_type.value == "video"
    assert post.liked_count == 1000


def test_parse_post_auto_detect(douyin_post_data, xhs_post_data):
    """测试自动检测平台解析帖子"""
    # 抖音数据
    post1 = parse_post(douyin_post_data)
    assert post1 is not None
    assert post1.platform == Platform.DY

    # 小红书数据
    post2 = parse_post(xhs_post_data)
    assert post2 is not None
    assert post2.platform == Platform.XHS


def test_parse_post_invalid_data():
    """测试解析无效数据"""
    result = parse_post({"foo": "bar"})
    assert result is None


def test_parse_post_none_input():
    """测试解析 None 输入"""
    result = parse_post(None)
    assert result is None


# =============================================================================
# 评论解析测试
# =============================================================================

def test_parse_douyin_comment(douyin_comment_data):
    """测试解析抖音评论"""
    comment = parse_comment(douyin_comment_data, Platform.DY)

    assert isinstance(comment, Comment)
    assert comment.comment_id == "7609314008492311337"
    assert comment.content_id == "7605333789232876826"
    assert comment.platform == Platform.DY
    assert comment.content == "这是一条测试评论"
    assert comment.like_count == 10
    assert comment.sub_comment_count == 5
    assert comment.is_sub_comment is False
    assert len(comment.pictures) == 2


def test_parse_xhs_comment(xhs_comment_data):
    """测试解析小红书评论"""
    comment = parse_comment(xhs_comment_data, Platform.XHS)

    assert isinstance(comment, Comment)
    assert comment.comment_id == "comment123"
    assert comment.platform == Platform.XHS
    assert comment.like_count == 20


def test_parse_comment_auto_detect(douyin_comment_data):
    """测试自动检测平台解析评论"""
    comment = parse_comment(douyin_comment_data)
    assert comment is not None
    assert comment.platform == Platform.DY


def test_parse_comment_with_parent():
    """测试解析子评论"""
    data = {
        "comment_id": "reply123",
        "aweme_id": "video123",
        "content": "回复内容",
        "parent_comment_id": "parent456",
        "create_time": 1704067200,
        "nickname": "回复者",
    }
    comment = parse_comment(data, Platform.DY)

    assert comment is not None
    assert comment.parent_comment_id == "parent456"
    assert comment.is_sub_comment is True


# =============================================================================
# 文件解析测试
# =============================================================================

def test_parse_json_file_douyin(douyin_post_data, douyin_comment_data):
    """测试解析抖音 JSON 文件"""
    # 创建临时文件
    data = [douyin_post_data, douyin_comment_data]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        temp_path = Path(f.name)

    try:
        result = parse_json_file(temp_path)

        assert isinstance(result, ParsedData)
        assert result.platform == Platform.DY
        assert len(result.posts) == 1
        assert len(result.comments) == 1
        assert result.total_records == 2
        assert result.success_count == 2
        assert result.error_count == 0
    finally:
        temp_path.unlink()


def test_parse_json_file_xhs(xhs_post_data, xhs_comment_data):
    """测试解析小红书 JSON 文件"""
    data = [xhs_post_data, xhs_comment_data]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        temp_path = Path(f.name)

    try:
        result = parse_json_file(temp_path)

        assert result.platform == Platform.XHS
        assert len(result.posts) == 1
        assert len(result.comments) == 1
    finally:
        temp_path.unlink()


def test_parse_json_file_single_object(douyin_post_data):
    """测试解析单个对象（非列表）JSON 文件"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(douyin_post_data, f)
        temp_path = Path(f.name)

    try:
        result = parse_json_file(temp_path)

        assert result.total_records == 1
        assert len(result.posts) == 1
    finally:
        temp_path.unlink()


def test_parse_json_file_not_found():
    """测试解析不存在的文件"""
    with pytest.raises(FileNotFoundError):
        parse_json_file("/nonexistent/file.json")


def test_parse_json_file_invalid_json():
    """测试解析无效的 JSON 文件"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        f.write("invalid json content")
        temp_path = Path(f.name)

    try:
        with pytest.raises(json.JSONDecodeError):
            parse_json_file(temp_path)
    finally:
        temp_path.unlink()


def test_parse_json_file_with_errors():
    """测试解析包含无效数据的文件"""
    data = [
        {"aweme_id": "123", "nickname": "valid"},  # 有效
        {"unknown_field": "value"},  # 无效（无法识别平台）
        "not a dict",  # 无效（不是字典）
    ]

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        temp_path = Path(f.name)

    try:
        result = parse_json_file(temp_path)

        assert result.total_records == 3
        assert result.success_count == 1
        assert result.error_count == 2
        assert len(result.errors) == 2
    finally:
        temp_path.unlink()


# =============================================================================
# DataFrame 转换测试
# =============================================================================

def test_posts_to_dataframe(douyin_post_data, xhs_post_data):
    """测试帖子转 DataFrame"""
    pytest.importorskip("pandas")

    posts = [
        parse_post(douyin_post_data, Platform.DY),
        parse_post(xhs_post_data, Platform.XHS),
    ]

    df = posts_to_dataframe(posts)

    assert len(df) == 2
    assert "content_id" in df.columns
    assert "platform" in df.columns
    assert "title" in df.columns
    assert "raw_data" not in df.columns  # raw_data 应被排除


def test_posts_to_dataframe_empty():
    """测试空帖子列表转 DataFrame"""
    pytest.importorskip("pandas")

    df = posts_to_dataframe([])
    assert len(df) == 0


# =============================================================================
# 字段转换测试
# =============================================================================

def test_timestamp_conversion():
    """测试时间戳字段转换"""
    data = {
        "aweme_id": "123",
        "create_time": 1704067200,  # Unix 时间戳
        "nickname": "测试用户",
    }

    post = parse_post(data, Platform.DY)
    assert isinstance(post.create_time, datetime)
    assert post.create_time.year == 2024


def test_timestamp_string_conversion():
    """测试字符串时间戳转换"""
    data = {
        "aweme_id": "123",
        "create_time": "1704067200",  # 字符串时间戳
        "nickname": "测试用户",
    }

    post = parse_post(data, Platform.DY)
    assert isinstance(post.create_time, datetime)


def test_count_string_conversion():
    """测试字符串数字转换为整数"""
    data = {
        "aweme_id": "123",
        "liked_count": "1000",  # 字符串
        "collected_count": "500",
        "nickname": "测试用户",
    }

    post = parse_post(data, Platform.DY)
    assert post.liked_count == 1000
    assert post.collected_count == 500
    assert isinstance(post.liked_count, int)


def test_empty_string_count():
    """测试空字符串计数字段"""
    data = {
        "aweme_id": "123",
        "liked_count": "",  # 空字符串
        "nickname": "测试用户",
    }

    post = parse_post(data, Platform.DY)
    assert post.liked_count == 0


# =============================================================================
# ParsedData 统计测试
# =============================================================================

def test_parsed_data_interactions(douyin_post_data):
    """测试互动数据统计"""
    post = parse_post(douyin_post_data, Platform.DY)
    parsed = ParsedData(posts=[post])

    interactions = parsed.total_interactions
    assert interactions["likes"] == 15057
    assert interactions["collects"] == 11502
    assert interactions["comments"] == 373
    assert interactions["shares"] == 578


def test_parsed_data_user_count(douyin_post_data, douyin_comment_data):
    """测试用户数量统计"""
    post = parse_post(douyin_post_data, Platform.DY)
    comment = parse_comment(douyin_comment_data, Platform.DY)
    parsed = ParsedData(posts=[post], comments=[comment])

    # 帖子和评论是不同用户
    assert parsed.user_count == 2


def test_parsed_data_same_user_counted_once(douyin_post_data):
    """测试同一用户只统计一次"""
    # 创建两条相同用户的帖子
    data1 = douyin_post_data.copy()
    data2 = douyin_post_data.copy()
    data2["aweme_id"] = "different_id"

    post1 = parse_post(data1, Platform.DY)
    post2 = parse_post(data2, Platform.DY)
    parsed = ParsedData(posts=[post1, post2])

    # 同一用户只算一个
    assert parsed.user_count == 1


# =============================================================================
# 去重功能测试
# =============================================================================

def test_deduplicate_posts():
    """测试帖子去重：保留最新抓取的数据"""
    from datetime import datetime

    # 创建两条相同 content_id 的帖子，但抓取时间不同
    base_data = {
        "aweme_id": "same_id",
        "desc": "内容",
        "nickname": "用户",
        "liked_count": 100,
    }

    post1 = parse_post(base_data, Platform.DY)
    post1 = post1.model_copy(update={"crawl_time": datetime(2024, 1, 15, 10, 0, 0)})

    post2 = parse_post(base_data, Platform.DY)
    post2 = post2.model_copy(update={"crawl_time": datetime(2024, 1, 20, 14, 30, 0)})

    # 合并数据（包含重复）
    parsed = ParsedData(posts=[post1, post2])
    assert len(parsed.posts) == 2
    assert parsed.deduplication_stats["duplicate_posts"] == 1

    # 去重后应该只保留最新的
    deduplicated = parsed.deduplicate()
    assert len(deduplicated.posts) == 1
    assert deduplicated.posts[0].crawl_time == datetime(2024, 1, 20, 14, 30, 0)


def test_deduplicate_comments():
    """测试评论去重：保留最新抓取的数据"""
    from datetime import datetime

    base_data = {
        "comment_id": "same_comment",
        "aweme_id": "video123",
        "content": "评论内容",
        "nickname": "评论用户",
        "like_count": 50,
    }

    comment1 = parse_comment(base_data, Platform.DY)
    comment1 = comment1.model_copy(update={"crawl_time": datetime(2024, 2, 1, 8, 0, 0)})

    comment2 = parse_comment(base_data, Platform.DY)
    comment2 = comment2.model_copy(update={"crawl_time": datetime(2024, 2, 5, 16, 45, 0)})

    parsed = ParsedData(comments=[comment1, comment2])
    assert len(parsed.comments) == 2
    assert parsed.deduplication_stats["duplicate_comments"] == 1

    deduplicated = parsed.deduplicate()
    assert len(deduplicated.comments) == 1
    assert deduplicated.comments[0].crawl_time == datetime(2024, 2, 5, 16, 45, 0)


def test_deduplicate_without_crawl_time():
    """测试没有去重时间时的去重行为：保留后遇到的"""
    base_data = {
        "aweme_id": "same_id",
        "desc": "内容",
        "nickname": "用户",
    }

    post1 = parse_post(base_data, Platform.DY)
    post1 = post1.model_copy(update={"source_file": "file1.json"})

    post2 = parse_post(base_data, Platform.DY)
    post2 = post2.model_copy(update={"source_file": "file2.json"})

    parsed = ParsedData(posts=[post1, post2])
    deduplicated = parsed.deduplicate()

    # 没有去重时间时，保留后遇到的（post2）
    assert len(deduplicated.posts) == 1
    assert deduplicated.posts[0].source_file == "file2.json"


def test_deduplicate_stats_no_duplicates():
    """测试无重复数据时的统计"""
    post1 = parse_post({"aweme_id": "id1", "desc": "内容1", "nickname": "用户1"}, Platform.DY)
    post2 = parse_post({"aweme_id": "id2", "desc": "内容2", "nickname": "用户2"}, Platform.DY)

    parsed = ParsedData(posts=[post1, post2])
    stats = parsed.deduplication_stats

    assert stats["duplicate_posts"] == 0
    assert stats["duplicate_comments"] == 0
    assert stats["total_duplicates"] == 0


# =============================================================================
# 文件名时间提取测试
# =============================================================================

def test_extract_crawl_time_from_filename():
    """测试从文件名提取抓取时间"""
    from media_analyst.core.parser import extract_crawl_time_from_filename
    from datetime import datetime

    # 下划线分隔格式
    result = extract_crawl_time_from_filename("douyin_contents_2024_0222_143052.json")
    assert result == datetime(2024, 2, 22, 14, 30, 52)

    # 紧凑日期格式
    result = extract_crawl_time_from_filename("xhs_comments_20240222_143052.json")
    assert result == datetime(2024, 2, 22, 14, 30, 52)


def test_extract_crawl_time_from_invalid_filename():
    """测试无法解析的文件名返回 None"""
    from media_analyst.core.parser import extract_crawl_time_from_filename

    result = extract_crawl_time_from_filename("some_random_file.json")
    assert result is None


# =============================================================================
# 抓取时间元数据测试
# =============================================================================

def test_post_metadata_fields():
    """测试帖子模型的元数据字段"""
    from datetime import datetime

    data = {"aweme_id": "123", "desc": "测试", "nickname": "用户"}
    post = parse_post(data, Platform.DY)

    # 默认情况下元数据为空
    assert post.crawl_time is None
    assert post.source_file == ""

    # 可以更新元数据
    post_with_meta = post.model_copy(update={
        "crawl_time": datetime(2024, 1, 15, 10, 30, 0),
        "source_file": "/path/to/file.json"
    })
    assert post_with_meta.crawl_time == datetime(2024, 1, 15, 10, 30, 0)
    assert post_with_meta.source_file == "/path/to/file.json"


def test_comment_metadata_fields():
    """测试评论模型的元数据字段"""
    from datetime import datetime

    data = {"comment_id": "c123", "aweme_id": "v123", "content": "评论", "nickname": "用户"}
    comment = parse_comment(data, Platform.DY)

    # 默认情况下元数据为空
    assert comment.crawl_time is None
    assert comment.source_file == ""

    # 可以更新元数据
    comment_with_meta = comment.model_copy(update={
        "crawl_time": datetime(2024, 3, 10, 8, 15, 0),
        "source_file": "/path/to/comments.json"
    })
    assert comment_with_meta.crawl_time == datetime(2024, 3, 10, 8, 15, 0)
    assert comment_with_meta.source_file == "/path/to/comments.json"


def test_deduplicate_posts_and_comments_combined():
    """测试同时包含 Post 和 Comment 的去重"""
    from datetime import datetime

    # Post 数据
    post_data = {"aweme_id": "same_post", "desc": "内容", "nickname": "用户"}
    post1 = parse_post(post_data, Platform.DY).model_copy(
        update={"crawl_time": datetime(2024, 1, 10, 10, 0, 0)}
    )
    post2 = parse_post(post_data, Platform.DY).model_copy(
        update={"crawl_time": datetime(2024, 1, 15, 10, 0, 0)}
    )

    # Comment 数据
    comment_data = {"comment_id": "same_comment", "aweme_id": "v123", "content": "评论", "nickname": "用户"}
    comment1 = parse_comment(comment_data, Platform.DY).model_copy(
        update={"crawl_time": datetime(2024, 1, 12, 10, 0, 0)}
    )
    comment2 = parse_comment(comment_data, Platform.DY).model_copy(
        update={"crawl_time": datetime(2024, 1, 18, 10, 0, 0)}
    )

    # 合并数据
    parsed = ParsedData(posts=[post1, post2], comments=[comment1, comment2])

    # 验证去重前统计
    stats = parsed.deduplication_stats
    assert stats["duplicate_posts"] == 1
    assert stats["duplicate_comments"] == 1
    assert stats["total_duplicates"] == 2

    # 去重后验证
    deduplicated = parsed.deduplicate()
    assert len(deduplicated.posts) == 1
    assert len(deduplicated.comments) == 1

    # 验证保留的是最新数据
    assert deduplicated.posts[0].crawl_time == datetime(2024, 1, 15, 10, 0, 0)
    assert deduplicated.comments[0].crawl_time == datetime(2024, 1, 18, 10, 0, 0)


def test_parse_json_files_auto_deduplicate():
    """测试 parse_json_files 自动去重功能"""
    from media_analyst.core.parser import parse_json_files

    # 创建两个包含重复数据的临时文件
    import tempfile
    import json

    with tempfile.TemporaryDirectory() as tmpdir:
        # 文件1：旧数据
        file1 = Path(tmpdir) / "douyin_2024_0115_100000.json"
        data1 = [{"aweme_id": "same_id", "desc": "旧内容", "nickname": "用户", "liked_count": 100}]
        with open(file1, "w", encoding="utf-8") as f:
            json.dump(data1, f)

        # 文件2：新数据（相同ID，更新内容）
        file2 = Path(tmpdir) / "douyin_2024_0120_120000.json"
        data2 = [{"aweme_id": "same_id", "desc": "新内容", "nickname": "用户", "liked_count": 200}]
        with open(file2, "w", encoding="utf-8") as f:
            json.dump(data2, f)

        # 测试自动去重（默认）
        result_dedup = parse_json_files([file1, file2], deduplicate=True)
        assert len(result_dedup.posts) == 1
        # 应该保留最新数据（文件2的）
        assert result_dedup.posts[0].liked_count == 200

        # 测试不去重
        result_no_dedup = parse_json_files([file1, file2], deduplicate=False)
        assert len(result_no_dedup.posts) == 2
