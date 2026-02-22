"""
Params 模块单元测试

测试参数构建纯函数：
- build_args
- build_command
- preview_command

使用函数形式编写测试
"""

from media_analyst.core.models import (
    CreatorRequest,
    DetailRequest,
    LoginType,
    Platform,
    SaveOption,
    SearchRequest,
)
from media_analyst.core.params import build_args, build_command, preview_command

# ============================================================================
# build_args Tests
# ============================================================================


def test_build_args_with_search_request():
    """测试搜索请求参数构建"""
    req = SearchRequest(
        platform=Platform.DY,
        login_type=LoginType.QRCODE,
        keywords='美食,旅游',
        start_page=1,
        get_comment=True,
        save_option=SaveOption.JSON,
        max_comments=50,
    )

    args = build_args(req)

    # 验证必要参数
    assert '--platform' in args
    assert args[args.index('--platform') + 1] == 'dy'
    assert '--lt' in args
    assert args[args.index('--lt') + 1] == 'qrcode'
    assert '--type' in args
    assert args[args.index('--type') + 1] == 'search'
    assert '--keywords' in args
    assert args[args.index('--keywords') + 1] == '美食,旅游'
    assert '--get_comment' in args
    assert args[args.index('--get_comment') + 1] == 'yes'
    assert '--max_comments_count_singlenotes' in args
    assert args[args.index('--max_comments_count_singlenotes') + 1] == '50'


def test_build_args_with_detail_request():
    """测试详情请求参数构建"""
    req = DetailRequest(
        platform=Platform.XHS,
        specified_ids='https://xiaohongshu.com/note/123',
        get_comment=False,
        headless=False,
        max_comments=100,
    )

    args = build_args(req)

    assert '--type' in args
    assert args[args.index('--type') + 1] == 'detail'
    assert '--specified_id' in args
    assert args[args.index('--specified_id') + 1] == 'https://xiaohongshu.com/note/123'
    assert '--get_comment' in args
    assert args[args.index('--get_comment') + 1] == 'no'
    assert '--headless' in args
    assert args[args.index('--headless') + 1] == 'no'


def test_build_args_with_creator_request():
    """测试创作者请求参数构建"""
    req = CreatorRequest(
        platform=Platform.KS,
        creator_ids='user1,user2',
        start_page=2,
        get_sub_comment=True,
    )

    args = build_args(req)

    assert '--type' in args
    assert args[args.index('--type') + 1] == 'creator'
    assert '--creator_id' in args
    assert args[args.index('--creator_id') + 1] == 'user1,user2'
    assert '--start' in args
    assert args[args.index('--start') + 1] == '2'
    assert '--get_sub_comment' in args
    assert args[args.index('--get_sub_comment') + 1] == 'yes'


def test_build_args_with_custom_save_path():
    """测试自定义保存路径"""
    req = SearchRequest(
        platform=Platform.DY,
        keywords='测试',
        save_path='/custom/path',
    )

    args = build_args(req)

    assert '--save_data_path' in args
    assert args[args.index('--save_data_path') + 1] == '/custom/path'


def test_build_args_without_save_path():
    """测试无保存路径时不添加参数"""
    req = SearchRequest(
        platform=Platform.DY,
        keywords='测试',
        save_path=None,
    )

    args = build_args(req)

    assert '--save_data_path' not in args


def test_build_args_all_boolean_flags():
    """测试所有布尔标志"""
    req_true = SearchRequest(
        platform=Platform.DY,
        keywords='测试',
        get_comment=True,
        get_sub_comment=True,
        headless=True,
    )
    req_false = SearchRequest(
        platform=Platform.DY,
        keywords='测试',
        get_comment=False,
        get_sub_comment=False,
        headless=False,
    )

    args_true = build_args(req_true)
    args_false = build_args(req_false)

    # 验证 true 值
    assert args_true[args_true.index('--get_comment') + 1] == 'yes'
    assert args_true[args_true.index('--get_sub_comment') + 1] == 'yes'
    assert args_true[args_true.index('--headless') + 1] == 'yes'

    # 验证 false 值
    assert args_false[args_false.index('--get_comment') + 1] == 'no'
    assert args_false[args_false.index('--get_sub_comment') + 1] == 'no'
    assert args_false[args_false.index('--headless') + 1] == 'no'


# ============================================================================
# build_command Tests
# ============================================================================


def test_build_command_with_uv():
    """测试使用 uv 前缀"""
    req = SearchRequest(
        platform=Platform.DY,
        keywords='测试',
    )

    cmd = build_command(req, use_uv=True)

    assert cmd[0] == 'uv'
    assert cmd[1] == 'run'
    assert cmd[2] == 'main.py'
    assert '--platform' in cmd


def test_build_command_without_uv():
    """测试不使用 uv 前缀"""
    req = SearchRequest(
        platform=Platform.DY,
        keywords='测试',
    )

    cmd = build_command(req, use_uv=False)

    assert cmd[0] == 'python'
    assert cmd[1] == 'main.py'
    assert '--platform' in cmd


# ============================================================================
# preview_command Tests
# ============================================================================


def test_preview_command_format():
    """测试命令预览格式"""
    req = SearchRequest(
        platform=Platform.DY,
        keywords='美食',
    )

    preview = preview_command(req, media_crawler_path='../MediaCrawler')

    assert preview.startswith('cd ../MediaCrawler &&')
    assert 'uv run main.py' in preview
    assert '--platform dy' in preview
    assert '--keywords 美食' in preview


def test_preview_command_with_different_path():
    """测试不同路径"""
    req = SearchRequest(
        platform=Platform.XHS,
        keywords='穿搭',
    )

    preview = preview_command(req, media_crawler_path='/opt/MediaCrawler')

    assert 'cd /opt/MediaCrawler' in preview


# ============================================================================
# Idempotency Tests
# ============================================================================


def test_build_args_is_pure():
    """build_args 是纯函数：相同输入产生相同输出"""
    req = SearchRequest(
        platform=Platform.DY,
        keywords='测试',
        max_comments=50,
    )

    args1 = build_args(req)
    args2 = build_args(req)

    assert args1 == args2
    # 原始请求未被修改
    assert req.keywords == '测试'
    assert req.max_comments == 50
