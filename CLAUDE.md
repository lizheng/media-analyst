# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the Application
```bash
# Start the Streamlit development server
uv run streamlit run src/media_analyst/ui/app.py

# The app will be available at http://localhost:8501
```

### Dependency Management
```bash
# Add a new dependency
uv add <package>

# Sync dependencies from uv.lock
uv sync
```

### Linting & Formatting

项目使用 **Ruff** 进行代码 linting 和格式化（替代 black + isort + flake8）：

```bash
# 检查代码（从项目根目录运行，自动排除 .venv/ 等目录）
uv run ruff check .

# 自动修复可修复的问题
uv run ruff check . --fix

# 格式化代码
uv run ruff format .

# 检查格式化（不修改文件）
uv run ruff format --check .
```

**Ruff 配置**（`pyproject.toml`）：
- 行长度: 120 字符
- Python 目标版本: 3.13
- 引号风格: 单引号
- 启用规则: `E` (pycodestyle), `F` (Pyflakes), `I` (isort)

### Git Hooks (Prek)

项目使用 **prek** 作为 Git pre-commit hook，在提交前自动运行代码检查和测试：

```bash
# 安装 prek（首次）
uv tool install prek

# 安装 git hooks（项目初始化时）
prek install

# 查看已配置的 hooks
prek list

# 手动运行所有 hooks
prek run --all-files

# 仅运行特定 hook
prek run ruff --all-files

# 跳过 hooks（紧急情况）
git commit --no-verify -m "hotfix"
```

**prek 配置**（`.pre-commit-config.yaml`）：
- **Ruff Linter**: 自动修复代码问题
- **Ruff Formatter**: 格式化代码
- **Pytest**: 运行单元测试、集成测试和 UI 测试

**为什么使用 prek？**
- prek 是用 Rust 重写的 pre-commit，完全兼容其配置格式
- 速度更快，单二进制文件无额外依赖
- 原生支持并行执行和 uv 集成

> **注意**: prek 不是 Python 依赖，需要通过 `uv tool install` 单独安装。

## Architecture

This is a **Streamlit-based web UI wrapper** around the [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) project.

### Core Design Principles

#### 1. Functional Core, Imperative Shell (FCIS)

**核心思想**：将业务逻辑（纯函数）与副作用（IO、状态变更）严格分离。

```
┌─────────────────────────────────────────────────────────────┐
│                        UI Layer                              │
│  (Streamlit - 用户交互、状态管理)                              │
└───────────────────────┬─────────────────────────────────────┘
                        │ build_request()
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                     Functional Core                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │    Models    │  │    Params    │  │      Config      │  │
│  │  (Pydantic)  │  │ (Pure Funcs) │  │    (Constants)   │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│                                                              │
│  特点：无副作用、可测试、可序列化、类型安全                     │
└───────────────────────┬─────────────────────────────────────┘
                        │ CrawlerRunner
                        ▼
┌─────────────────────────────────────────────────────────────┐
│                    Imperative Shell                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                   CrawlerRunner                       │  │
│  │  - subprocess.Popen()  - 文件系统操作                  │  │
│  │  - 实时输出捕获        - 进程生命周期管理               │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                              │
│  特点：封装所有副作用、便于Mock、可替换为其他后端              │
└─────────────────────────────────────────────────────────────┘
```

**FCIS 在本项目中的实践**：

| 层级 | 职责 | 示例 |
|------|------|------|
| **Core** | 数据转换、验证、业务规则 | `request.to_cli_args()` 纯函数 |
| **Shell** | IO操作、进程管理 | `CrawlerRunner.start()` 有副作用 |
| **UI** | 用户交互、调用Core/Shell | `build_request()` + `runner.start()` |

**FCIS 带来的好处**：
1. **可测试性**：Core 层无需 Mock，直接测试纯函数
2. **可维护性**：业务逻辑与IO分离，修改一边不影响另一边
3. **可移植性**：Shell 可替换为远程执行（Docker/SSH/K8s）

#### 2. Make Illegal States Unrepresentable (MISM)

**核心思想**：利用类型系统让不合法的状态在编译期（或模型创建期）就无法表示，而非运行时检查。

