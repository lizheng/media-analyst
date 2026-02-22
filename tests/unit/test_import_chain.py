"""
导入链路测试

验证从 core → ui 的完整导入链路
"""

import pytest


class TestImportChain:
    """测试各级导入链路"""

    def test_import_from_url_parser_directly(self):
        """直接导入 url_parser 模块"""
        from media_analyst.core.url_parser import (
            ParsedLink,
            URLParseError,
            extract_urls_from_text,
            parse_douyin_url,
            extract_douyin_links,
            normalize_douyin_links,
            format_link_for_display,
        )
        assert callable(extract_urls_from_text)
        assert callable(extract_douyin_links)

    def test_import_from_core_init(self):
        """从 core.__init__ 导入"""
        from media_analyst.core import (
            ParsedLink,
            URLParseError,
            extract_urls_from_text,
            parse_douyin_url,
            extract_douyin_links,
            normalize_douyin_links,
            format_link_for_display,
        )
        assert callable(extract_douyin_links)

    def test_import_format_link_for_display_from_core(self):
        """测试 format_link_for_display 是否能从core导入"""
        from media_analyst.core import format_link_for_display
        assert callable(format_link_for_display)

    def test_import_in_app_context(self):
        """模拟 app.py 中的导入方式"""
        # 这是 app.py 中的实际导入语句
        from media_analyst.core import (
            extract_douyin_links,
            format_link_for_display,
        )
        assert callable(extract_douyin_links)
        assert callable(format_link_for_display)

    def test_import_all_exports(self):
        """测试 __all__ 中导出的所有名称"""
        import media_analyst.core as core

        # 检查 url_parser 相关导出
        assert hasattr(core, 'ParsedLink')
        assert hasattr(core, 'URLParseError')
        assert hasattr(core, 'extract_urls_from_text')
        assert hasattr(core, 'parse_douyin_url')
        assert hasattr(core, 'extract_douyin_links')
        assert hasattr(core, 'normalize_douyin_links')
        assert hasattr(core, 'format_link_for_display')

    def test_parsed_link_dataclass(self):
        """测试 ParsedLink 数据类可用"""
        from media_analyst.core import ParsedLink

        link = ParsedLink(
            original="https://v.douyin.com/abc/",
            normalized="https://www.douyin.com/video/123",
            video_id="123",
            link_type="short"
        )
        assert link.video_id == "123"
        assert link.link_type == "short"
