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
    Comment,
    CrawlerExecution,
    CrawlerType,
    CreatorRequest,
    DetailRequest,
    ExecutionStatus,
    LoginType,
    Platform,
    Post,
    SearchRequest,
)

# ============================================================================
# SearchRequest Tests
# ============================================================================


def test_search_request_valid():
    """测试有效的搜索请求"""
    req = SearchRequest(
        platform=Platform.DY,
        keywords='美食,旅游',
        start_page=1,
    )

    assert req.platform == Platform.DY
    assert req.keywords == '美食,旅游'
    assert req.crawler_type == CrawlerType.SEARCH


def test_search_request_requires_keywords():
    """搜索模式必须提供关键词"""
    with pytest.raises(ValueError, match='搜索关键词不能为空'):
        SearchRequest(
            platform=Platform.DY,
            keywords='',
        )


def test_search_request_rejects_whitespace_only_keywords():
    """搜索模式拒绝纯空白关键词"""
    with pytest.raises(ValueError, match='搜索关键词不能为空'):
        SearchRequest(
            platform=Platform.DY,
            keywords='   ',
        )


def test_search_request_strips_whitespace():
    """搜索关键词自动去除首尾空白"""
    req = SearchRequest(
        platform=Platform.DY,
        keywords='  美食  ',
    )
    assert req.keywords == '美食'


def test_search_request_to_cli_args():
    """测试搜索请求转换为 CLI 参数"""
    req = SearchRequest(
        platform=Platform.XHS,
        login_type=LoginType.QRCODE,
        keywords='穿搭',
        start_page=2,
        get_comment=True,
        max_comments=50,
    )

    args = req.to_cli_args()

    assert '--platform' in args
    assert 'xhs' in args
    assert '--type' in args
    assert 'search' in args
    assert '--keywords' in args
    assert '穿搭' in args
    assert '--start' in args
    assert '2' in args
    assert '--get_comment' in args
    assert 'yes' in args


# ============================================================================
# DetailRequest Tests
# ============================================================================


def test_detail_request_valid():
    """测试有效的详情请求"""
    req = DetailRequest(
        platform=Platform.DY,
        specified_ids='https://douyin.com/video/123',
    )

    assert req.platform == Platform.DY
    assert req.specified_ids == 'https://douyin.com/video/123'
    assert req.crawler_type == CrawlerType.DETAIL


def test_detail_request_requires_specified_ids():
    """详情模式必须提供 ID"""
    with pytest.raises(ValueError, match='笔记/视频 ID 不能为空'):
        DetailRequest(
            platform=Platform.DY,
            specified_ids='',
        )


def test_detail_request_to_cli_args():
    """测试详情请求转换为 CLI 参数"""
    req = DetailRequest(
        platform=Platform.DY,
        specified_ids='https://douyin.com/video/123',
        get_comment=False,
        max_comments=10,
    )

    args = req.to_cli_args()

    assert '--type' in args
    assert 'detail' in args
    assert '--specified_id' in args
    assert 'https://douyin.com/video/123' in args
    assert '--max_comments_count_singlenotes' in args
    assert '10' in args


# ============================================================================
# CreatorRequest Tests
# ============================================================================


def test_creator_request_valid():
    """测试有效的创作者请求"""
    req = CreatorRequest(
        platform=Platform.KS,
        creator_ids='user123',
    )

    assert req.platform == Platform.KS
    assert req.creator_ids == 'user123'
    assert req.crawler_type == CrawlerType.CREATOR


def test_creator_request_requires_creator_ids():
    """创作者模式必须提供创作者 ID"""
    with pytest.raises(ValueError, match='创作者 ID 不能为空'):
        CreatorRequest(
            platform=Platform.KS,
            creator_ids='',
        )


def test_creator_request_to_cli_args():
    """测试创作者请求转换为 CLI 参数"""
    req = CreatorRequest(
        platform=Platform.BILI,
        creator_ids='UID123,UID456',
        headless=False,
    )

    args = req.to_cli_args()

    assert '--type' in args
    assert 'creator' in args
    assert '--creator_id' in args
    assert 'UID123,UID456' in args
    assert '--headless' in args
    assert 'no' in args


