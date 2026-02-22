"""
Core Models 单元测试

测试 Pydantic 模型的：
1. 验证逻辑（让不合法状态无法表示）
2. 序列化/反序列化
3. 业务方法（to_cli_args）

使用函数形式编写测试，一个文件一个模型或主题
"""

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from media_analyst.core.models import (
    CrawlerExecution,
    CrawlerType,
    CreatorRequest,
    DetailRequest,
    ExecutionStatus,
    LoginType,
    Platform,
    SaveOption,
    SearchRequest,
)


# ============================================================================
# SearchRequest Tests
# ============================================================================

def test_search_request_valid():
    """测试有效的搜索请求"""
    req = SearchRequest(
        platform=Platform.DY,
        keywords="美食,旅游",
        start_page=1,
    )

    assert req.platform == Platform.DY
    assert req.keywords == "美食,旅游"
    assert req.crawler_type == CrawlerType.SEARCH


def test_search_request_requires_keywords():
    """搜索模式必须提供关键词"""
    with pytest.raises(ValueError, match="搜索关键词不能为空"):
        SearchRequest(
            platform=Platform.DY,
            keywords="",
        )


def test_search_request_rejects_whitespace_only_keywords():
    """搜索模式拒绝纯空白关键词"""
    with pytest.raises(ValueError, match="搜索关键词不能为空"):
        SearchRequest(
            platform=Platform.DY,
            keywords="   ",
        )


def test_search_request_strips_whitespace():
    """搜索关键词自动去除首尾空白"""
    req = SearchRequest(
        platform=Platform.DY,
        keywords="  美食  ",
    )
    assert req.keywords == "美食"


def test_search_request_to_cli_args():
    """测试搜索请求转换为 CLI 参数"""
    req = SearchRequest(
        platform=Platform.XHS,
        login_type=LoginType.QRCODE,
        keywords="穿搭",
        start_page=2,
        get_comment=True,
        max_comments=50,
    )

    args = req.to_cli_args()

    assert "--platform" in args
    assert "xhs" in args
    assert "--type" in args
    assert "search" in args
    assert "--keywords" in args
    assert "穿搭" in args
    assert "--start" in args
    assert "2" in args
    assert "--get_comment" in args
    assert "yes" in args


# ============================================================================
# DetailRequest Tests
# ============================================================================

def test_detail_request_valid():
    """测试有效的详情请求"""
    req = DetailRequest(
        platform=Platform.DY,
        specified_ids="https://douyin.com/video/123",
    )

    assert req.platform == Platform.DY
    assert req.specified_ids == "https://douyin.com/video/123"
    assert req.crawler_type == CrawlerType.DETAIL


def test_detail_request_requires_specified_ids():
    """详情模式必须提供 ID"""
    with pytest.raises(ValueError, match="笔记/视频 ID 不能为空"):
        DetailRequest(
            platform=Platform.DY,
            specified_ids="",
        )


def test_detail_request_to_cli_args():
    """测试详情请求转换为 CLI 参数"""
    req = DetailRequest(
        platform=Platform.DY,
        specified_ids="https://douyin.com/video/123",
        get_comment=False,
        max_comments=10,
    )

    args = req.to_cli_args()

    assert "--type" in args
    assert "detail" in args
    assert "--specified_id" in args
    assert "https://douyin.com/video/123" in args
    assert "--max_comments_count_singlenotes" in args
    assert "10" in args


# ============================================================================
# CreatorRequest Tests
# ============================================================================

def test_creator_request_valid():
    """测试有效的创作者请求"""
    req = CreatorRequest(
        platform=Platform.KS,
        creator_ids="user123",
    )

    assert req.platform == Platform.KS
    assert req.creator_ids == "user123"
    assert req.crawler_type == CrawlerType.CREATOR


def test_creator_request_requires_creator_ids():
    """创作者模式必须提供创作者 ID"""
    with pytest.raises(ValueError, match="创作者 ID 不能为空"):
        CreatorRequest(
            platform=Platform.KS,
            creator_ids="",
        )


def test_creator_request_to_cli_args():
    """测试创作者请求转换为 CLI 参数"""
    req = CreatorRequest(
        platform=Platform.BILI,
        creator_ids="UID123,UID456",
        headless=False,
    )

    args = req.to_cli_args()

    assert "--type" in args
    assert "creator" in args
    assert "--creator_id" in args
    assert "UID123,UID456" in args
    assert "--headless" in args
    assert "no" in args


# ============================================================================
# Request Immutability Tests
# ============================================================================

def test_request_is_frozen():
    """请求模型创建后不可修改"""
    req = SearchRequest(
        platform=Platform.DY,
        keywords="测试",
    )

    with pytest.raises(Exception):
        req.keywords = "修改"


# ============================================================================
# CrawlerExecution Tests
# ============================================================================

def test_execution_creation_with_valid_request():
    """测试使用有效请求创建执行状态"""
    request = SearchRequest(
        platform=Platform.DY,
        keywords="美食",
    )

    execution = CrawlerExecution(request=request)

    assert execution.request == request
    assert execution.status == ExecutionStatus.PENDING
    assert execution.start_time is None
    assert execution.process_id is None


