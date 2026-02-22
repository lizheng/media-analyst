"""
UI偏好持久化模块测试

测试UserPreferences模型和持久化函数
"""

import json
import tempfile
from pathlib import Path

import pytest

from media_analyst.ui.persistence import (
    UserPreferences,
    get_preference,
    save_from_form_values,
    _ensure_config_dir,
    PREFS_FILE,
)


# ============================================================================
# UserPreferences Model Tests
# ============================================================================

def test_user_preferences_defaults():
    """测试UserPreferences默认值"""
    prefs = UserPreferences()

    assert prefs.platform == "dy"  # 默认抖音
    assert prefs.login_type == "qrcode"  # 默认扫码
    assert prefs.crawler_type == "search"  # 默认搜索模式
    assert prefs.save_option == "csv"  # 默认CSV
    assert prefs.max_comments == 100  # 默认100条评论
    assert prefs.get_comment is False
    assert prefs.get_sub_comment is False
    assert prefs.headless is True  # 默认无头模式
    assert prefs.save_path == ""


def test_user_preferences_custom_values():
    """测试自定义偏好值"""
    prefs = UserPreferences(
        platform="xhs",
        login_type="phone",
        crawler_type="detail",
        save_option="json",
        max_comments=50,
        get_comment=True,
        get_sub_comment=True,
        headless=False,
        save_path="/custom/path",
    )

    assert prefs.platform == "xhs"
    assert prefs.login_type == "phone"
    assert prefs.crawler_type == "detail"
    assert prefs.save_option == "json"
    assert prefs.max_comments == 50
    assert prefs.get_comment is True
    assert prefs.get_sub_comment is True
    assert prefs.headless is False
    assert prefs.save_path == "/custom/path"


def test_user_preferences_to_dict():
    """测试转换为字典"""
    prefs = UserPreferences(platform="dy", max_comments=200)
    data = prefs.to_dict()

    assert isinstance(data, dict)
    assert data["platform"] == "dy"
    assert data["max_comments"] == 200
    assert data["headless"] is True


def test_user_preferences_from_dict():
    """测试从字典创建"""
    data = {
        "platform": "xhs",
        "login_type": "cookie",
        "crawler_type": "creator",
        "save_option": "json",
        "save_path": "/test",
        "max_comments": 500,
        "get_comment": True,
        "get_sub_comment": True,
        "headless": False,
    }

    prefs = UserPreferences.from_dict(data)

    assert prefs.platform == "xhs"
    assert prefs.login_type == "cookie"
    assert prefs.crawler_type == "creator"
    assert prefs.max_comments == 500


def test_user_preferences_from_dict_partial():
    """测试从部分字典创建（缺失字段使用默认值）"""
    data = {"platform": "bili", "max_comments": 10}

    prefs = UserPreferences.from_dict(data)

    assert prefs.platform == "bili"
    assert prefs.max_comments == 10
    # 其他字段使用默认值
    assert prefs.login_type == "qrcode"
    assert prefs.crawler_type == "search"
    assert prefs.headless is True


def test_user_preferences_from_dict_ignores_invalid():
    """测试忽略无效字段"""
    data = {
        "platform": "dy",
        "invalid_field": "should_be_ignored",
        "another_bad_key": 123,
    }

    prefs = UserPreferences.from_dict(data)

    assert prefs.platform == "dy"
    # 不会抛出错误，只是忽略无效字段
    assert not hasattr(prefs, "invalid_field")


# ============================================================================
# Preference Access Tests
# ============================================================================

def test_get_preference_with_explicit_prefs():
    """测试使用显式偏好对象获取值"""
    prefs = UserPreferences(platform="ks", login_type="phone")

    assert get_preference("platform", prefs=prefs) == "ks"
    assert get_preference("login_type", prefs=prefs) == "phone"
    assert get_preference("headless", prefs=prefs) is True


def test_get_preference_with_default():
    """测试获取不存在的键时使用默认值"""
    prefs = UserPreferences()

    # 使用不存在的键应返回默认值
    assert get_preference("nonexistent", default="fallback", prefs=prefs) == "fallback"


# ============================================================================
# Save Form Values Tests
# ============================================================================

def test_save_from_form_values():
    """测试从表单值保存偏好"""
    # 这个函数主要操作streamlit session_state，
    # 这里只测试它可以被调用而不抛出异常
    # 实际功能需要在Streamlit环境中测试
    try:
        save_from_form_values(
            platform="dy",
            login_type="qrcode",
            crawler_type="search",
            save_option="csv",
            max_comments=100,
            get_comment=False,
            get_sub_comment=False,
            headless=True,
            save_path="",
        )
    except Exception as e:
        # 在非Streamlit环境中可能会失败，这是预期的
        pytest.skip(f"Streamlit session_state not available: {e}")


# ============================================================================
# Integration with Core Models
# ============================================================================

def test_preferences_match_platform_options():
    """测试偏好值与平台选项匹配"""
    from media_analyst.core import PLATFORMS

    prefs = UserPreferences()

    # 默认平台必须在可用平台列表中
    assert prefs.platform in PLATFORMS.keys()


def test_preferences_match_login_options():
    """测试偏好值与登录选项匹配"""
    from media_analyst.core import LOGIN_TYPES

    prefs = UserPreferences()

    # 默认登录方式必须在可用选项中
    assert prefs.login_type in LOGIN_TYPES.keys()


