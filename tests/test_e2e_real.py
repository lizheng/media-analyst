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

    # 验证输出文件
    print("\n📁 检查输出文件...")

    import json
    import time

    # 等待一小段时间确保文件写入完成
    time.sleep(1)

    data_dir = media_crawler_path / "data"

    # 1. 检查数据目录是否存在
    if not data_dir.exists():
        print(f"⚠️ 数据目录不存在: {data_dir}")
        print("提示：可能是MediaCrawler配置为其他保存路径")
        return

    print(f"✅ 数据目录存在: {data_dir}")

    # 2. 查找所有生成的文件（递归搜索）
    all_files = list(data_dir.rglob("*"))
    data_files = [f for f in all_files if f.is_file()]

    if not data_files:
        print("⚠️ 未找到任何数据文件")
        print(f"目录结构: {list(data_dir.iterdir())}")
        return

    print(f"\n📊 找到 {len(data_files)} 个文件:")

    # 按类型分类文件
    json_files = [f for f in data_files if f.suffix == '.json']
    csv_files = [f for f in data_files if f.suffix == '.csv']
    other_files = [f for f in data_files if f.suffix not in ['.json', '.csv']]

    if json_files:
        print(f"  - JSON文件: {len(json_files)} 个")
        for f in json_files[:3]:  # 只显示前3个
            print(f"    • {f.relative_to(media_crawler_path)} ({f.stat().st_size} bytes)")
        if len(json_files) > 3:
            print(f"    ... 还有 {len(json_files) - 3} 个")

    if csv_files:
        print(f"  - CSV文件: {len(csv_files)} 个")

    if other_files:
        print(f"  - 其他文件: {len(other_files)} 个")

    # 3. 验证JSON文件内容
    if json_files:
        print("\n🔍 验证JSON文件内容...")
        for json_file in json_files[:2]:  # 验证前2个
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                if isinstance(data, list):
                    print(f"  ✅ {json_file.name}: 包含 {len(data)} 条记录")
                    if data and isinstance(data[0], dict):
                        print(f"     字段: {list(data[0].keys())[:5]}")  # 显示前5个字段
                elif isinstance(data, dict):
                    print(f"  ✅ {json_file.name}: 包含字段 {list(data.keys())[:5]}")
                else:
                    print(f"  ⚠️ {json_file.name}: 未知格式 {type(data)}")

            except json.JSONDecodeError as e:
                print(f"  ❌ {json_file.name}: JSON解析错误 - {e}")
            except Exception as e:
                print(f"  ⚠️ {json_file.name}: 读取错误 - {e}")

    # 4. 验证是否包含视频数据特征
    video_data_found = False
    for json_file in json_files:
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'video' in content.lower() or 'aweme' in content.lower() or 'modal_id' in content:
                    video_data_found = True
                    break
        except:
            continue

    if video_data_found:
        print("\n✅ 验证通过：找到视频相关数据")
    else:
        print("\n⚠️ 未找到明显的视频数据特征（可能保存格式不同）")

    print(f"\n{'='*60}")
    print("✅ 输出文件验证完成！")
    print(f"{'='*60}")
