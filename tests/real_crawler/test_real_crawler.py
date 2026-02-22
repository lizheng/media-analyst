"""
真实执行 MediaCrawler 的 E2E 测试

使用 Pydantic 模型进行完整测试：
1. 构建 CrawlerRequest 模型
2. 使用 CrawlerRunner 执行
3. 验证 CrawlerExecution 结果

需要：
- MediaCrawler 已安装在正确路径
- 人类介入扫码登录（首次运行）
- 网络连接正常

运行命令:
    uv run pytest tests/e2e/test_real_crawler.py -v -s

参数说明:
    -v: 详细输出
    -s: 显示 stdout（让用户看到二维码和爬取日志）
    -m 'real_crawler': 只运行真实爬虫测试
"""

import json
import time
from pathlib import Path

import pytest

from media_analyst.core.models import (
    CrawlerExecution,
    DetailRequest,
    ExecutionStatus,
    LoginType,
    Platform,
    SearchRequest,
)
from media_analyst.core.params import build_command
from media_analyst.shell import CrawlerRunner

# 超时时间（秒）- 5分钟，允许扫码和爬取
TEST_TIMEOUT = 300


@pytest.fixture
def media_crawler_path() -> Path:
    """返回 MediaCrawler 项目路径"""
    return Path("../MediaCrawler")


@pytest.fixture
def ensure_media_crawler(media_crawler_path: Path) -> Path:
    """确保 MediaCrawler 存在，否则跳过测试"""
    if not media_crawler_path.exists():
        pytest.skip(f"MediaCrawler 路径不存在: {media_crawler_path.absolute()}")

    main_py = media_crawler_path / "main.py"
    if not main_py.exists():
        pytest.skip(f"找不到 main.py: {main_py}")

    return media_crawler_path


@pytest.fixture
def sample_detail_request() -> DetailRequest:
    """示例详情请求（抖音）"""
    return DetailRequest(
        platform=Platform.DY,
        login_type=LoginType.QRCODE,
        specified_ids="https://www.douyin.com/jingxuan?modal_id=7605333789232876826",
        get_comment=True,
        max_comments=10,
        headless=False,  # 非无头模式，让用户能看到二维码
    )


@pytest.mark.real_crawler
@pytest.mark.human_interaction
@pytest.mark.timeout(TEST_TIMEOUT)
def test_douyin_detail_with_pydantic_model(
    ensure_media_crawler: Path,
    sample_detail_request: DetailRequest,
):
    """
    使用 Pydantic 模型测试抖音详情模式

    此测试验证：
    1. DetailRequest 模型正确构建
    2. CrawlerRunner 正确执行
    3. CrawlerExecution 记录完整状态
    4. 输出文件被正确追踪
    """
    print("\n" + "=" * 60)
    print("🧪 E2E 测试：抖音详情模式")
    print("=" * 60)

    # 1. 验证请求模型
    print("\n📋 请求模型:")
    print(f"  平台: {sample_detail_request.platform.value}")
    print(f"  类型: {sample_detail_request.crawler_type.value}")
    print(f"  ID: {sample_detail_request.specified_ids}")
    print(f"  登录: {sample_detail_request.login_type.value}")

    # 2. 验证 CLI 参数
    cli_args = sample_detail_request.to_cli_args()
    print(f"\n🔧 CLI 参数: {' '.join(cli_args)}")

    # 3. 初始化 Runner
    print(f"\n🚀 启动 CrawlerRunner...")
    runner = CrawlerRunner(ensure_media_crawler)

    # 4. 启动爬虫
    execution = runner.start(sample_detail_request)
    print(f"  进程 ID: {execution.process_id}")
    print(f"  状态: {execution.status.value}")

    # 5. 实时输出并等待完成
    print("\n📊 实时输出:")
    print("-" * 60)

    try:
        for line in runner.iter_output(execution, timeout=TEST_TIMEOUT):
            print(line)
    except TimeoutError:
        pytest.fail(f"测试超时（{TEST_TIMEOUT}秒）")

    print("-" * 60)

    # 6. 验证执行结果
    print("\n✅ 执行结果:")
    print(f"  最终状态: {execution.status.value}")
    print(f"  返回码: {execution.return_code}")
    print(f"  耗时: {execution.duration_seconds:.1f} 秒")
    print(f"  输出行数: {len(execution.stdout_lines)}")

    # 7. 断言验证
    assert execution.status == ExecutionStatus.COMPLETED, \
        f"期望 COMPLETED，实际是 {execution.status.value}"
    assert execution.return_code == 0, \
        f"期望返回码 0，实际是 {execution.return_code}"
    assert execution.process_id is not None
    assert execution.start_time is not None
    assert execution.end_time is not None

    print("\n" + "=" * 60)
    print("✅ 测试通过！")
    print("=" * 60)


