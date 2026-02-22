"""
真实执行MediaCrawler的E2E测试

这些测试会实际启动MediaCrawler进程，需要：
1. MediaCrawler已安装在 ../MediaCrawler
2. 人类介入扫码登录（首次运行）
3. 网络连接正常

运行命令:
    uv run pytest tests/test_e2e_real.py -v -s

参数说明:
    -v: 详细输出
    -s: 显示stdout（让用户看到二维码和爬取日志）
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest


# 超时时间（秒）- 5分钟，允许扫码和爬取
TEST_TIMEOUT = 300


def run_crawler_with_live_output(cmd: list, cwd: Path, timeout: int = TEST_TIMEOUT) -> int:
    """
    运行爬虫并实时输出stdout/stderr

    Args:
        cmd: 命令列表
        cwd: 工作目录
        timeout: 超时时间（秒）

    Returns:
        进程返回码

    Raises:
        TimeoutError: 如果进程超时
        RuntimeError: 如果进程启动失败
    """
    print(f"\n{'='*60}")
    print(f"启动 MediaCrawler...")
    print(f"命令: {' '.join(cmd)}")
    print(f"工作目录: {cwd}")
    print(f"超时时间: {timeout}秒")
    print(f"{'='*60}\n")

    # 启动进程，使用行缓冲
    try:
        process = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # 合并stderr到stdout
            text=True,
            bufsize=1,  # 行缓冲
        )
    except FileNotFoundError as e:
        raise RuntimeError(f"找不到命令: {cmd[0]}。请确保已安装uv工具") from e
    except Exception as e:
        raise RuntimeError(f"启动进程失败: {e}") from e

    # 实时读取并输出
    start_time = time.time()
    output_lines = []

    try:
        while True:
            # 检查是否超时
            elapsed = time.time() - start_time
            if elapsed > timeout:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise TimeoutError(f"测试超时（{timeout}秒）。请检查是否需要扫码，或调整超时时间")

            # 读取一行输出
            line = process.stdout.readline()
            if line:
                line = line.rstrip('\n')
                output_lines.append(line)
                # 实时打印到控制台
                print(line, flush=True)

            # 检查进程是否结束
            ret = process.poll()
            if ret is not None and not line:
                break

        return ret

    except KeyboardInterrupt:
        print("\n接收到中断信号，正在终止进程...")
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise

    finally:
        # 确保关闭管道
        process.stdout.close()


@pytest.mark.real_crawler
@pytest.mark.human_interaction
@pytest.mark.timeout(TEST_TIMEOUT)
def test_douyin_detail_real(media_crawler_path: Path, douyin_detail_command: list):
    """
    测试抖音详情模式真实执行

    此测试会：
    1. 启动MediaCrawler抖音详情模式
    2. 显示二维码供用户扫码登录（首次）
    3. 爬取指定视频的详情和评论
    4. 验证进程正常结束

    前置条件：
    - MediaCrawler已安装在 ../MediaCrawler
    - 网络连接正常
    - 首次运行需要扫码登录

    预期结果：
    - 进程返回码为0
    - 爬取数据保存到默认路径
    """
    # 验证MediaCrawler路径存在
    if not media_crawler_path.exists():
        pytest.fail(f"MediaCrawler路径不存在: {media_crawler_path.absolute()}. "
                    f"请确保MediaCrawler已安装在正确位置")

    # 验证main.py存在
    main_py = media_crawler_path / "main.py"
    if not main_py.exists():
        pytest.fail(f"找不到 main.py: {main_py}")

    # 运行爬虫
    return_code = run_crawler_with_live_output(
        cmd=douyin_detail_command,
        cwd=media_crawler_path,
        timeout=TEST_TIMEOUT
    )

    # 验证返回码
    assert return_code == 0, f"爬虫进程异常退出，返回码: {return_code}"

    print(f"\n{'='*60}")
    print("✅ 爬取成功完成！")
    print(f"{'='*60}")


@pytest.mark.real_crawler
@pytest.mark.human_interaction
@pytest.mark.timeout(TEST_TIMEOUT)
def test_douyin_detail_with_output_verification(media_crawler_path: Path):
    """
    测试抖音详情模式并验证输出文件

    此测试会：
    1. 执行抖音详情模式爬取
    2. 验证输出数据文件是否生成
    """
    # 验证MediaCrawler路径存在
    if not media_crawler_path.exists():
        pytest.skip(f"MediaCrawler路径不存在: {media_crawler_path.absolute()}")

    cmd = [
        "uv", "run", "main.py",
        "--platform", "dy",
        "--lt", "qrcode",
        "--type", "detail",
        "--specified_id", "https://www.douyin.com/jingxuan?modal_id=7605333789232876826",
        "--get_comment", "yes",
        "--max_comments_count_singlenotes", "10",
        "--save_data_option", "json",
        "--headless", "no",
    ]

    return_code = run_crawler_with_live_output(
        cmd=cmd,
        cwd=media_crawler_path,
        timeout=TEST_TIMEOUT
    )

    assert return_code == 0, f"爬虫进程异常退出，返回码: {return_code}"

    # TODO(human): 实现输出文件验证逻辑
    # 任务：在下面的代码块中实现数据文件验证
    #
    # 背景：MediaCrawler爬取的数据默认保存在 MediaCrawler/data/ 目录下
    # 抖音数据的保存路径通常是：data/dy/日期/ 或 data/douyin/日期/
    #
    # 需要验证：
    # 1. 数据目录是否存在
    # 2. 是否生成了JSON/CSV等数据文件
    # 3. 文件内容是否包含预期的视频数据
    #
    # 指导：
    # - 使用 Path 和 glob 查找生成的文件
    # - 考虑数据保存可能有延迟，可能需要短暂等待
    # - 可以先打印找到的目录结构帮助调试
    # - 如果文件不存在，打印提示信息但不导致测试失败（因为可能是配置问题）

    print("\n📁 检查输出文件...")
    # 在这里实现你的验证代码
    for f in (media_crawler_path / 'data').glob('*.json'):
        print(f)

    print("✅ 测试完成！请检查 data/ 目录下的输出文件")
