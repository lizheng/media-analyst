"""
UI选项持久化模块

使用本地JSON文件保存用户偏好设置，实现跨会话的选项记忆功能。
"""

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

import streamlit as st

# 配置文件路径
CONFIG_DIR = Path.home() / ".media_analyst"
PREFS_FILE = CONFIG_DIR / "preferences.json"


@dataclass
class UserPreferences:
    """用户偏好设置"""

    platform: str = "dy"  # 默认抖音
    login_type: str = "qrcode"  # 默认扫码登录
    crawler_type: str = "search"  # 默认搜索模式
    save_option: str = "csv"  # 默认CSV格式
    save_path: str = ""  # 保存路径
    max_comments: int = 100  # 默认100条评论
    get_comment: bool = False  # 默认不获取评论
    get_sub_comment: bool = False  # 默认不获取子评论
    headless: bool = True  # 默认无头模式

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "UserPreferences":
        # 只保留有效的字段
        valid_fields = {k: v for k, v in data.items() if k in cls.__dataclass_fields__}
        return cls(**valid_fields)


def _ensure_config_dir() -> None:
    """确保配置目录存在"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_preferences() -> UserPreferences:
    """
    从本地JSON文件加载用户偏好

    Returns:
        UserPreferences对象，如果文件不存在则返回默认值
    """
    # 首先检查session_state（当前会话已加载）
    if "_user_preferences" in st.session_state:
        return UserPreferences.from_dict(st.session_state._user_preferences)

    # 从文件加载
    if PREFS_FILE.exists():
        try:
            with open(PREFS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            prefs = UserPreferences.from_dict(data)
            st.session_state._user_preferences = prefs.to_dict()
            return prefs
        except (json.JSONDecodeError, IOError, TypeError):
            # 文件损坏或读取失败，使用默认值
            pass

    # 返回默认偏好
    default_prefs = UserPreferences()
    st.session_state._user_preferences = default_prefs.to_dict()
    return default_prefs


def save_preferences(preferences: UserPreferences) -> None:
    """
    保存用户偏好到本地JSON文件

    Args:
        preferences: 用户偏好设置对象
    """
    prefs_dict = preferences.to_dict()

    # 更新session_state
    st.session_state._user_preferences = prefs_dict

    # 保存到文件
    try:
        _ensure_config_dir()
        with open(PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs_dict, f, ensure_ascii=False, indent=2)
    except IOError as e:
        # 保存失败时记录错误但不中断流程
        st.warning(f"⚠️ 无法保存偏好设置: {e}")


def save_from_form_values(
    platform: str,
    login_type: str,
    crawler_type: str,
    save_option: str,
    max_comments: int,
    get_comment: bool,
    get_sub_comment: bool,
    headless: bool,
    save_path: str = "",
) -> None:
    """
    从表单值创建并保存偏好

    Args:
        platform: 平台代码
        login_type: 登录方式代码
        crawler_type: 爬虫类型代码
        save_option: 保存选项
        max_comments: 最大评论数
        get_comment: 是否获取评论
        get_sub_comment: 是否获取子评论
        headless: 是否无头模式
        save_path: 保存路径（可选）
    """
    preferences = UserPreferences(
        platform=platform,
        login_type=login_type,
        crawler_type=crawler_type,
        save_option=save_option,
        save_path=save_path,
        max_comments=max_comments,
        get_comment=get_comment,
        get_sub_comment=get_sub_comment,
        headless=headless,
    )
    save_preferences(preferences)


def get_preference(
    key: str,
    default: Any = None,
    prefs: UserPreferences | None = None,
) -> Any:
    """
    获取单个偏好值

    Args:
        key: 偏好键名
        default: 默认值
        prefs: 偏好对象（如果为None则从session_state加载）

    Returns:
        偏好值或默认值
    """
    if prefs is None:
        prefs = load_preferences()
    return getattr(prefs, key, default)


def clear_preferences() -> None:
    """清除所有保存的偏好设置"""
    # 清除session_state
    keys_to_clear = ["_user_preferences"]
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    # 删除文件
    if PREFS_FILE.exists():
        try:
            PREFS_FILE.unlink()
        except IOError:
            pass


def get_prefs_file_path() -> Path:
    """获取偏好文件路径（用于显示）"""
    return PREFS_FILE