**实践示例**：

```python
# ❌ 不推荐：通用模型 + 运行时验证
class CrawlerRequest(BaseModel):
    crawler_type: str  # "search" | "detail" | "creator"
    keywords: Optional[str] = None
    specified_ids: Optional[str] = None
    creator_ids: Optional[str] = None

# 需要在运行时检查
if crawler_type == "search" and not keywords:
    raise ValueError("搜索模式需要关键词")

# ✅ 推荐：特定模型，让不合法状态无法表示
class SearchRequest(BaseModel):
    crawler_type: Literal["search"] = "search"
    keywords: str  # 必填，非Optional

class DetailRequest(BaseModel):
    crawler_type: Literal["detail"] = "detail"
    specified_ids: str  # 必填

class CreatorRequest(BaseModel):
    crawler_type: Literal["creator"] = "creator"
    creator_ids: str  # 必填
```

**MISM 在本项目中的实践**：

1. **请求模型分离**：
   - `SearchRequest` 必须提供 `keywords`
   - `DetailRequest` 必须提供 `specified_ids`
   - `CreatorRequest` 必须提供 `creator_ids`

2. **执行状态验证**：
   ```python
   class CrawlerExecution(BaseModel):
       @model_validator(mode="after")
       def validate_status_consistency(self):
           # RUNNING 状态必须有 process_id
           if self.status == ExecutionStatus.RUNNING and self.process_id is None:
               raise ValueError("running 状态必须有 process_id")
           # COMPLETED 状态必须有 end_time
           if self.status == ExecutionStatus.COMPLETED and self.end_time is None:
               raise ValueError("completed 状态必须有 end_time")
   ```

3. **输出文件存在性验证**：
   ```python
   @model_validator(mode="after")
   def validate_output_files_exist(self):
       for file_path in self.output_files:
           if not file_path.exists():
               raise ValueError(f"输出文件不存在: {file_path}")
   ```

### Key Components

