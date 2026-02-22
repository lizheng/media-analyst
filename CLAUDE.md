# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Running the Application
```bash
# Start the Streamlit development server
uv run streamlit run streamlit_app.py

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

This is a **Streamlit-based web UI wrapper** around the [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler) project. It does not implement crawling logic itself; instead, it launches MediaCrawler as a subprocess with user-configured parameters.

### Key Components

**streamlit_app.py** - The main and only application file containing:
- Streamlit UI configuration and page layout (`st.set_page_config`)
- Form builders for crawler parameters (platform, login type, crawler type, etc.)
- `run_crawler()` - Executes MediaCrawler via `subprocess.Popen` using `uv run main.py`
- `build_args()` - Converts UI form values into MediaCrawler CLI arguments

### External Dependency

The application **requires MediaCrawler to be installed separately** at a hardcoded path:
```python
MEDIA_CRAWLER_PATH = Path("../MediaCrawler")
```

This path is used as the working directory when spawning the crawler subprocess. If MediaCrawler is not present at this location, the application will fail at runtime.

### Supported Platforms

The UI supports configuring crawlers for: 小红书 (xhs), 抖音 (dy), 快手 (ks), B站 (bili), 微博 (wb), 贴吧 (tieba), 知乎 (zhihu)

### Data Flow

1. User configures options via Streamlit sidebar and main form
2. `build_args()` constructs CLI arguments matching MediaCrawler's expected format
3. `run_crawler()` spawns a subprocess: `uv run main.py [args]` in `MEDIA_CRAWLER_PATH`
4. stdout/stderr are streamed back to the UI in real-time

## Testing

项目包含两层测试架构：

### 1. Streamlit UI 测试 (`tests/test_streamlit_ui.py`)
使用 `streamlit.testing.v1.AppTest` 测试界面组件和交互，**无需实际运行 MediaCrawler**。

```bash
# 运行UI测试（快速）
uv run pytest tests/test_streamlit_ui.py -v
```

测试覆盖：页面加载、平台选择、爬虫类型切换、参数构建等。

### 2. 真实 E2E 测试 (`tests/test_e2e_real.py`)
使用 `subprocess` 实际调用 MediaCrawler，**需要 MediaCrawler 环境**。

```bash
# 运行真实E2E测试（慢速，首次需扫码）
uv run pytest tests/test_e2e_real.py -v -s
```

测试场景：抖音详情模式真实爬取，验证输出文件生成。

### 测试配置
- 测试框架: `pytest` + `pytest-timeout` + `pytest-asyncio`
- 超时设置: 5分钟（允许扫码和爬取）
- 测试目录: `tests/`

## Development Notes

- Python version: 3.14+ (specified in `.python-version`)
- Package manager: `uv` with Tsinghua PyPI mirror configured
- The TODO.md tracks known issues: logging cleanup, button states, speed optimization, URL detection/parsing, and UI state persistence