# ============================================================================
# Request Immutability Tests
# ============================================================================


def test_request_is_frozen():
    """请求模型创建后不可修改"""
    req = SearchRequest(
        platform=Platform.DY,
        keywords='测试',
    )

    with pytest.raises(Exception):
        req.keywords = '修改'


# ============================================================================
# CrawlerExecution Tests
# ============================================================================


def test_execution_creation_with_valid_request():
    """测试使用有效请求创建执行状态"""
    request = SearchRequest(
        platform=Platform.DY,
        keywords='美食',
    )

    execution = CrawlerExecution(request=request)

    assert execution.request == request
    assert execution.status == ExecutionStatus.PENDING
    assert execution.start_time is None
    assert execution.process_id is None


def test_execution_validates_nonexistent_output_files():
    """执行状态拒绝不存在的输出文件"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    nonexistent_file = Path('/tmp/definitely_not_exists_12345.json')

    with pytest.raises(ValueError, match='输出文件不存在'):
        CrawlerExecution(
            request=request,
            output_files=[nonexistent_file],
        )


def test_execution_accepts_existing_files(tmp_path: Path):
    """执行状态接受存在的文件"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    existing_file = tmp_path / 'test.json'
    existing_file.write_text('{"test": true}')

    execution = CrawlerExecution(
        request=request,
        output_files=[existing_file],
    )

    assert execution.output_files == [existing_file]


def test_execution_status_running_requires_process_id():
    """RUNNING 状态必须有 process_id"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')

    with pytest.raises(ValueError, match='running 状态必须有 process_id'):
        CrawlerExecution(
            request=request,
            status=ExecutionStatus.RUNNING,
        )


def test_execution_status_completed_requires_end_time():
    """COMPLETED 状态必须有 end_time"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')

    with pytest.raises(ValueError, match='completed 状态必须有 end_time'):
        CrawlerExecution(
            request=request,
            status=ExecutionStatus.COMPLETED,
        )


def test_execution_status_failed_requires_error():
    """FAILED 状态必须有错误信息"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')

    with pytest.raises(ValueError, match='FAILED 状态必须有 error_message 或 stderr_lines'):
        CrawlerExecution(
            request=request,
            status=ExecutionStatus.FAILED,
            end_time=datetime.now(),
        )


def test_mark_running():
    """测试标记为运行中"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    execution = CrawlerExecution(request=request)

    execution.mark_running(process_id=12345)

    assert execution.status == ExecutionStatus.RUNNING
    assert execution.process_id == 12345
    assert execution.start_time is not None


def test_mark_completed_success():
    """测试标记为成功完成"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    execution = CrawlerExecution(request=request)
    execution.mark_running(process_id=12345)

    execution.mark_completed(return_code=0)

    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.return_code == 0
    assert execution.end_time is not None


def test_mark_completed_failure():
    """测试标记为失败完成"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    execution = CrawlerExecution(request=request)
    execution.mark_running(process_id=12345)

    execution.mark_completed(return_code=1)

    assert execution.status == ExecutionStatus.FAILED
    assert execution.return_code == 1
    assert execution.error_message == '进程返回码: 1'


def test_duration_calculation():
    """测试时长计算"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
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
    request = SearchRequest(platform=Platform.DY, keywords='测试')

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
        keywords='美食',
        max_comments=50,
    )

    data = req.model_dump()

    assert data['platform'] == 'dy'
    assert data['crawler_type'] == 'search'
    assert data['keywords'] == '美食'
    assert data['max_comments'] == 50


def test_search_request_deserialization():
    """测试搜索请求反序列化"""
    data = {
        'platform': 'dy',
        'crawler_type': 'search',
        'keywords': '美食',
        'start_page': 2,
    }

    req = SearchRequest.model_validate(data)

    assert req.platform == Platform.DY
    assert req.keywords == '美食'
    assert req.start_page == 2


def test_execution_serialization():
    """测试执行状态序列化"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    execution = CrawlerExecution(request=request)
    execution.mark_running(process_id=12345)

    data = execution.model_dump()

    assert data['status'] == 'running'
    assert data['process_id'] == 12345
    assert data['request']['platform'] == 'dy'


