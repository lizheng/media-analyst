"""
参数构建模块

纯函数：将 CrawlerRequest 转换为 MediaCrawler 命令行参数
"""

from typing import List

from media_analyst.core.models import CrawlerRequest


def build_args(request: CrawlerRequest) -> List[str]:
    """
    将爬虫请求模型转换为命令行参数列表

    这是一个纯函数：相同的输入总是产生相同的输出，无副作用

    Args:
        request: 爬虫请求模型（SearchRequest/DetailRequest/CreatorRequest）

    Returns:
        命令行参数列表，可直接传递给 subprocess

    Examples:
        >>> req = SearchRequest(platform=Platform.DY, keywords="美食")
        >>> build_args(req)
        ['--platform', 'dy', '--lt', 'qrcode', '--start', '1', ...]
    """
    return request.to_cli_args()


def build_command(request: CrawlerRequest, use_uv: bool = True) -> List[str]:
    """
    构建完整命令（包含 uv run main.py 前缀）

    Args:
        request: 爬虫请求模型
        use_uv: 是否使用 uv run 前缀

    Returns:
        完整命令列表
    """
    args = build_args(request)
    if use_uv:
        return ['uv', 'run', 'main.py'] + args
    return ['python', 'main.py'] + args


def preview_command(request: CrawlerRequest, media_crawler_path: str = '../MediaCrawler') -> str:
    """
    生成命令预览字符串（用于 UI 显示）

    Args:
        request: 爬虫请求模型
        media_crawler_path: MediaCrawler 项目路径

    Returns:
        可读的命令字符串
    """
    cmd = build_command(request)
    cmd_str = ' '.join(cmd)
    return f'cd {media_crawler_path} && {cmd_str}'