**src/media_analyst/core/** - Functional Core (pure functions, no side effects)
- `models.py` - Pydantic data models
  - Crawler: `SearchRequest`, `DetailRequest`, `CreatorRequest`, `CrawlerExecution`
  - Parser: `Post`, `Comment`, `ParsedData` (解析结果模型)
- `params.py` - Pure functions for building CLI arguments
- `config.py` - Constants and mappings
- `url_parser.py` - Douyin URL extraction and normalization (pure functions)
- `parser.py` - Data parser (自动检测平台、去重处理)

**src/media_analyst/shell/** - Imperative Shell (side effects)
- `runner.py` - CrawlerRunner class for process management (subprocess)

**src/media_analyst/ui/** - Streamlit UI
- `app.py` - Main application with form builders and execution logic
- `parser_page.py` - Data parser page (读取-解析-预览)
- `persistence.py` - User preferences and path management (统一管理 MediaCrawler 路径)

### Data Flow

```
用户输入 → build_request() → Pydantic Model → to_cli_args() → CLI Args
                                                            ↓
UI 显示 ← CrawlerExecution ← CrawlerRunner ← subprocess.Popen
```

1. User configures options via Streamlit sidebar and main form
2. `build_request()` creates a Pydantic model (SearchRequest/DetailRequest/CreatorRequest)
3. `request.to_cli_args()` generates CLI arguments (pure function)
4. `CrawlerRunner.start(request)` spawns subprocess: `uv run main.py [args]`
5. `CrawlerExecution` tracks process state, stdout/stderr, and output files

### Data Parsing

The application includes a separate data parsing page (`parser_page.py`) for parsing crawled JSON data:

**Features:**
- Accept directory input (recursively finds all `.json` files)
- Auto-detect platform from filename and content
- Deduplication (keeps latest crawl based on filename timestamp)
- Preview parsed data in tables

**Deduplication Strategy:**
```python
# Post: (platform, content_id) as unique key
# Comment: (platform, comment_id) as unique key
# Keep the one with latest crawl_time
```

**Crawl Time Extraction:**
- Extracted from filename: `douyin_contents_2024_0221_143052.json` → `2024-02-21 14:30:52`
- Fallback to file modification time

### URL Parsing (Douyin)

The application includes a URL parser for Douyin links that supports extracting and normalizing various URL formats:

**Supported URL formats:**
- Short links: `https://v.douyin.com/xxxxx/` (requires resolver for full normalization)
- Video pages: `https://www.douyin.com/video/xxxxx`
- Note pages: `https://www.douyin.com/note/xxxxx` → normalized to video format
- Featured pages: `https://www.douyin.com/jingxuan?modal_id=xxxxx` → normalized to video format
- Mobile pages: `https://m.douyin.com/share/video/xxxxx` → normalized to video format

**Usage in Core:**
```python
from media_analyst.core import extract_douyin_links, format_link_for_display

# Extract links from share text or comma-separated URLs
text = "6.61 w@f.bn https://v.douyin.com/abc123/ 复制此链接"
links = extract_douyin_links(text)

# links[0].link_type == "short"
# links[0].video_id == "abc123"
# links[0].normalized == "https://v.douyin.com/abc123/" (unchanged for short links)

# To resolve short links, provide a resolver function:
def resolve_short_link(url: str) -> str:
    import requests
    response = requests.head(url, allow_redirects=True)
    return response.url

links = extract_douyin_links(text, short_link_resolver=resolve_short_link)
# Now links[0].link_type == "video" with real video ID
```

**Note:** Short link resolution requires HTTP requests (side effects), so it's implemented as an optional callback. The Core layer remains pure - the Shell layer can provide the resolver when needed.

### External Dependency

### MediaCrawler Path Configuration

The application uses a **unified path management** system via `persistence.py`:

**Path Resolution Priority:**
1. User saved path (stored in `~/.media_analyst/preferences.json`)
2. Auto-detected path (multiple strategies)
3. Default: `../MediaCrawler` (relative to working directory)

**Auto-detection Strategies:**
- Current working directory relative (`../MediaCrawler`)
- Based on `__file__` location
- CWD parents traversal
- Common absolute paths (`~/MediaCrawler`, `~/projects/MediaCrawler`)

**Usage:**
```python
from media_analyst.ui.persistence import get_media_crawler_path

# Get path (auto-resolves using priority above)
mc_path = get_media_crawler_path()

# Save custom path
save_media_crawler_path("/path/to/MediaCrawler")
```

Both the crawler page and parser page use this unified configuration.

### Supported Platforms

The UI supports configuring crawlers for: 小红书 (xhs), 抖音 (dy), 快手 (ks), B站 (bili), 微博 (wb), 贴吧 (tieba), 知乎 (zhihu)

## Testing

项目采用分层测试架构，**严格对应 FCIS 架构分层**：

```
tests/
├── unit/              # 测试 Core 层（纯函数，无需 Mock）
├── integration/       # 测试 Shell 层（Mock 副作用）
├── ui/                # 测试 UI 层（AppTest，验证模型输出）
└── real_crawler/      # 端到端测试（真实进程，慢速）
```

### 1. 单元测试 (`tests/unit/`)

**测试目标**：Core 层的纯函数和模型验证

**特点**：
- ⚡ **极速**：无需 MediaCrawler，无需文件系统
- 🎯 **精准**：失败即说明业务逻辑有问题
- 📦 **独立**：每个测试不依赖外部状态

```bash
# 运行单元测试（~160个，<1秒）
uv run pytest tests/unit -v
```

测试覆盖：
- Pydantic 模型验证（MISM 原则）
- `build_args()` 纯函数
- `to_cli_args()` 方法
- 模型序列化/反序列化
- URL 解析（`extract_douyin_links`, `parse_douyin_url`）
- 数据解析（`parse_json_file`, `parse_json_files`）
- 去重逻辑（`deduplicate`, `deduplication_stats`）
- 真实数据格式测试（使用 MediaCrawler 实际输出格式）
- CLI 入口测试
- 偏好持久化测试

**示例**（纯函数测试）：
```python
def test_build_args_is_pure():
    """相同输入产生相同输出，不修改原对象"""
    req = SearchRequest(platform=Platform.DY, keywords="测试")
    args1 = build_args(req)
    args2 = build_args(req)
    assert args1 == args2  # 幂等
    assert req.keywords == "测试"  # 未修改原对象
```

### 2. 集成测试 (`tests/integration/`)

**测试目标**：Shell 层的 Runner，使用 mock subprocess

**特点**：
- 🎭 Mock 外部依赖（subprocess）
- 🔍 验证 Runner 与 Core 的集成
- ⚡ 快速执行（无需真实爬虫）

```bash
# 运行集成测试（~20个）
uv run pytest tests/integration -v
```

测试覆盖：
- Runner 初始化和验证
- 进程启动和停止
- 输出捕获和超时处理
- 错误处理（FileNotFoundError, PermissionError 等）

### 3. UI 测试 (`tests/ui/`)

**测试目标**：Streamlit 界面和 `build_request()` 输出

**特点**：
- 🖥️ 使用 `streamlit.testing.v1.AppTest`
- ✅ 验证 UI 操作输出正确的 Pydantic 模型
- 🔗 连接用户操作与 Core 层

```bash
# 运行UI测试（~80个）
uv run pytest tests/ui -v
```

**测试覆盖**：
- 主应用页面加载和交互
- 数据解析页面功能
- 各爬虫模式的表单渲染
- `build_request()` 输出验证
- 侧边栏配置组件

**关键测试**：验证 UI 输出正确的模型类型
```python
def test_build_search_request():
    """UI 表单应输出 SearchRequest 模型"""
    request = build_request(common_config, mode_config)
    assert isinstance(request, SearchRequest)
    assert request.keywords == "美食,旅游"
```

### 4. 真实爬虫测试 (`tests/real_crawler/`)

**测试目标**：完整数据流验证（需要真实 MediaCrawler 环境）

**特点**：
- 🐢 慢速执行（需要扫码、网络请求）
- ✅ 验证完整数据流：Model → Runner → Execution
- 👤 可能需要人工介入（首次扫码登录）

```bash
# 运行真实爬虫测试（4个，慢速）
uv run pytest tests/real_crawler -v -s
```

### 测试配置
- 测试框架: `pytest` + `pytest-timeout` + `pytest-asyncio` + `pytest-cov`
- 超时设置: 5分钟（允许扫码和爬取）
- 测试目录: `tests/`
- 标记: `real_crawler`（真实爬虫）, `human_interaction`（需人工介入）, `slow`（执行慢）

### 覆盖率测试

**当前覆盖率**（261 个测试）：

| 模块 | 覆盖率 | 说明 |
|------|--------|------|
| `core/models.py` | 94.9% | Pydantic 模型验证 |
| `core/params.py` | 100% | 纯函数 CLI 参数构建 |
| `core/parser.py` | 91.4% | 数据解析和平台检测 |
| `core/url_parser.py` | 98.5% | URL 提取和标准化 |
| `core/config.py` | 100% | 配置常量 |
| `shell/runner.py` | 93.8% | 进程管理 |
| `ui/persistence.py` | 95.1% | 偏好持久化 |
| `ui/app.py` | 57.0% | 主应用界面 |
| `ui/parser_page.py` | 47.3% | 数据解析页面 |
| `cli.py` | 100% | CLI 入口 |
| **整体** | **81.3%** | 总计 1414 语句 |

使用 `pytest-cov` 进行测试覆盖率统计：

```bash
# 运行所有测试并显示覆盖率报告
uv run pytest tests/unit tests/integration tests/ui --cov --cov-report=term

# 生成 HTML 覆盖率报告（详细到每一行）
uv run pytest tests/unit tests/integration tests/ui --cov --cov-report=html

# 查看 HTML 报告
open htmlcov/index.html

# 仅查看未覆盖的代码行
uv run pytest tests/unit tests/integration tests/ui --cov --cov-report=term-missing

# 指定覆盖率阈值（低于此值会失败）
uv run pytest tests/unit tests/integration tests/ui --cov --cov-fail-under=80
```

**覆盖率配置**（在 `pyproject.toml` 中）：
- 统计范围：`src/media_analyst/` 目录下的源代码
- 排除项：测试文件、`__pycache__`、TYPE_CHECKING 代码块
- HTML 报告输出到 `htmlcov/` 目录

### 测试文件组织

```
tests/
├── unit/                      # 单元测试（纯函数，无需 Mock）
│   ├── test_core_models.py    # Pydantic 模型测试（44个）
│   ├── test_params.py         # CLI 参数构建测试
│   ├── test_parser.py         # 数据解析测试（53个）
│   ├── test_url_parser.py     # URL 解析测试
│   ├── test_persistence.py    # 偏好持久化测试（29个）
│   └── test_cli.py            # CLI 入口测试（9个）
├── integration/               # 集成测试（Mock 副作用）
│   └── test_runner.py         # CrawlerRunner 测试（21个）
├── ui/                        # UI 测试（AppTest）
│   ├── test_streamlit.py      # 主应用测试（29个）
│   └── test_parser_page.py    # 解析页面测试（19个）
└── real_crawler/              # 端到端测试（慢速）
    └── test_real_crawler.py
```

### 测试编写规范

1. **偏好函数形式**：使用 `def test_xxx()` 而非 `class TestXxx:`
2. **按主题分文件**：一个测试文件一个主题（如 test_core_models.py）
3. **使用注释分组**：用 `===` 分隔不同主题的测试
4. **命名清晰**：`test_<被测对象>_<场景>_<预期结果>`
5. **分层测试**：
   - Core 层测试：直接调用纯函数，无需 Mock
   - Shell 层测试：使用 `unittest.mock.patch` 模拟 IO
   - UI 层测试：使用 `streamlit.testing.v1.AppTest`

## Development Notes

- Python version: 3.13+ (specified in `.python-version`)
- Package manager: `uv` with Tsinghua PyPI mirror configured
- Project layout: `src/` layout (modern Python packaging)
- Architecture: Functional Core, Imperative Shell (FCIS)
- Design Principle: Make Illegal States Unrepresentable (MISM)
- Multi-page app: `app.py` (crawler) + `parser_page.py` (data parsing)
- Unified path config: `persistence.py` manages MediaCrawler path
- Git hooks: **prek** for pre-commit checks (Ruff + Pytest)
- The TODO.md tracks known issues: logging cleanup, button states, speed optimization, and UI state persistence

## Key Insights

### 1. FCIS 架构的价值

**重构前**：
```python
# streamlit_app.py - 混合逻辑和IO
def run_crawler(args):
    process = subprocess.Popen(...)  # IO 混合在业务逻辑中
    while True:
        line = process.stdout.readline()
        # 处理输出...
```

**重构后**：
```python
# core/params.py - 纯函数
def build_args(request: CrawlerRequest) -> list[str]:
    return request.to_cli_args()  # 无副作用，易测试

# shell/runner.py - 封装IO
class CrawlerRunner:
    def start(self, request: CrawlerRequest) -> CrawlerExecution:
        # IO 操作封装在这里
```

### 2. Pydantic 模型作为防腐层

Pydantic 模型在代码中充当**数据契约**：
- UI 层输出 `CrawlerRequest`
- Core 层处理 `CrawlerRequest`
- Shell 层接收 `CrawlerRequest`，输出 `CrawlerExecution`

各层之间通过强类型模型交互，避免隐式字典传递。

### 3. 测试覆盖率提升策略

**测试作为质量保障**：
- 新增功能必须配套测试
- Bug 修复先写重现测试，再修复代码
- 覆盖率报告作为 PR 审查参考

**分层覆盖策略**：
- **Core 层**：追求 95%+ 覆盖率（纯函数易于测试）
- **Shell 层**：追求 90%+ 覆盖率（Mock 副作用）
- **UI 层**：覆盖关键用户流程（表单提交、状态转换）

**难以测试的代码是设计问题的信号**：
- 如果测试难以编写，说明耦合度过高
- 考虑重构以提高可测试性
- 遵循 FCIS 架构分离纯函数和副作用

### 4. 测试即架构验证

测试结构直接反映架构分层：
- `tests/unit/` → Core 层（纯函数）
- `tests/integration/` → Shell 层（副作用）
- `tests/ui/` → UI 层（交互）

如果测试难以编写，说明架构可能需要调整。
