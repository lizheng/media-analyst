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

    XHS = 'xhs'
    DY = 'dy'
    KS = 'ks'
    BILI = 'bili'
    WB = 'wb'
    TIEBA = 'tieba'
    ZHIHU = 'zhihu'


class LoginType(str, Enum):
    """登录方式"""

    QRCODE = 'qrcode'
    PHONE = 'phone'
    COOKIE = 'cookie'


class CrawlerType(str, Enum):
    """爬虫类型"""

    SEARCH = 'search'
    DETAIL = 'detail'
    CREATOR = 'creator'


class SaveOption(str, Enum):
    """保存格式选项"""

    JSON = 'json'
    CSV = 'csv'
    EXCEL = 'excel'
    SQLITE = 'sqlite'
    DB = 'db'
    MONGODB = 'mongodb'
    POSTGRES = 'postgres'


class ExecutionStatus(str, Enum):
    """执行状态"""

    PENDING = 'pending'
    RUNNING = 'running'
    COMPLETED = 'completed'
    FAILED = 'failed'
    TIMEOUT = 'timeout'
    STOPPED = 'stopped'


class CommonRequestFields(BaseModel):
    """通用请求字段（抽象基类）"""

    model_config = {'frozen': True}  # 不可变对象，函数式风格

    platform: Platform = Field(..., description='目标平台')
    login_type: LoginType = Field(default=LoginType.QRCODE, description='登录方式')
    get_comment: bool = Field(default=False, description='是否获取评论')
    get_sub_comment: bool = Field(default=False, description='是否获取子评论')
    headless: bool = Field(default=True, description='是否使用无头模式')
    save_option: SaveOption = Field(default=SaveOption.JSON, description='保存格式')
    max_comments: int = Field(default=100, ge=0, le=10000, description='单篇最大评论数')
    save_path: Optional[str] = Field(default=None, description='自定义保存路径')

    @abstractmethod
    def to_cli_args(self) -> List[str]:
        """转换为命令行参数列表（纯函数）"""
        raise NotImplementedError

    def _build_common_args(self) -> List[str]:
        """构建通用参数"""
        args = [
            '--platform',
            self.platform.value,
            '--lt',
            self.login_type.value,
            '--start',
            '1',  # 起始页码默认为1，子类可覆盖
            '--save_data_option',
            self.save_option.value,
            '--max_comments_count_singlenotes',
            str(self.max_comments),
            '--get_comment',
            'yes' if self.get_comment else 'no',
            '--get_sub_comment',
            'yes' if self.get_sub_comment else 'no',
            '--headless',
            'yes' if self.headless else 'no',
        ]
        if self.save_path:
            args.extend(['--save_data_path', self.save_path])
        return args


class SearchRequest(CommonRequestFields):
    """
    搜索模式请求

    强制要求：
    - keywords: 搜索关键词（必填，且不能为empty）
    - crawler_type: Literal["search"]
    """

    crawler_type: Literal[CrawlerType.SEARCH] = CrawlerType.SEARCH
    keywords: str = Field(..., description='搜索关键词，多个用逗号分隔')
    start_page: int = Field(default=1, ge=1, description='起始页码')

    @field_validator('keywords')
    @classmethod
    def validate_keywords(cls, v: str) -> str:
        """验证关键词不为空字符串（包括纯空白）"""
        if not v or not v.strip():
            raise ValueError('搜索关键词不能为空')
        return v.strip()

    def to_cli_args(self) -> List[str]:
        """转换为命令行参数"""
        args = self._build_common_args()
        # 覆盖起始页码
        args = [arg if arg != '1' or args[i - 1] != '--start' else str(self.start_page) for i, arg in enumerate(args)]
        args[args.index('--start') + 1] = str(self.start_page)
        args.extend(['--type', 'search', '--keywords', self.keywords])
        return args


class DetailRequest(CommonRequestFields):
    """
    详情模式请求

    强制要求：
    - specified_ids: 笔记/视频 URL 或 ID（必填，且不能为empty）
    - crawler_type: Literal["detail"]
    """

    crawler_type: Literal[CrawlerType.DETAIL] = CrawlerType.DETAIL
    specified_ids: str = Field(..., description='笔记/视频 URL 或 ID，多个用逗号分隔')
    start_page: int = Field(default=1, ge=1, description='起始页码')

    @field_validator('specified_ids')
    @classmethod
    def validate_specified_ids(cls, v: str) -> str:
        """验证 ID 不为空字符串（包括纯空白）"""
        if not v or not v.strip():
            raise ValueError('笔记/视频 ID 不能为空')
        return v.strip()

    def to_cli_args(self) -> List[str]:
        """转换为命令行参数"""
        args = self._build_common_args()
        args[args.index('--start') + 1] = str(self.start_page)
        args.extend(['--type', 'detail', '--specified_id', self.specified_ids])
        return args


