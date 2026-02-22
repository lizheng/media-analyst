"""
真实数据格式测试

使用模拟的 MediaCrawler 真实数据格式进行测试，
确保解析器能正确处理实际抓取的数据。
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from media_analyst.core.models import ParsedData, Platform
from media_analyst.core.parser import (
    extract_crawl_time_from_filename,
    parse_json_file,
    parse_json_files,
)


# 测试数据目录
TEST_DATA_DIR = Path(__file__).parent.parent / "data" / "douyin" / "json"


class TestRealDataFormat:
    """测试真实数据格式解析"""

    def test_parse_real_douyin_contents_format(self):
        """测试解析真实抖音内容数据格式"""
        # 使用模拟的真实数据文件
        file_path = TEST_DATA_DIR / "douyin_contents_2024_0221_143052.json"

        if not file_path.exists():
            pytest.skip("测试数据文件不存在")

        result = parse_json_file(file_path)

        # 验证解析结果
        assert isinstance(result, ParsedData)
        assert len(result.posts) == 2
        assert len(result.comments) == 0
        assert result.platform == Platform.DY

        # 验证第一个帖子的字段
        post = result.posts[0]
        assert post.content_id == "1234567890"
        assert post.platform == Platform.DY
        assert post.title == "测试视频标题"
        assert post.desc == "测试视频描述 #测试"
        assert post.nickname == "测试用户"
        assert post.liked_count == 1000
        assert post.collected_count == 500
        assert post.comment_count == 100
        assert post.share_count == 50

        # 验证时间戳转换
        assert isinstance(post.create_time, datetime)
        assert post.create_time.year == 2024

        # 验证抓取时间从文件名提取
        assert post.crawl_time is not None
        assert post.crawl_time.year == 2024
        assert post.crawl_time.month == 2
        assert post.crawl_time.day == 21

        # 验证源文件信息
        assert "douyin_contents_2024_0221_143052.json" in post.source_file

    def test_parse_real_douyin_comments_format(self):
        """测试解析真实抖音评论数据格式"""
        file_path = TEST_DATA_DIR / "douyin_comments_2024_0221_143052.json"

        if not file_path.exists():
            pytest.skip("测试数据文件不存在")

        result = parse_json_file(file_path)

        # 验证解析结果
        assert isinstance(result, ParsedData)
        assert len(result.posts) == 0
        assert len(result.comments) == 2
        assert result.platform == Platform.DY

        # 验证第一个评论的字段
        comment = result.comments[0]
        assert comment.comment_id == "comment_001"
        assert comment.content_id == "1234567890"
        assert comment.platform == Platform.DY
        assert comment.content == "这是一条测试评论"
        assert comment.nickname == "评论用户1"
        assert comment.like_count == 10
        assert comment.sub_comment_count == 2
        assert comment.is_sub_comment is False

    def test_deduplicate_with_real_data_format(self):
        """测试使用真实数据格式进行去重"""
        file1 = TEST_DATA_DIR / "douyin_contents_2024_0221_143052.json"
        file2 = TEST_DATA_DIR / "douyin_contents_2024_0222_153000.json"

        if not file1.exists() or not file2.exists():
            pytest.skip("测试数据文件不存在")

        # 解析两个文件（都包含 aweme_id=1234567890 的数据）
        result = parse_json_files([file1, file2], deduplicate=True)

        # file1: 2条, file2: 2条(其中1条重复) = 去重后 3条
        assert len(result.posts) == 3

        # 找到重复的帖子
        duplicate_post = [p for p in result.posts if p.content_id == "1234567890"]
        assert len(duplicate_post) == 1

        # 验证保留的是最新的数据（file2 的）
        post = duplicate_post[0]
        assert post.liked_count == 1500  # file2 中的值
        assert post.crawl_time.day == 22  # file2 的日期

    def test_deduplicate_stats_with_real_data(self):
        """测试真实数据的去重统计"""
        file1 = TEST_DATA_DIR / "douyin_contents_2024_0221_143052.json"
        file2 = TEST_DATA_DIR / "douyin_contents_2024_0222_153000.json"

        if not file1.exists() or not file2.exists():
            pytest.skip("测试数据文件不存在")

        # 先获取原始数据（不去重）
        raw_result = parse_json_files([file1, file2], deduplicate=False)

        # 验证原始数据统计
        assert len(raw_result.posts) == 4  # 2 + 2
        stats = raw_result.deduplication_stats
        assert stats["duplicate_posts"] == 1  # 1条重复
        assert stats["total_duplicates"] == 1

        # 去重后验证
        dedup_result = raw_result.deduplicate()
        assert len(dedup_result.posts) == 3

    def test_extract_time_from_real_filename_formats(self):
        """测试从真实文件名格式提取时间"""
        # 下划线分隔格式（MediaCrawler 默认格式）
        time = extract_crawl_time_from_filename("douyin_contents_2024_0221_143052.json")
        assert time == datetime(2024, 2, 21, 14, 30, 52)

        # 横线分隔格式
        time = extract_crawl_time_from_filename("detail_contents_2026-02-22.json")
        assert time == datetime(2026, 2, 22, 0, 0, 0)

        # 带路径的
        time = extract_crawl_time_from_filename("/path/to/douyin_data_2024_0315_120000.json")
        assert time == datetime(2024, 3, 15, 12, 0, 0)


class TestMixedContentParsing:
    """测试混合内容解析"""

    def test_parse_mixed_posts_and_comments(self):
        """测试同时解析帖子和评论"""
        contents_file = TEST_DATA_DIR / "douyin_contents_2024_0221_143052.json"
        comments_file = TEST_DATA_DIR / "douyin_comments_2024_0221_143052.json"

        if not contents_file.exists() or not comments_file.exists():
            pytest.skip("测试数据文件不存在")

        result = parse_json_files([contents_file, comments_file])

        # 验证同时包含帖子和评论
        assert len(result.posts) == 2
        assert len(result.comments) == 2
        assert result.platform == Platform.DY

    def test_string_count_conversion(self):
        """测试字符串数字转换（真实数据中计数字段是字符串）"""
        file_path = TEST_DATA_DIR / "douyin_contents_2024_0221_143052.json"

        if not file_path.exists():
            pytest.skip("测试数据文件不存在")

        result = parse_json_file(file_path)
        post = result.posts[0]

        # 验证字符串 "1000" 被正确转换为整数 1000
        assert isinstance(post.liked_count, int)
        assert post.liked_count == 1000
        assert isinstance(post.collected_count, int)
        assert post.collected_count == 500


class TestErrorHandling:
    """测试错误处理"""

    def test_parse_invalid_json(self):
        """测试解析无效 JSON"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            f.write("{invalid json content")
            temp_path = f.name

        try:
            with pytest.raises(Exception):
                parse_json_file(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_parse_empty_list(self):
        """测试解析空列表"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump([], f)
            temp_path = f.name

        try:
            result = parse_json_file(temp_path)
            assert len(result.posts) == 0
            assert len(result.comments) == 0
            assert result.success_count == 0
        finally:
            Path(temp_path).unlink()

    def test_parse_non_dict_record(self):
        """测试解析非字典类型的记录"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(["not a dict", 123, None], f)
            temp_path = f.name

        try:
            result = parse_json_file(temp_path)
            # 应该有3条错误记录
            assert len(result.errors) == 3
            assert result.success_count == 0
        finally:
            Path(temp_path).unlink()


class TestDataFrameExport:
    """测试 DataFrame 导出"""

    def test_posts_to_dataframe_with_real_data(self):
        """测试将真实帖子数据转换为 DataFrame"""
        from media_analyst.core.parser import posts_to_dataframe

        file_path = TEST_DATA_DIR / "douyin_contents_2024_0221_143052.json"

        if not file_path.exists():
            pytest.skip("测试数据文件不存在")

        result = parse_json_file(file_path)
        df = posts_to_dataframe(result.posts)

        # 验证 DataFrame 结构
        assert len(df) == 2
        assert "content_id" in df.columns
        assert "platform" in df.columns
        assert "title" in df.columns
        assert "liked_count" in df.columns

        # 验证数据类型
        assert df["liked_count"].dtype in ["int64", "int32"]

    def test_comments_to_dataframe_with_real_data(self):
        """测试将真实评论数据转换为 DataFrame"""
        from media_analyst.core.parser import comments_to_dataframe

        file_path = TEST_DATA_DIR / "douyin_comments_2024_0221_143052.json"

        if not file_path.exists():
            pytest.skip("测试数据文件不存在")

        result = parse_json_file(file_path)
        df = comments_to_dataframe(result.comments)

        # 验证 DataFrame 结构
        assert len(df) == 2
        assert "comment_id" in df.columns
        assert "content" in df.columns
        assert "like_count" in df.columns
