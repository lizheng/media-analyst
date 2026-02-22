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

## Development Notes

- Python version: 3.14+ (specified in `.python-version`)
- Package manager: `uv` with Tsinghua PyPI mirror configured
- No test suite, linting, or formatting tools are currently configured
- The TODO.md tracks known issues: automated testing, logging cleanup, button states, speed optimization, URL detection/parsing, and UI state persistence
