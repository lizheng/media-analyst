"""
CrawlerRunner 集成测试

使用 mock 测试 Runner 逻辑，不实际启动 MediaCrawler

使用函数形式编写测试
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from media_analyst.core.models import (
    ExecutionStatus,
    Platform,
    SearchRequest,
)
from media_analyst.shell.runner import (
    CrawlerRunner,
    CrawlerRunnerError,
    MediaCrawlerNotFoundError,
    ProcessError,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_media_crawler_dir(tmp_path: Path) -> Path:
    """创建模拟的 MediaCrawler 目录结构"""
    main_py = tmp_path / 'main.py'
    main_py.write_text('# mock main.py')
    return tmp_path


@pytest.fixture
def sample_request() -> SearchRequest:
    """示例搜索请求"""
    return SearchRequest(
        platform=Platform.DY,
        keywords='测试',
    )


# ============================================================================
# Initialization Tests
# ============================================================================


def test_init_with_valid_path(mock_media_crawler_dir: Path):
    """使用有效路径初始化"""
    runner = CrawlerRunner(mock_media_crawler_dir)

    assert runner.media_crawler_path == mock_media_crawler_dir
    assert runner.use_uv is True


def test_init_with_invalid_path():
    """使用无效路径初始化应失败"""
    with pytest.raises(MediaCrawlerNotFoundError, match='MediaCrawler 路径不存在'):
        CrawlerRunner(Path('/nonexistent/path'))


def test_init_without_main_py(tmp_path: Path):
    """路径存在但缺少 main.py"""
    with pytest.raises(MediaCrawlerNotFoundError, match='找不到 main.py'):
        CrawlerRunner(tmp_path)


# ============================================================================
# Start Tests
# ============================================================================


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_start_creates_execution(mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """启动后创建执行状态对象"""
    # 配置 mock
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)
    execution = runner.start(sample_request)

    assert execution.request == sample_request
    assert execution.status == ExecutionStatus.RUNNING
    assert execution.process_id == 12345
    assert execution.start_time is not None


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_start_calls_popen_with_correct_args(mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """使用正确参数调用 Popen"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)
    runner.start(sample_request)

    # 验证调用参数
    call_args = mock_popen.call_args
    cmd = call_args[0][0]

    assert cmd[0] == 'uv'
    assert cmd[1] == 'run'
    assert cmd[2] == 'main.py'
    assert '--platform' in cmd
    assert 'dy' in cmd
    assert '--keywords' in cmd
    assert '测试' in cmd


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_start_prevents_concurrent_execution(mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """防止并发执行多个爬虫"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.poll.return_value = None  # 进程仍在运行
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)

    # 启动第一个
    runner.start(sample_request)

    # 尝试启动第二个应失败
    with pytest.raises(CrawlerRunnerError, match='已有爬虫进程在运行'):
        runner.start(sample_request)


# ============================================================================
# Poll Tests
# ============================================================================


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_poll_running_process(mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """轮询运行中的进程"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.poll.return_value = None  # 仍在运行
    mock_process.stdout.readline.return_value = ''
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)
    execution = runner.start(sample_request)
    execution = runner.poll(execution)

    assert execution.status == ExecutionStatus.RUNNING


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_poll_completed_process(mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """轮询已完成的进程"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.poll.return_value = 0  # 正常退出
    mock_process.communicate.return_value = ('output\n', '')
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)
    execution = runner.start(sample_request)
    execution = runner.poll(execution)

    assert execution.status == ExecutionStatus.COMPLETED
    assert execution.return_code == 0
    assert execution.end_time is not None


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_poll_captures_output(mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """轮询时捕获输出"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.poll.return_value = 0
    mock_process.communicate.return_value = ('line1\nline2\n', 'error\n')
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)
    execution = runner.start(sample_request)
    execution = runner.poll(execution)

    assert 'line1' in execution.stdout_lines
    assert 'line2' in execution.stdout_lines


# ============================================================================
# Wait Tests
# ============================================================================


@patch('media_analyst.shell.runner.subprocess.Popen')
@patch('media_analyst.shell.runner.time.sleep')
def test_wait_until_completion(mock_sleep, mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """等待直到完成"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    # 第一次 poll 返回 None（运行中），第二次返回 0（完成）
    mock_process.poll.side_effect = [None, 0]
    mock_process.communicate.return_value = ('', '')
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)
    execution = runner.start(sample_request)
    execution = runner.wait(execution, poll_interval=0.01)

    assert execution.status == ExecutionStatus.COMPLETED


@patch('media_analyst.shell.runner.subprocess.Popen')
@patch('media_analyst.shell.runner.time.sleep')
def test_wait_timeout(mock_sleep, mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """等待超时"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.poll.return_value = None  # 一直在运行
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)
    execution = runner.start(sample_request)
    execution = runner.wait(execution, timeout=0.1, poll_interval=0.01)

    # 验证状态被标记为 TIMEOUT
    assert execution.status == ExecutionStatus.TIMEOUT


