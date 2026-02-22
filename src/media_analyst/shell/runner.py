"""
CrawlerRunner - 爬虫执行器

职责：管理 MediaCrawler 进程的生命周期（含副作用）
- 启动进程
- 轮询状态
- 停止进程
"""
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Iterator, List, Optional

from media_analyst.core.models import (
    CrawlerExecution,
    CrawlerRequest,
    ExecutionStatus,
)
from media_analyst.core.params import build_command


class CrawlerRunnerError(Exception):
    """爬虫运行器错误"""
    pass


class MediaCrawlerNotFoundError(CrawlerRunnerError):
    """MediaCrawler 路径不存在"""
    pass


class ProcessError(CrawlerRunnerError):
    """进程操作错误"""
    pass


class CrawlerRunner:
    """
    爬虫执行器

    封装所有与 subprocess 相关的副作用，便于：
    1. 测试时 mock 替换
    2. 将来扩展为远程执行（Docker/SSH/K8s）

    Usage:
        runner = CrawlerRunner(Path("../MediaCrawler"))
        execution = runner.start(request)

        # 非阻塞轮询
        while not execution.is_finished:
            execution = runner.poll(execution)
            time.sleep(0.1)

        # 或阻塞等待
        execution = runner.wait(execution, timeout=300)
    """

    def __init__(
        self,
        media_crawler_path: Path,
        use_uv: bool = True,
    ):
        """
        初始化 Runner

        Args:
            media_crawler_path: MediaCrawler 项目路径
            use_uv: 是否使用 uv run 执行

        Raises:
            MediaCrawlerNotFoundError: 如果路径不存在
        """
        self.media_crawler_path = Path(media_crawler_path)
        self.use_uv = use_uv

        # 验证路径存在（立即失败原则）
        if not self.media_crawler_path.exists():
            raise MediaCrawlerNotFoundError(
                f"MediaCrawler 路径不存在: {self.media_crawler_path.absolute()}"
            )

        # 验证 main.py 存在
        self.main_py = self.media_crawler_path / "main.py"
        if not self.main_py.exists():
            raise MediaCrawlerNotFoundError(
                f"找不到 main.py: {self.main_py}"
            )

        # 跟踪当前运行的进程
        self._current_process: Optional[subprocess.Popen] = None
        self._current_execution: Optional[CrawlerExecution] = None

    def start(self, request: CrawlerRequest) -> CrawlerExecution:
        """
        启动爬虫

        Args:
            request: 爬虫请求模型

        Returns:
            CrawlerExecution: 执行状态对象

        Raises:
            ProcessError: 如果启动失败
            CrawlerRunnerError: 如果已有进程在运行
        """
        # 检查是否有进程在运行
        if self._current_process is not None and self._current_process.poll() is None:
            raise CrawlerRunnerError("已有爬虫进程在运行，请先停止")

        # 构建命令
        cmd = build_command(request, use_uv=self.use_uv)

        # 创建执行状态对象
        execution = CrawlerExecution(request=request)

        try:
            # 启动进程
            process = subprocess.Popen(
                cmd,
                cwd=self.media_crawler_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # 行缓冲
            )
        except FileNotFoundError as e:
            raise ProcessError(f"找不到命令: {cmd[0]}。请确保已安装 uv") from e
        except Exception as e:
            raise ProcessError(f"启动进程失败: {e}") from e

        # 更新状态
        execution.mark_running(process.pid)

        # 保存引用
        self._current_process = process
        self._current_execution = execution

        return execution

    def poll(self, execution: CrawlerExecution) -> CrawlerExecution:
        """
        轮询获取最新状态（非阻塞）

        Args:
            execution: 当前执行状态

        Returns:
            更新后的执行状态
        """
        if execution.is_finished:
            return execution

        if self._current_process is None:
            execution.mark_failed("进程未启动")
            return execution

        process = self._current_process

        # 读取可用输出（非阻塞）
        # 注意：Popen.stdout.readline() 在 bufsize=1 和 text=True 时
        # 会尽可能读取，但如果没有新行会阻塞，所以我们需要谨慎

        # 简单实现：只检查进程是否结束
        return_code = process.poll()

        if return_code is not None:
            # 进程已结束，读取剩余输出
            stdout, stderr = process.communicate()
            if stdout:
                for line in stdout.split('\n'):
                    if line:
                        execution.add_output(line)
            if stderr:
                for line in stderr.split('\n'):
                    if line:
                        execution.add_output(line, is_stderr=True)

            # 标记完成
            execution.mark_completed(return_code)

            # 清理
            self._current_process = None
            self._current_execution = None

        return execution

    def iter_output(
        self,
        execution: CrawlerExecution,
        timeout: Optional[float] = None,
        poll_interval: float = 0.1,
    ) -> Iterator[str]:
        """
        迭代输出（阻塞，生成器模式）

        适用于 UI 实时显示输出

        Args:
            execution: 执行状态
            timeout: 超时时间（秒），None 表示不超时
            poll_interval: 轮询间隔（秒）

        Yields:
            输出行（实时）

        Raises:
            TimeoutError: 如果超时
        """
        if self._current_process is None:
            raise ProcessError("进程未启动")

        process = self._current_process
        start_time = time.time()

        # 实时读取输出
        while True:
            # 检查超时
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    self.stop(execution)
                    raise TimeoutError(f"执行超时（{timeout}秒）")

            # 读取一行（阻塞直到有数据或进程结束）
            line = process.stdout.readline() if process.stdout else ""

            if line:
                line = line.rstrip('\n')
                execution.add_output(line)
                yield line

            # 检查进程是否结束
            return_code = process.poll()
            if return_code is not None and not line:
                # 读取 stderr 剩余内容
                if process.stderr:
                    stderr_remaining = process.stderr.read()
                    if stderr_remaining:
                        for err_line in stderr_remaining.split('\n'):
                            if err_line:
                                execution.add_output(err_line, is_stderr=True)
                                yield f"[stderr] {err_line}"

                execution.mark_completed(return_code)
                self._current_process = None
                self._current_execution = None
                break

            if not line:
                # 没有新数据，短暂等待
                time.sleep(poll_interval)

    def wait(
        self,
        execution: CrawlerExecution,
        timeout: Optional[float] = None,
        poll_interval: float = 0.1,
    ) -> CrawlerExecution:
        """
        等待执行完成（阻塞）

        Args:
            execution: 执行状态
            timeout: 超时时间（秒），None 表示不超时
            poll_interval: 轮询间隔（秒）

        Returns:
            最终执行状态

        Raises:
            TimeoutError: 如果超时
        """
        start_time = time.time()

        while not execution.is_finished:
            # 检查超时
            if timeout is not None:
                elapsed = time.time() - start_time
                if elapsed > timeout:
                    self.stop(execution)
                    execution.mark_timeout()
                    return execution

            # 轮询
            execution = self.poll(execution)

            if not execution.is_finished:
                time.sleep(poll_interval)

        return execution

    def stop(self, execution: CrawlerExecution) -> CrawlerExecution:
        """
        停止执行中的爬虫

        Args:
            execution: 执行状态

        Returns:
            更新后的执行状态
        """
        if execution.is_finished:
            return execution

        if self._current_process is None:
            execution.mark_failed("进程未启动")
            return execution

        process = self._current_process

        # 尝试优雅终止
        process.terminate()

        try:
            # 等待 5 秒
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # 强制终止
            process.kill()
            process.wait()

        execution.mark_stopped()

        # 清理
        self._current_process = None
        self._current_execution = None

        return execution

    @property
    def is_running(self) -> bool:
        """是否有进程在运行"""
        if self._current_process is None:
            return False
        return self._current_process.poll() is None

    @property
    def current_execution(self) -> Optional[CrawlerExecution]:
        """当前执行状态"""
        return self._current_execution