class CreatorRequest(CommonRequestFields):
    """
    创作者模式请求

    强制要求：
    - creator_ids: 创作者主页 URL 或 ID（必填，且不能为empty）
    - crawler_type: Literal["creator"]
    """

    crawler_type: Literal[CrawlerType.CREATOR] = CrawlerType.CREATOR
    creator_ids: str = Field(..., description='创作者主页 URL 或 ID，多个用逗号分隔')
    start_page: int = Field(default=1, ge=1, description='起始页码')

    @field_validator('creator_ids')
    @classmethod
    def validate_creator_ids(cls, v: str) -> str:
        """验证 ID 不为空字符串（包括纯空白）"""
        if not v or not v.strip():
            raise ValueError('创作者 ID 不能为空')
        return v.strip()

    def to_cli_args(self) -> List[str]:
        """转换为命令行参数"""
        args = self._build_common_args()
        args[args.index('--start') + 1] = str(self.start_page)
        args.extend(['--type', 'creator', '--creator_id', self.creator_ids])
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

    model_config = {'frozen': False}  # 执行状态是可变的

    # 关联的请求（创建后不可变）
    request: CrawlerRequest = Field(..., description='关联的爬虫请求')

    # 进程信息
    process_id: Optional[int] = Field(default=None, description='操作系统进程ID')

    # 状态
    status: ExecutionStatus = Field(default=ExecutionStatus.PENDING, description='执行状态')
    start_time: Optional[datetime] = Field(default=None, description='开始时间')
    end_time: Optional[datetime] = Field(default=None, description='结束时间')

    # 输出
    stdout_lines: List[str] = Field(default_factory=list, description='标准输出行')
    stderr_lines: List[str] = Field(default_factory=list, description='标准错误行')
    return_code: Optional[int] = Field(default=None, description='进程返回码')

    # 错误信息
    error_message: Optional[str] = Field(default=None, description='错误信息')

    # 输出文件路径（创建时自动校验存在性）
    output_files: List[Path] = Field(default_factory=list, description='生成的输出文件路径')

    @model_validator(mode='after')
    def validate_output_files_exist(self) -> 'CrawlerExecution':
        """
        验证 output_files 指向的文件都存在

        注意：这会在模型创建/更新时执行，确保不合法状态无法表示
        """
        for file_path in self.output_files:
            if not file_path.exists():
                raise ValueError(f'输出文件不存在: {file_path}')
        return self

    @model_validator(mode='after')
    def validate_status_consistency(self) -> 'CrawlerExecution':
        """
        验证状态与字段的一致性
        """
        # RUNNING 状态必须有 process_id 和 start_time
        if self.status == ExecutionStatus.RUNNING:
            if self.process_id is None:
                raise ValueError('running 状态必须有 process_id')
            if self.start_time is None:
                raise ValueError('running 状态必须有 start_time')

        # COMPLETED/FAILED/TIMEOUT/STOPPED 状态必须有 end_time
        if self.status in (
            ExecutionStatus.COMPLETED,
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT,
            ExecutionStatus.STOPPED,
        ):
            if self.end_time is None:
                raise ValueError(f'{self.status.value} 状态必须有 end_time')

        # FAILED 状态必须有 error_message 或 stderr
        if self.status == ExecutionStatus.FAILED:
            if not self.error_message and not self.stderr_lines:
                raise ValueError('FAILED 状态必须有 error_message 或 stderr_lines')

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
            self.error_message = f'进程返回码: {return_code}'

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
                raise ValueError(f'输出文件不存在: {f}')
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
        return '\n'.join(self.stdout_lines)

    @property
    def full_stderr(self) -> str:
        """完整错误输出文本"""
        return '\n'.join(self.stderr_lines)


# =============================================================================
# 数据解析模型（用于解析抓取结果）
# =============================================================================


class ContentType(str, Enum):
    """内容类型"""

    VIDEO = 'video'  # 视频
    NOTE = 'note'  # 图文/笔记
    ARTICLE = 'article'  # 文章
    UNKNOWN = 'unknown'  # 未知