# ============================================================================
# Mark Failed Tests
# ============================================================================


def test_mark_failed():
    """测试 mark_failed 方法"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    execution = CrawlerExecution(request=request)

    execution.mark_failed('Something went wrong')

    assert execution.status == ExecutionStatus.FAILED
    assert execution.error_message == 'Something went wrong'
    assert execution.end_time is not None


def test_mark_failed_requires_error_message():
    """测试 mark_failed 后状态验证需要 error_message"""
    from datetime import datetime

    request = SearchRequest(platform=Platform.DY, keywords='测试')

    # 创建时没有错误信息会导致验证失败
    with pytest.raises(ValueError, match='FAILED 状态必须有 error_message 或 stderr_lines'):
        CrawlerExecution(
            request=request,
            status=ExecutionStatus.FAILED,
            end_time=datetime.now(),
        )


# ============================================================================
# Output Properties Tests
# ============================================================================


def test_full_output_property():
    """测试 full_output 属性"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    execution = CrawlerExecution(request=request)

    execution.add_output('Line 1')
    execution.add_output('Line 2')
    execution.add_output('Line 3')

    assert execution.full_output == 'Line 1\nLine 2\nLine 3'


def test_full_stderr_property():
    """测试 full_stderr 属性"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    execution = CrawlerExecution(request=request)

    execution.add_output('Error 1', is_stderr=True)
    execution.add_output('Error 2', is_stderr=True)

    assert execution.full_stderr == 'Error 1\nError 2'


def test_stdout_stderr_separation():
    """测试 stdout 和 stderr 分离"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    execution = CrawlerExecution(request=request)

    execution.add_output('stdout line')
    execution.add_output('stderr line', is_stderr=True)
    execution.add_output('another stdout')

    assert 'stdout line' in execution.full_output
    assert 'another stdout' in execution.full_output
    assert 'stderr line' not in execution.full_output  # stderr 不在 stdout 中
    assert 'stderr line' in execution.full_stderr


# ============================================================================
# Update Output Files Tests
# ============================================================================


def test_update_output_files_validates_existence(tmp_path: Path):
    """测试 update_output_files 验证文件存在性"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    execution = CrawlerExecution(request=request)

    # 创建存在的文件
    existing_file = tmp_path / 'existing.json'
    existing_file.write_text('{}')

    # 应该成功
    execution.update_output_files([existing_file])
    assert execution.output_files == [existing_file]


def test_update_output_files_rejects_nonexistent():
    """测试 update_output_files 拒绝不存在的文件"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    execution = CrawlerExecution(request=request)

    with pytest.raises(ValueError, match='输出文件不存在'):
        execution.update_output_files([Path('/nonexistent/file.json')])


# ============================================================================
# Execution Properties Edge Cases
# ============================================================================


def test_duration_seconds_returns_none_when_not_started():
    """测试未开始时 duration_seconds 返回 None"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    execution = CrawlerExecution(request=request)

    assert execution.duration_seconds is None


def test_duration_seconds_while_running():
    """测试运行中的 duration_seconds"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    execution = CrawlerExecution(request=request)

    execution.mark_running(process_id=12345)

    # 应该返回非负值
    assert execution.duration_seconds is not None
    assert execution.duration_seconds >= 0


def test_is_finished_for_all_terminal_states():
    """测试所有终止状态的 is_finished 属性"""
    from datetime import datetime

    request = SearchRequest(platform=Platform.DY, keywords='测试')

    # PENDING - 未完成
    pending = CrawlerExecution(request=request, status=ExecutionStatus.PENDING)
    assert not pending.is_finished

    # RUNNING - 未完成
    running = CrawlerExecution(
        request=request,
        status=ExecutionStatus.RUNNING,
        process_id=12345,
        start_time=datetime.now(),
    )
    assert not running.is_finished

    # COMPLETED - 已完成
    completed = CrawlerExecution(
        request=request,
        status=ExecutionStatus.COMPLETED,
        end_time=datetime.now(),
    )
    assert completed.is_finished

    # FAILED - 已完成
    failed = CrawlerExecution(
        request=request,
        status=ExecutionStatus.FAILED,
        end_time=datetime.now(),
        error_message='Error',
    )
    assert failed.is_finished

    # TIMEOUT - 已完成
    timeout = CrawlerExecution(
        request=request,
        status=ExecutionStatus.TIMEOUT,
        end_time=datetime.now(),
    )
    assert timeout.is_finished

    # STOPPED - 已完成
    stopped = CrawlerExecution(
        request=request,
        status=ExecutionStatus.STOPPED,
        end_time=datetime.now(),
    )
    assert stopped.is_finished


