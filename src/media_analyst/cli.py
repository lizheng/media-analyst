"""
Media Analyst CLI 入口

提供命令行入口点，启动 Streamlit 应用
"""

import subprocess
import sys
from pathlib import Path


def main():
    """CLI 入口：启动 Streamlit 应用"""
    # 获取 app.py 的绝对路径
    app_path = Path(__file__).parent / "ui" / "app.py"

    # 使用 subprocess 启动 streamlit
    # 这样可以确保 streamlit 的上下文正确初始化
    result = subprocess.run(
        [sys.executable, "-m", "streamlit", "run", str(app_path)],
        check=False,
    )

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