class Post(BaseModel):
    """
    帖子/视频信息模型（统一各平台格式）

    将不同平台的字段统一为标准格式：
    - 抖音: aweme_id -> content_id
    - 小红书: note_id -> content_id
    - B站: bvid -> content_id
    """

    model_config = {'frozen': True}

    # 核心标识
    content_id: str = Field(..., description='内容ID（平台唯一标识）')
    platform: Platform = Field(..., description='所属平台')
    content_type: ContentType = Field(default=ContentType.UNKNOWN, description='内容类型')

    # 内容信息
    title: str = Field(default='', description='标题')
    desc: str = Field(default='', description='描述/正文')
    content_url: str = Field(default='', description='内容链接')
    cover_url: str = Field(default='', description='封面图片URL')
    media_urls: List[str] = Field(default_factory=list, description='媒体文件URL（视频/图片）')

    # 时间信息
    create_time: Optional[datetime] = Field(default=None, description='发布时间')
    last_modify_ts: Optional[int] = Field(default=None, description='最后修改时间戳')

    # 作者信息
    user_id: str = Field(default='', description='用户ID')
    sec_uid: str = Field(default='', description='安全用户ID（抖音等平台）')
    short_user_id: str = Field(default='', description='短用户ID')
    user_unique_id: str = Field(default='', description='用户唯一标识')
    nickname: str = Field(default='', description='昵称')
    avatar: str = Field(default='', description='头像URL')
    user_signature: str = Field(default='', description='用户简介')

    # 互动数据
    liked_count: int = Field(default=0, description='点赞数')
    collected_count: int = Field(default=0, description='收藏数')
    comment_count: int = Field(default=0, description='评论数')
    share_count: int = Field(default=0, description='分享数')

    # 其他
    ip_location: str = Field(default='', description='IP属地')
    source_keyword: str = Field(default='', description='来源关键词')

    # 元数据
    crawl_time: Optional[datetime] = Field(default=None, description='抓取时间（从文件名提取）')
    source_file: str = Field(default='', description='来源文件路径')

    # 保留原始数据（用于高级查询）
    raw_data: Dict[str, Any] = Field(default_factory=dict, description='原始数据')

    @field_validator('create_time', mode='before')
    @classmethod
    def parse_timestamp(cls, v: Any) -> Optional[datetime]:
        """将 Unix 时间戳转换为 datetime"""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v)
        if isinstance(v, str):
            # 尝试解析数字字符串
            try:
                return datetime.fromtimestamp(int(v))
            except ValueError:
                pass
            # 尝试 ISO 格式
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                return None
        return None

    @field_validator('liked_count', 'collected_count', 'comment_count', 'share_count', mode='before')
    @classmethod
    def parse_count(cls, v: Any) -> int:
        """将字符串数字转换为整数"""
        if v is None:
            return 0
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            try:
                return int(v) if v else 0
            except ValueError:
                return 0
        return 0


class Comment(BaseModel):
    """
    评论信息模型（统一各平台格式）

    支持主评论和子评论（回复）
    """

    model_config = {'frozen': True}

    # 核心标识
    comment_id: str = Field(..., description='评论ID')
    content_id: str = Field(..., description='关联的内容ID')
    platform: Platform = Field(..., description='所属平台')

    # 评论内容
    content: str = Field(default='', description='评论内容')
    pictures: List[str] = Field(default_factory=list, description='评论图片URL')

    # 时间信息
    create_time: Optional[datetime] = Field(default=None, description='评论时间')
    last_modify_ts: Optional[int] = Field(default=None, description='最后修改时间戳')

    # 作者信息
    user_id: str = Field(default='', description='用户ID')
    sec_uid: str = Field(default='', description='安全用户ID')
    short_user_id: str = Field(default='', description='短用户ID')
    user_unique_id: str = Field(default='', description='用户唯一标识')
    nickname: str = Field(default='', description='昵称')
    avatar: str = Field(default='', description='头像URL')
    user_signature: Optional[str] = Field(default=None, description='用户简介')

    # 互动数据
    like_count: int = Field(default=0, description='点赞数')
    sub_comment_count: int = Field(default=0, description='子评论数')

    # 层级关系
    parent_comment_id: Optional[str] = Field(default=None, description='父评论ID（子评论使用）')
    is_sub_comment: bool = Field(default=False, description='是否为子评论')

    # 其他
    ip_location: str = Field(default='', description='IP属地')

    # 元数据
    crawl_time: Optional[datetime] = Field(default=None, description='抓取时间（从文件名提取）')
    source_file: str = Field(default='', description='来源文件路径')

    # 元数据
    crawl_time: Optional[datetime] = Field(default=None, description='抓取时间（从文件名提取）')
    source_file: str = Field(default='', description='来源文件路径')

    # 保留原始数据
    raw_data: Dict[str, Any] = Field(default_factory=dict, description='原始数据')

    @field_validator('create_time', mode='before')
    @classmethod
    def parse_timestamp(cls, v: Any) -> Optional[datetime]:
        """将 Unix 时间戳转换为 datetime"""
        if v is None:
            return None
        if isinstance(v, datetime):
            return v
        if isinstance(v, (int, float)):
            return datetime.fromtimestamp(v)
        if isinstance(v, str):
            try:
                return datetime.fromtimestamp(int(v))
            except ValueError:
                pass
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                return None
        return None

    @field_validator('like_count', 'sub_comment_count', mode='before')
    @classmethod
    def parse_count(cls, v: Any) -> int:
        """将字符串数字转换为整数"""
        if v is None:
            return 0
        if isinstance(v, int):
            return v
        if isinstance(v, str):
            try:
                return int(v) if v else 0
            except ValueError:
                return 0
        return 0

    @field_validator('pictures', mode='before')
    @classmethod
    def parse_pictures(cls, v: Any) -> List[str]:
        """解析图片字段（支持逗号分隔的字符串或列表）"""
        if v is None:
            return []
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            if not v:
                return []
            return [url.strip() for url in v.split(',') if url.strip()]
        return []


