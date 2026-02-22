"""
Pydantic 数据模型

设计原则：让不合法状态无法表示（Making Illegal States Unrepresentable）
- 不同爬虫类型使用不同模型，强制要求必填字段
- CrawlerExecution 创建时自动校验输出文件存在性
"""

from abc import abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class Platform(str, Enum):
    """支持的平台"""
    XHS = "xhs"
    DY = "dy"
    KS = "ks"
    BILI = "bili"
    WB = "wb"
    TIEBA = "tieba"
    ZHIHU = "zhihu"


class LoginType(str, Enum):
    """登录方式"""
    QRCODE = "qrcode"
    PHONE = "phone"
    COOKIE = "cookie"


class CrawlerType(str, Enum):
    """爬虫类型"""
    SEARCH = "search"
    DETAIL = "detail"
    CREATOR = "creator"


class SaveOption(str, Enum):
    """保存格式选项"""
    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    SQLITE = "sqlite"
    DB = "db"
    MONGODB = "mongodb"
    POSTGRES = "postgres"


class ExecutionStatus(str, Enum):
    """执行状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    STOPPED = "stopped"


class CommonRequestFields(BaseModel):
    """通用请求字段（抽象基类）"""
    model_config = {"frozen": True}  # 不可变对象，函数式风格

    platform: Platform = Field(..., description="目标平台")
    login_type: LoginType = Field(default=LoginType.QRCODE, description="登录方式")
    get_comment: bool = Field(default=False, description="是否获取评论")
    get_sub_comment: bool = Field(default=False, description="是否获取子评论")
    headless: bool = Field(default=True, description="是否使用无头模式")
    save_option: SaveOption = Field(default=SaveOption.JSON, description="保存格式")
    max_comments: int = Field(default=100, ge=0, le=10000, description="单篇最大评论数")
    save_path: Optional[str] = Field(default=None, description="自定义保存路径")

    @abstractmethod
    def to_cli_args(self) -> List[str]:
        """转换为命令行参数列表（纯函数）"""
        raise NotImplementedError

    def _build_common_args(self) -> List[str]:
        """构建通用参数"""
        args = [
            "--platform", self.platform.value,
            "--lt", self.login_type.value,
            "--start", "1",  # 起始页码默认为1，子类可覆盖
            "--save_data_option", self.save_option.value,
            "--max_comments_count_singlenotes", str(self.max_comments),
            "--get_comment", "yes" if self.get_comment else "no",
            "--get_sub_comment", "yes" if self.get_sub_comment else "no",
            "--headless", "yes" if self.headless else "no",
        ]
        if self.save_path:
            args.extend(["--save_data_path", self.save_path])
        return args


class SearchRequest(CommonRequestFields):
    """
    搜索模式请求

    强制要求：
    - keywords: 搜索关键词（必填，且不能为empty）
    - crawler_type: Literal["search"]
    """
    crawler_type: Literal[CrawlerType.SEARCH] = CrawlerType.SEARCH
    keywords: str = Field(..., description="搜索关键词，多个用逗号分隔")
    start_page: int = Field(default=1, ge=1, description="起始页码")

    @field_validator("keywords")
    @classmethod
    def validate_keywords(cls, v: str) -> str:
        """验证关键词不为空字符串（包括纯空白）"""
        if not v or not v.strip():
            raise ValueError("搜索关键词不能为空")
        return v.strip()

    def to_cli_args(self) -> List[str]:
        """转换为命令行参数"""
        args = self._build_common_args()
        # 覆盖起始页码
        args = [arg if arg != "1" or args[i-1] != "--start" else str(self.start_page)
                for i, arg in enumerate(args)]
        args[args.index("--start") + 1] = str(self.start_page)
        args.extend(["--type", "search", "--keywords", self.keywords])
        return args


class DetailRequest(CommonRequestFields):
    """
    详情模式请求

    强制要求：
    - specified_ids: 笔记/视频 URL 或 ID（必填，且不能为empty）
    - crawler_type: Literal["detail"]
    """
    crawler_type: Literal[CrawlerType.DETAIL] = CrawlerType.DETAIL
    specified_ids: str = Field(..., description="笔记/视频 URL 或 ID，多个用逗号分隔")
    start_page: int = Field(default=1, ge=1, description="起始页码")

    @field_validator("specified_ids")
    @classmethod
    def validate_specified_ids(cls, v: str) -> str:
        """验证 ID 不为空字符串（包括纯空白）"""
        if not v or not v.strip():
            raise ValueError("笔记/视频 ID 不能为空")
        return v.strip()

    def to_cli_args(self) -> List[str]:
        """转换为命令行参数"""
        args = self._build_common_args()
        args[args.index("--start") + 1] = str(self.start_page)
        args.extend(["--type", "detail", "--specified_id", self.specified_ids])
        return args


class CreatorRequest(CommonRequestFields):
    """
    创作者模式请求

    强制要求：
    - creator_ids: 创作者主页 URL 或 ID（必填，且不能为empty）
    - crawler_type: Literal["creator"]
    """
    crawler_type: Literal[CrawlerType.CREATOR] = CrawlerType.CREATOR
    creator_ids: str = Field(..., description="创作者主页 URL 或 ID，多个用逗号分隔")
    start_page: int = Field(default=1, ge=1, description="起始页码")

    @field_validator("creator_ids")
    @classmethod
    def validate_creator_ids(cls, v: str) -> str:
        """验证 ID 不为空字符串（包括纯空白）"""
        if not v or not v.strip():
            raise ValueError("创作者 ID 不能为空")
        return v.strip()

    def to_cli_args(self) -> List[str]:
        """转换为命令行参数"""
        args = self._build_common_args()
        args[args.index("--start") + 1] = str(self.start_page)
        args.extend(["--type", "creator", "--creator_id", self.creator_ids])
        return args


# 联合类型：任意类型的爬虫请求
CrawlerRequest = Union[SearchRequest, DetailRequest, CreatorRequest]


class CrawlerExecution(BaseModel):
    """
    爬虫执行状态和结果

    创建时自动校验：
    - output_files 必须指向存在的文件
    - 状态与返回码的一致性
    """
    model_config = {"frozen": False}  # 执行状态是可变的

    # 关联的请求（创建后不可变）
    request: CrawlerRequest = Field(..., description="关联的爬虫请求")

    # 进程信息
    process_id: Optional[int] = Field(default=None, description="操作系统进程ID")

    # 状态
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description="执行状态")
    start_time: Optional[datetime] = Field(default=None, description="开始时间")
    end_time: Optional[datetime] = Field(default=None, description="结束时间")

    # 输出
    stdout_lines: List[str] = Field(default_factory=list, description="标准输出行")
    stderr_lines: List[str] = Field(default_factory=list, description="标准错误行")
    return_code: Optional[int] = Field(default=None, description="进程返回码")

    # 错误信息
    error_message: Optional[str] = Field(default=None, description="错误信息")

    # 输出文件路径（创建时自动校验存在性）
    output_files: List[Path] = Field(default_factory=list, description="生成的输出文件路径")

    @model_validator(mode="after")
    def validate_output_files_exist(self) -> "CrawlerExecution":
        """
        验证 output_files 指向的文件都存在

        注意：这会在模型创建/更新时执行，确保不合法状态无法表示
        """
        for file_path in self.output_files:
            if not file_path.exists():
                raise ValueError(f"输出文件不存在: {file_path}")
        return self

    @model_validator(mode="after")
    def validate_status_consistency(self) -> "CrawlerExecution":
        """
        验证状态与字段的一致性
        """
        # RUNNING 状态必须有 process_id 和 start_time
        if self.status == ExecutionStatus.RUNNING:
            if self.process_id is None:
                raise ValueError("running 状态必须有 process_id")
            if self.start_time is None:
                raise ValueError("running 状态必须有 start_time")

        # COMPLETED/FAILED/TIMEOUT/STOPPED 状态必须有 end_time
        if self.status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED,
                          ExecutionStatus.TIMEOUT, ExecutionStatus.STOPPED):
            if self.end_time is None:
                raise ValueError(f"{self.status.value} 状态必须有 end_time")

        # FAILED 状态必须有 error_message 或 stderr
        if self.status == ExecutionStatus.FAILED:
            if not self.error_message and not self.stderr_lines:
                raise ValueError("FAILED 状态必须有 error_message 或 stderr_lines")

        return self

    def add_output(self, line: str, is_stderr: bool = False) -> None:
        """添加输出（实时更新）"""
        if is_stderr:
            self.stderr_lines.append(line)
        else:
            self.stdout_lines.append(line)

    def mark_running(self, process_id: int) -> None:
        """标记为运行中"""
        self.status = ExecutionStatus.RUNNING
        self.process_id = process_id
        self.start_time = datetime.now()

    def mark_completed(self, return_code: int = 0) -> None:
        """标记为完成"""
        self.return_code = return_code
        self.end_time = datetime.now()
        if return_code == 0:
            self.status = ExecutionStatus.COMPLETED
        else:
            self.status = ExecutionStatus.FAILED
            self.error_message = f"进程返回码: {return_code}"

    def mark_failed(self, error: str) -> None:
        """标记为失败"""
        self.status = ExecutionStatus.FAILED
        self.error_message = error
        self.end_time = datetime.now()

    def mark_timeout(self) -> None:
        """标记为超时"""
        self.status = ExecutionStatus.TIMEOUT
        self.end_time = datetime.now()

    def mark_stopped(self) -> None:
        """标记为已停止"""
        self.status = ExecutionStatus.STOPPED
        self.end_time = datetime.now()

    def update_output_files(self, files: List[Path]) -> None:
        """
        更新输出文件列表

        会在赋值前验证所有文件存在
        """
        # 先验证所有文件存在
        for f in files:
            if not f.exists():
                raise ValueError(f"输出文件不存在: {f}")
        self.output_files = files

    @property
    def duration_seconds(self) -> Optional[float]:
        """执行时长（秒）"""
        if self.start_time is None:
            return None
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    @property
    def is_finished(self) -> bool:
        """是否已结束"""
        return self.status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT,
            ExecutionStatus.STOPPED,
        )

    @property
    def full_output(self) -> str:
        """完整输出文本"""
        return "\n".join(self.stdout_lines)

    @property
    def full_stderr(self) -> str:
        """完整错误输出文本"""
        return "\n".join(self.stderr_lines)
