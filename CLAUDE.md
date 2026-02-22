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
- `models.py` - Pydantic data models (SearchRequest, DetailRequest, CreatorRequest, CrawlerExecution)
- `params.py` - Pure functions for building CLI arguments
- `config.py` - Constants and mappings
- `url_parser.py` - Douyin URL extraction and normalization (pure functions)

**src/media_analyst/shell/** - Imperative Shell (side effects)
- `runner.py` - CrawlerRunner class for process management (subprocess)

**src/media_analyst/ui/** - Streamlit UI
- `app.py` - Main application with form builders and execution logic

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

The application **requires MediaCrawler to be installed separately** at a hardcoded path:
```python
MEDIA_CRAWLER_PATH = Path("../MediaCrawler")
```

This path is used as the working directory when spawning the crawler subprocess. If MediaCrawler is not present at this location, the application will fail at runtime.

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
# 运行单元测试（40个，<1秒）
uv run pytest tests/unit -v
```

测试覆盖：
- Pydantic 模型验证（MISM 原则）
- `build_args()` 纯函数
- `to_cli_args()` 方法
- 模型序列化/反序列化
- URL 解析（`extract_douyin_links`, `parse_douyin_url`）- 支持多种抖音链接格式

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
# 运行集成测试（14个）
uv run pytest tests/integration -v
```

### 3. UI 测试 (`tests/ui/`)

**测试目标**：Streamlit 界面和 `build_request()` 输出

**特点**：
- 🖥️ 使用 `streamlit.testing.v1.AppTest`
- ✅ 验证 UI 操作输出正确的 Pydantic 模型
- 🔗 连接用户操作与 Core 层

```bash
# 运行UI测试（13个）
uv run pytest tests/ui -v
```

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
- 测试框架: `pytest` + `pytest-timeout` + `pytest-asyncio`
- 超时设置: 5分钟（允许扫码和爬取）
- 测试目录: `tests/`
- 标记: `real_crawler`（真实爬虫）, `human_interaction`（需人工介入）, `slow`（执行慢）

### 测试编写规范

1. **偏好函数形式**：使用 `def test_xxx()` 而非 `class TestXxx:`
2. **按主题分文件**：一个测试文件一个主题（如 test_core_models.py）
3. **使用注释分组**：用 `===` 分隔不同主题的测试
4. **命名清晰**：`test_<被测对象>_<场景>_<预期结果>`

## Development Notes

- Python version: 3.14+ (specified in `.python-version`)
- Package manager: `uv` with Tsinghua PyPI mirror configured
- Project layout: `src/` layout (modern Python packaging)
- Architecture: Functional Core, Imperative Shell (FCIS)
- Design Principle: Make Illegal States Unrepresentable (MISM)
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

### 3. 测试即架构验证

测试结构直接反映架构分层：
- `tests/unit/` → Core 层（纯函数）
- `tests/integration/` → Shell 层（副作用）
- `tests/ui/` → UI 层（交互）

如果测试难以编写，说明架构可能需要调整。