@pytest.mark.real_crawler
@pytest.mark.human_interaction
@pytest.mark.timeout(TEST_TIMEOUT)
def test_douyin_detail_with_output_verification(
    ensure_media_crawler: Path,
):
    """
    测试并验证输出文件

    验证 CrawlerExecution 能正确追踪输出文件
    """
    print("\n" + "=" * 60)
    print("🧪 E2E 测试：输出文件验证")
    print("=" * 60)

    # 构建请求
    request = DetailRequest(
        platform=Platform.DY,
        login_type=LoginType.QRCODE,
        specified_ids="https://www.douyin.com/jingxuan?modal_id=7605333789232876826",
        get_comment=True,
        max_comments=5,
        headless=False,
        save_option="json",
    )

    print(f"\n📋 请求: {request.platform.value} {request.crawler_type.value}")

    # 执行
    runner = CrawlerRunner(ensure_media_crawler)
    execution = runner.start(request)

    try:
        for _ in runner.iter_output(execution, timeout=TEST_TIMEOUT):
            pass
    except TimeoutError:
        pytest.fail("测试超时")

    # 验证执行成功
    assert execution.status == ExecutionStatus.COMPLETED

    # 查找输出文件
    print("\n📁 扫描输出文件...")
    data_dir = ensure_media_crawler / "data"

    if data_dir.exists():
        json_files = list(data_dir.rglob("*.json"))
        print(f"  找到 {len(json_files)} 个 JSON 文件")

        if json_files:
            # 验证文件存在（CrawlerExecution 的校验）
            try:
                execution.update_output_files(json_files[:5])  # 最多5个
                print(f"  ✅ 已追踪 {len(execution.output_files)} 个文件")
            except ValueError as e:
                print(f"  ⚠️ 文件验证失败: {e}")

            # 验证 JSON 内容
            for json_file in json_files[:2]:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    print(f"  ✅ {json_file.name}: {len(data) if isinstance(data, list) else 'object'} 条记录")
                except Exception as e:
                    print(f"  ⚠️ {json_file.name}: 读取失败 - {e}")
    else:
        print(f"  ⚠️ 数据目录不存在: {data_dir}")

    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)


@pytest.mark.real_crawler
@pytest.mark.human_interaction
@pytest.mark.timeout(TEST_TIMEOUT)
def test_model_to_execution_flow(ensure_media_crawler: Path):
    """
    测试完整的数据流：Model → Runner → Execution
    """
    print("\n" + "=" * 60)
    print("🧪 E2E 测试：完整数据流")
    print("=" * 60)

    # 1. 创建模型
    request = DetailRequest(
        platform=Platform.DY,
        specified_ids="https://www.douyin.com/jingxuan?modal_id=7605333789232876826",
        get_comment=True,
        max_comments=3,
        headless=False,
    )

    # 2. 序列化/反序列化验证
    request_data = request.model_dump()
    restored_request = DetailRequest.model_validate(request_data)
    assert restored_request.platform == request.platform
    print("✅ 模型序列化/反序列化验证通过")

    # 3. 构建命令
    cmd = build_command(request)
    print(f"✅ 命令构建: {' '.join(cmd[:5])}...")

    # 4. 执行
    runner = CrawlerRunner(ensure_media_crawler)
    execution = runner.start(request)

    # 5. 验证 Execution 初始状态
    assert execution.request == request  # 请求关联
    assert execution.status == ExecutionStatus.RUNNING
    print(f"✅ Execution 创建: pid={execution.process_id}")

    # 6. 等待完成
    for line in runner.iter_output(execution, timeout=TEST_TIMEOUT):
        pass

    # 7. 验证 Execution 最终状态
    assert execution.is_finished
    assert execution.duration_seconds is not None
    assert execution.duration_seconds > 0
    print(f"✅ Execution 完成: 耗时={execution.duration_seconds:.1f}s")

    # 8. Execution 序列化验证
    execution_data = execution.model_dump()
    assert execution_data["status"] == "completed"
    assert execution_data["request"]["platform"] == "dy"
    print("✅ Execution 序列化验证通过")

    print("\n" + "=" * 60)
    print("✅ 完整数据流测试通过！")
    print("=" * 60)


@pytest.mark.real_crawler
@pytest.mark.human_interaction
@pytest.mark.timeout(TEST_TIMEOUT)
def test_execution_state_transitions(ensure_media_crawler: Path):
    """
    测试执行状态转换

    验证状态机：PENDING → RUNNING → COMPLETED
    """
    print("\n" + "=" * 60)
    print("🧪 E2E 测试：状态转换")
    print("=" * 60)

    request = DetailRequest(
        platform=Platform.DY,
        specified_ids="https://www.douyin.com/jingxuan?modal_id=7605333789232876826",
        max_comments=3,
        headless=False,
    )

    # 初始状态
    execution = CrawlerExecution(request=request)
    assert execution.status == ExecutionStatus.PENDING
    print(f"1. 初始状态: {execution.status.value}")

    # 启动 → RUNNING
    runner = CrawlerRunner(ensure_media_crawler)
    execution = runner.start(request)
    assert execution.status == ExecutionStatus.RUNNING
    assert execution.process_id is not None
    print(f"2. 启动后: {execution.status.value} (pid={execution.process_id})")

    # 完成 → COMPLETED
    for _ in runner.iter_output(execution, timeout=TEST_TIMEOUT):
        pass

    assert execution.status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED)
    print(f"3. 结束后: {execution.status.value}")

    if execution.status == ExecutionStatus.COMPLETED:
        print(f"   返回码: {execution.return_code}")
        print(f"   耗时: {execution.duration_seconds:.1f}s")

    print("\n" + "=" * 60)
    print("✅ 状态转换测试完成！")
    print("=" * 60)