# ============================================================================
# Timestamp Serialization Tests
# ============================================================================


def test_post_timestamp_serialization():
    """测试帖子时间戳序列化"""
    from datetime import datetime

    post = Post(
        content_id='123',
        platform=Platform.DY,
        create_time=datetime(2024, 1, 15, 10, 30, 0),
    )

    data = post.model_dump()
    assert data['create_time'] is not None


def test_post_timestamp_from_unix_int():
    """测试从整数 Unix 时间戳创建 Post"""
    post = Post(
        content_id='123',
        platform=Platform.DY,
        create_time=1705315800,  # 2024-01-15 10:30:00 UTC
    )

    assert post.create_time is not None
    assert isinstance(post.create_time, datetime)


def test_post_timestamp_from_unix_string():
    """测试从字符串 Unix 时间戳创建 Post"""
    post = Post(
        content_id='123',
        platform=Platform.DY,
        create_time='1705315800',  # 字符串形式
    )

    assert post.create_time is not None
    assert isinstance(post.create_time, datetime)


def test_comment_timestamp_serialization():
    """测试评论时间戳序列化"""
    from datetime import datetime

    comment = Comment(
        comment_id='456',
        content_id='123',
        platform=Platform.DY,
        create_time=datetime(2024, 1, 15, 10, 30, 0),
    )

    data = comment.model_dump()
    assert data['create_time'] is not None


def test_comment_pictures_parsing():
    """测试评论图片字段解析"""
    # 字符串形式（逗号分隔）
    comment1 = Comment(
        comment_id='1',
        content_id='post1',
        platform=Platform.DY,
        pictures='url1.jpg,url2.jpg,url3.jpg',
    )
    assert comment1.pictures == ['url1.jpg', 'url2.jpg', 'url3.jpg']

    # 列表形式
    comment2 = Comment(
        comment_id='2',
        content_id='post2',
        platform=Platform.DY,
        pictures=['url1.jpg', 'url2.jpg'],
    )
    assert comment2.pictures == ['url1.jpg', 'url2.jpg']

    # None
    comment3 = Comment(
        comment_id='3',
        content_id='post3',
        platform=Platform.DY,
        pictures=None,
    )
    assert comment3.pictures == []


# ============================================================================
# Status Consistency Validation Tests
# ============================================================================


def test_running_status_requires_start_time():
    """测试 RUNNING 状态需要 start_time"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')

    with pytest.raises(ValueError, match='running 状态必须有 start_time'):
        CrawlerExecution(
            request=request,
            status=ExecutionStatus.RUNNING,
            process_id=12345,
            # 缺少 start_time
        )


def test_completed_status_requires_end_time():
    """测试 COMPLETED 状态需要 end_time"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')

    with pytest.raises(ValueError, match='completed 状态必须有 end_time'):
        CrawlerExecution(
            request=request,
            status=ExecutionStatus.COMPLETED,
            # 缺少 end_time
        )


def test_failed_status_can_use_stderr_lines():
    """测试 FAILED 状态可以使用 stderr_lines 作为错误信息"""
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    from datetime import datetime

    # 有 stderr_lines 但没有 error_message 应该可以通过验证
    execution = CrawlerExecution(
        request=request,
        status=ExecutionStatus.FAILED,
        end_time=datetime.now(),
        stderr_lines=['Error line 1', 'Error line 2'],
    )
    assert execution.status == ExecutionStatus.FAILED
    assert len(execution.stderr_lines) == 2