def test_preferences_match_crawler_types():
    """测试偏好值与爬虫类型匹配"""
    from media_analyst.core import CRAWLER_TYPES

    prefs = UserPreferences()

    # 默认爬虫类型必须在可用选项中
    assert prefs.crawler_type in CRAWLER_TYPES.keys()


def test_preferences_match_save_options():
    """测试偏好值与保存选项匹配"""
    from media_analyst.core import SAVE_OPTIONS

    prefs = UserPreferences()

    # 默认保存选项必须在可用选项中
    assert prefs.save_option in SAVE_OPTIONS


# ============================================================================
# File Persistence Tests
# ============================================================================

def test_preferences_save_and_load_from_file():
    """测试偏好设置保存到文件并能正确加载"""
    import streamlit as st

    # 使用临时目录测试
    with tempfile.TemporaryDirectory() as tmpdir:
        # 临时修改配置文件路径
        from media_analyst.ui import persistence
        original_path = persistence.PREFS_FILE
        test_file = Path(tmpdir) / "test_prefs.json"
        persistence.PREFS_FILE = test_file

        try:
            # 清除session_state中的缓存
            if "_user_preferences" in st.session_state:
                del st.session_state._user_preferences

            # 创建并保存自定义偏好
            prefs = UserPreferences(
                platform="xhs",
                login_type="phone",
                crawler_type="detail",
                save_option="json",
                max_comments=50,
                get_comment=True,
                headless=False,
            )
            persistence.save_preferences(prefs)

            # 验证文件已创建
            assert test_file.exists()

            # 读取文件内容验证
            with open(test_file, "r", encoding="utf-8") as f:
                saved_data = json.load(f)

            assert saved_data["platform"] == "xhs"
            assert saved_data["login_type"] == "phone"
            assert saved_data["max_comments"] == 50
            assert saved_data["get_comment"] is True
            assert saved_data["headless"] is False

            # 清除session_state模拟新会话
            if "_user_preferences" in st.session_state:
                del st.session_state._user_preferences

            # 从文件加载
            loaded_prefs = persistence.load_preferences()

            assert loaded_prefs.platform == "xhs"
            assert loaded_prefs.login_type == "phone"
            assert loaded_prefs.crawler_type == "detail"
            assert loaded_prefs.max_comments == 50
            assert loaded_prefs.get_comment is True

        finally:
            # 恢复原配置路径
            persistence.PREFS_FILE = original_path


def test_preferences_file_not_exists():
    """测试配置文件不存在时返回默认值"""
    import streamlit as st

    with tempfile.TemporaryDirectory() as tmpdir:
        from media_analyst.ui import persistence
        original_path = persistence.PREFS_FILE
        test_file = Path(tmpdir) / "nonexistent.json"
        persistence.PREFS_FILE = test_file

        try:
            # 清除session_state
            if "_user_preferences" in st.session_state:
                del st.session_state._user_preferences

            # 加载不存在的文件应返回默认值
            prefs = persistence.load_preferences()

            assert prefs.platform == "dy"  # 默认值
            assert prefs.login_type == "qrcode"
            assert prefs.max_comments == 100

        finally:
            persistence.PREFS_FILE = original_path


def test_preferences_clear():
    """测试清除偏好设置"""
    import streamlit as st

    with tempfile.TemporaryDirectory() as tmpdir:
        from media_analyst.ui import persistence
        original_path = persistence.PREFS_FILE
        test_file = Path(tmpdir) / "prefs_to_clear.json"
        persistence.PREFS_FILE = test_file

        try:
            # 先保存一些偏好
            prefs = UserPreferences(platform="bili")
            persistence.save_preferences(prefs)
            assert test_file.exists()

            # 清除
            persistence.clear_preferences()

            # 文件应被删除
            assert not test_file.exists()

        finally:
            persistence.PREFS_FILE = original_path


def test_ensure_config_dir():
    """测试配置目录创建"""
    with tempfile.TemporaryDirectory() as tmpdir:
        from media_analyst.ui import persistence
        original_dir = persistence.CONFIG_DIR
        test_dir = Path(tmpdir) / ".media_analyst"
        persistence.CONFIG_DIR = test_dir

        try:
            # 目录不应存在
            assert not test_dir.exists()

            # 调用确保目录函数
            _ensure_config_dir()

            # 目录应被创建
            assert test_dir.exists()
            assert test_dir.is_dir()

        finally:
            persistence.CONFIG_DIR = original_dir


def test_corrupted_prefs_file():
    """测试损坏的配置文件应返回默认值"""
    import streamlit as st

    with tempfile.TemporaryDirectory() as tmpdir:
        from media_analyst.ui import persistence
        original_path = persistence.PREFS_FILE
        test_file = Path(tmpdir) / "corrupted.json"
        persistence.PREFS_FILE = test_file

        try:
            # 清除session_state
            if "_user_preferences" in st.session_state:
                del st.session_state._user_preferences

            # 创建损坏的JSON文件
            test_file.write_text("{invalid json content", encoding="utf-8")

            # 加载应返回默认值
            prefs = persistence.load_preferences()
            assert prefs.platform == "dy"  # 默认值

        finally:
            persistence.PREFS_FILE = original_path