# ============================================================================
# Stop Tests
# ============================================================================


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_stop_running_process(mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """停止运行中的进程"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.poll.return_value = None
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)
    execution = runner.start(sample_request)
    execution = runner.stop(execution)

    assert execution.status == ExecutionStatus.STOPPED
    mock_process.terminate.assert_called_once()


# ============================================================================
# Property Tests
# ============================================================================


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_is_running_property(mock_popen, mock_media_crawler_dir: Path):
    """测试 is_running 属性"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.poll.return_value = None
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)

    assert not runner.is_running

    request = SearchRequest(platform=Platform.DY, keywords='测试')
    runner.start(request)

    assert runner.is_running


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_current_execution_property(mock_popen, mock_media_crawler_dir: Path):
    """测试 current_execution 属性"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)

    assert runner.current_execution is None

    request = SearchRequest(platform=Platform.DY, keywords='测试')
    execution = runner.start(request)

    assert runner.current_execution is execution


# ============================================================================
# Error Handling Tests
# ============================================================================


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_start_handles_filenotfound_error(mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """测试处理 FileNotFoundError（命令不存在）"""
    mock_popen.side_effect = FileNotFoundError('No such file: uv')

    runner = CrawlerRunner(mock_media_crawler_dir)

    with pytest.raises(ProcessError, match='找不到命令'):
        runner.start(sample_request)


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_start_handles_generic_exception(mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """测试处理通用 Exception"""
    mock_popen.side_effect = Exception('Unexpected error')

    runner = CrawlerRunner(mock_media_crawler_dir)

    with pytest.raises(ProcessError, match='启动进程失败'):
        runner.start(sample_request)


# ============================================================================
# Stop Timeout Tests
# ============================================================================


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_stop_handles_timeout_expired(mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """测试停止时超时后强制终止"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.poll.return_value = None  # 进程仍在运行
    # 第一次 wait 超时，第二次成功（kill 之后）
    mock_process.wait.side_effect = [subprocess.TimeoutExpired(cmd='test', timeout=5), 0]
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)
    execution = runner.start(sample_request)

    # 停止应该成功，即使 wait 超时
    result = runner.stop(execution)

    assert result.status == ExecutionStatus.STOPPED
    # 验证调用了 kill
    mock_process.kill.assert_called_once()


# ============================================================================
# Iter Output Tests
# ============================================================================


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_iter_output_timeout(mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """测试 iter_output 超时处理"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.poll.return_value = None  # 一直在运行
    mock_process.stdout.readline.return_value = ''
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)
    execution = runner.start(sample_request)

    # 使用很短的超时时间
    with pytest.raises(TimeoutError):
        # 消费生成器
        for _ in runner.iter_output(execution, timeout=0.01, poll_interval=0.001):
            pass


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_iter_output_reads_stderr(mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """测试 iter_output 读取 stderr 内容"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    # 第一次 poll 返回 None（运行中），第二次返回 0（完成）
    mock_process.poll.side_effect = [None, 0]
    mock_process.stdout.readline.return_value = ''
    mock_process.stderr.read.return_value = 'error message\nanother error'
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)
    execution = runner.start(sample_request)

    output_lines = list(runner.iter_output(execution, poll_interval=0.001))

    # stderr 内容应该以 [stderr] 前缀输出
    assert any('[stderr]' in line for line in output_lines)
    assert any('error message' in line for line in output_lines)


# ============================================================================
# Poll Tests with Error Cases
# ============================================================================


@patch('media_analyst.shell.runner.subprocess.Popen')
def test_poll_when_process_not_started(mock_popen, mock_media_crawler_dir: Path, sample_request: SearchRequest):
    """测试 poll 当进程未启动时"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.poll.return_value = 0  # 进程已完成
    mock_process.communicate.return_value = ('output', '')
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)
    execution = runner.start(sample_request)

    # 手动清除内部进程引用
    runner._current_process = None

    result = runner.poll(execution)

    # 应该标记为失败
    assert result.status == ExecutionStatus.FAILED
    assert '进程未启动' in result.error_message


# ============================================================================
# Wait Tests with Edge Cases
# ============================================================================


@patch('media_analyst.shell.runner.subprocess.Popen')
@patch('media_analyst.shell.runner.time.sleep')
def test_wait_with_already_finished_execution(mock_sleep, mock_popen, mock_media_crawler_dir: Path):
    """测试等待已经完成的执行"""
    mock_process = MagicMock()
    mock_process.pid = 12345
    mock_process.poll.return_value = 0
    mock_process.communicate.return_value = ('', '')
    mock_popen.return_value = mock_process

    runner = CrawlerRunner(mock_media_crawler_dir)

    # 创建一个已经完成的执行状态
    request = SearchRequest(platform=Platform.DY, keywords='测试')
    execution = runner.start(request)
    execution = runner.poll(execution)
    assert execution.is_finished

    # 再次等待应该立即返回
    result = runner.wait(execution, poll_interval=0.001)
    assert result.is_finished