def test_execution_validates_nonexistent_output_files():
    """执行状态拒绝不存在的输出文件"""
    request = SearchRequest(platform=Platform.DY, keywords="测试")
    nonexistent_file = Path("/tmp/definitely_not_exists_12345.json")

    with pytest.raises(ValueError, match="输出文件不存在"):
        CrawlerExecution(
            request=request,
            output_files=[nonexistent_file],
        )


def test_execution_accepts_existing_files(tmp_path: Path):
    """执行状态接受存在的文件"""
    request = SearchRequest(platform=Platform.DY, keywords="测试")
    existing_file = tmp_path / "test.json"
    existing_file.write_text('{"test": true}')

    execution = CrawlerExecution(
        request=request,
        output_files=[existing_file],
    )

    assert execution.output_files == [existing_file]


def test_execution_status_running_requires_process_id():
    """RUNNING 状态必须有 process_id"""
    request = SearchRequest(platform=Platform.DY, keywords="测试")

    with pytest.raises(ValueError, match="running 状态必须有 process_id"):
        CrawlerExecution(
            request=request,
            status=ExecutionStatus.RUNNING,
        )


def test_execution_status_completed_requires_end_time():
    """COMPLETED 状态必须有 end_time"""
    request = SearchRequest(platform=Platform.DY, keywords="测试")

    with pytest.raises(ValueError, match="completed 状态必须有 end_time"):
        CrawlerExecution(
            request=request,
            status=ExecutionStatus.COMPLETED,
        )


def test_execution_status_failed_requires_error():
    """FAILED 状态必须有错误信息"""
    request = SearchRequest(platform=Platform.DY, keywords="测试")

    with pytest.raises(ValueError, match="FAILED 状态必须有 error_message 或 stderr_lines"):
        CrawlerExecution(
            request=request,
            status=ExecutionStatus.FAILED,
            end_time=datetime.now(),
        )


def test_mark_running():
    """测试标记为运行中"""
    request = SearchRequest(platform=Platform.DY, keywords="测试")
    execution = CrawlerExecution(request=request)

    execution.mark_running(process_id=12345)

    assert execution.status == ExecutionStatus.RUNNING
    assert execution.process_id == 12345
    assert execution.start_time is not None


def test_mark_completed_success():
    """测试标记为成功完成"""
    request = SearchRequest(platform=Platform.DY, keywords="测试")
    execution = CrawlerExecution(request=request)
    execution.mark_running(process_id=12345)

    execution.mark_completed(return_code=0)

    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.return_code == 0
    assert execution.end_time is not None


def test_mark_completed_failure():
    """测试标记为失败完成"""
    request = SearchRequest(platform=Platform.DY, keywords="测试")
    execution = CrawlerExecution(request=request)
    execution.mark_running(process_id=12345)

    execution.mark_completed(return_code=1)

    assert execution.status == ExecutionStatus.FAILED
    assert execution.return_code == 1
    assert execution.error_message == "进程返回码: 1"


def test_duration_calculation():
    """测试时长计算"""
    request = SearchRequest(platform=Platform.DY, keywords="测试")
    execution = CrawlerExecution(request=request)

    # 未开始
    assert execution.duration_seconds is None

    # 运行中
    execution.mark_running(process_id=12345)
    assert execution.duration_seconds >= 0

    # 已结束
    execution.end_time = execution.start_time + timedelta(seconds=5)
    execution.status = ExecutionStatus.COMPLETED
    assert execution.duration_seconds == 5.0


def test_is_finished_property():
    """测试 is_finished 属性"""
    request = SearchRequest(platform=Platform.DY, keywords="测试")

    pending = CrawlerExecution(request=request, status=ExecutionStatus.PENDING)
    running = CrawlerExecution(
        request=request,
        status=ExecutionStatus.RUNNING,
        process_id=12345,
        start_time=datetime.now(),
    )
    completed = CrawlerExecution(
        request=request,
        status=ExecutionStatus.COMPLETED,
        end_time=datetime.now(),
    )

    assert not pending.is_finished
    assert not running.is_finished
    assert completed.is_finished


# ============================================================================
# Model Serialization Tests
# ============================================================================

def test_search_request_serialization():
    """测试搜索请求序列化"""
    req = SearchRequest(
        platform=Platform.DY,
        keywords="美食",
        max_comments=50,
    )

    data = req.model_dump()

    assert data["platform"] == "dy"
    assert data["crawler_type"] == "search"
    assert data["keywords"] == "美食"
    assert data["max_comments"] == 50


def test_search_request_deserialization():
    """测试搜索请求反序列化"""
    data = {
        "platform": "dy",
        "crawler_type": "search",
        "keywords": "美食",
        "start_page": 2,
    }

    req = SearchRequest.model_validate(data)

    assert req.platform == Platform.DY
    assert req.keywords == "美食"
    assert req.start_page == 2


def test_execution_serialization():
    """测试执行状态序列化"""
    request = SearchRequest(platform=Platform.DY, keywords="测试")
    execution = CrawlerExecution(request=request)
    execution.mark_running(process_id=12345)

    data = execution.model_dump()

    assert data["status"] == "running"
    assert data["process_id"] == 12345
    assert data["request"]["platform"] == "dy"
