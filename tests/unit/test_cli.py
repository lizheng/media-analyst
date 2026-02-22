"""
CLI 入口单元测试

测试命令行接口的正确性和错误处理
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from media_analyst.cli import main

# ============================================================================
# Main Function Tests
# ============================================================================


def test_main_calls_streamlit_run():
    """验证 main() 使用正确的参数调用 streamlit run"""
    with patch('media_analyst.cli.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        with pytest.raises(SystemExit):
            main()

        # 验证 subprocess.run 被调用
        mock_run.assert_called_once()
        call_args = mock_run.call_args

        # 验证命令结构
        cmd = call_args[0][0]
        assert cmd[0] == sys.executable
        assert cmd[1] == '-m'
        assert cmd[2] == 'streamlit'
        assert cmd[3] == 'run'
        assert cmd[4].endswith('app.py')


def test_main_exits_with_returncode():
    """验证 main() 使用子进程的返回码退出"""
    with patch('media_analyst.cli.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=42)

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 42


def test_main_exits_with_zero_on_success():
    """验证成功时返回码为 0"""
    with patch('media_analyst.cli.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 0


def test_main_exits_with_nonzero_on_failure():
    """验证失败时返回非零返回码"""
    with patch('media_analyst.cli.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=1)

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1


def test_main_app_path_resolution():
    """验证 app.py 路径正确解析"""
    with patch('media_analyst.cli.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        with pytest.raises(SystemExit):
            main()

        call_args = mock_run.call_args
        app_path = call_args[0][0][4]

        # 验证路径存在且是文件
        path_obj = Path(app_path)
        assert path_obj.exists()
        assert path_obj.name == 'app.py'
        assert path_obj.parent.name == 'ui'


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_main_handles_subprocess_failure():
    """验证处理子进程执行失败"""
    with patch('media_analyst.cli.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=127)

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 127


def test_main_propagates_exception_on_subprocess_error():
    """验证子进程异常被正确传播"""
    with patch('media_analyst.cli.subprocess.run') as mock_run:
        mock_run.side_effect = OSError('Command not found')

        with pytest.raises(OSError, match='Command not found'):
            main()


# ============================================================================
# Module Entry Point Tests
# ============================================================================


def test_module_entry_point():
    """验证模块可以直接运行"""
    import media_analyst.cli as cli_module

    # 检查 main 函数存在
    assert hasattr(cli_module, 'main')
    assert callable(cli_module.main)


def test_main_check_false():
    """验证 check=False 允许非零返回码不抛出异常"""
    with patch('media_analyst.cli.subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=1)

        # 不应该抛出 CalledProcessError，因为 check=False
        with pytest.raises(SystemExit):
            main()

        # 验证 check=False 被传递
        call_kwargs = mock_run.call_args[1]
        assert call_kwargs.get('check') is False