class ParsedData(BaseModel):
    """
    解析结果容器

    包含解析后的帖子和评论列表，以及解析统计信息
    """

    model_config = {'frozen': False}  # 允许后续更新统计信息

    posts: List[Post] = Field(default_factory=list, description='帖子列表')
    comments: List[Comment] = Field(default_factory=list, description='评论列表')
    platform: Optional[Platform] = Field(default=None, description='检测到的平台')

    # 解析统计
    total_records: int = Field(default=0, description='总记录数')
    success_count: int = Field(default=0, description='成功解析数')
    error_count: int = Field(default=0, description='解析失败数')
    errors: List[str] = Field(default_factory=list, description='错误信息列表')

    @property
    def total_interactions(self) -> Dict[str, int]:
        """计算总互动量"""
        return {
            'likes': sum(p.liked_count for p in self.posts),
            'collects': sum(p.collected_count for p in self.posts),
            'comments': sum(p.comment_count for p in self.posts),
            'shares': sum(p.share_count for p in self.posts),
        }

    @property
    def user_count(self) -> int:
        """统计唯一用户数量"""
        user_ids = set()
        for post in self.posts:
            if post.user_id:
                user_ids.add((post.platform.value, post.user_id))
        for comment in self.comments:
            if comment.user_id:
                user_ids.add((comment.platform.value, comment.user_id))
        return len(user_ids)

    @property
    def deduplication_stats(self) -> Dict[str, int]:
        """获取去重统计信息"""
        # 统计帖子重复数
        post_keys = {}
        for post in self.posts:
            key = (post.platform.value, post.content_id)
            if key in post_keys:
                post_keys[key] += 1
            else:
                post_keys[key] = 1
        duplicate_posts = sum(1 for count in post_keys.values() if count > 1)

        # 统计评论重复数
        comment_keys = {}
        for comment in self.comments:
            key = (comment.platform.value, comment.comment_id)
            if key in comment_keys:
                comment_keys[key] += 1
            else:
                comment_keys[key] = 1
        duplicate_comments = sum(1 for count in comment_keys.values() if count > 1)

        return {
            'duplicate_posts': duplicate_posts,
            'duplicate_comments': duplicate_comments,
            'total_duplicates': duplicate_posts + duplicate_comments,
        }

    def deduplicate(self) -> 'ParsedData':
        """
        去重处理：相同内容保留最新抓取的数据

        去重规则：
        - 帖子：(platform, content_id) 相同视为重复
        - 评论：(platform, comment_id) 相同视为重复
        - 保留 crawl_time 最新的数据，如果没有 crawl_time 则保留最后遇到的

        Returns:
            去重后的新 ParsedData 对象
        """

        # 去重帖子：用字典保留最新数据
        post_map: Dict[tuple[str, str], Post] = {}
        for post in self.posts:
            key = (post.platform.value, post.content_id)
            if key in post_map:
                existing = post_map[key]
                # 保留 crawl_time 更新的，如果没有则保留当前（后遇到的优先）
                if post.crawl_time and existing.crawl_time:
                    if post.crawl_time > existing.crawl_time:
                        post_map[key] = post
                else:
                    post_map[key] = post  # 没有 crawl_time 时保留后遇到的
            else:
                post_map[key] = post

        # 去重评论
        comment_map: Dict[tuple[str, str], Comment] = {}
        for comment in self.comments:
            key = (comment.platform.value, comment.comment_id)
            if key in comment_map:
                existing = comment_map[key]
                if comment.crawl_time and existing.crawl_time:
                    if comment.crawl_time > existing.crawl_time:
                        comment_map[key] = comment
                else:
                    comment_map[key] = comment
            else:
                comment_map[key] = comment

        # 创建新的解析结果
        deduplicated = ParsedData(
            posts=list(post_map.values()),
            comments=list(comment_map.values()),
            platform=self.platform,
            total_records=self.total_records,
            success_count=len(post_map) + len(comment_map),
            error_count=self.error_count,
            errors=self.errors,
        )

        return deduplicated
