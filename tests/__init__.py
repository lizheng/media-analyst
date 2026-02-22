"""
测试包

测试分层：
- unit/: 单元测试（纯函数、模型验证）
- integration/: 集成测试（组件交互、mock）
- ui/: UI 测试（Streamlit AppTest）
- real_crawler/: 真实爬虫测试（真实 MediaCrawler 进程）

运行方式：
- 快速测试: uv run pytest tests/unit tests/integration -v
- UI 测试: uv run pytest tests/ui -v
- 真实爬虫测试: uv run pytest tests/real_crawler -v -s
"""
