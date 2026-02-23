# 抖音/小红书数据采集工具 - 从零开始

## 准备工作

您需要提前安装好：

1. **MediaCrawler**（并且用过一次，完成过扫码登录）
2. **uv**（Python 包管理器，比 pip 更快）

---

## 第一步：安装 uv（如果还没有）

**Windows 用户：**
```bash
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**Mac 用户：**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

装好后**关闭并重新打开**命令行窗口。

---

## 第二步：下载本工具

打开命令行，进入您想放工具的文件夹：

```bash
# 下载代码
git clone https://github.com/lizheng/media-analyst.git

# 进入文件夹
cd media-analyst
```

---

## 第三步：安装依赖

在 `media-analyst` 文件夹里运行：

```bash
uv sync
```

**您会看到：**
- 开始下载各种包（显示进度条）
- 最后出现 `Installed` 或 `Resolved` 字样就是成功了

---

## 第四步：启动程序

```bash
uv run streamlit run src/media_analyst/ui/app.py
```

**您会看到：**
```
You can now view your Streamlit app in your browser.

Local URL: http://localhost:8501
Network URL: http://192.168.x.x:8501
```

然后**自动打开浏览器**，显示网页界面。

---

## 第五步：配置 MediaCrawler 路径（关键！）

**第一次使用必须做这个：**

1. 看网页**左侧边栏**
2. 找到"**MediaCrawler 路径**"输入框
3. 填入您的 MediaCrawler 文件夹的**完整路径**：

   **Windows 示例：**
   ```
   C:\Users\您的用户名\Documents\MediaCrawler
   ```

   **Mac 示例：**
   ```
   /Users/您的用户名/MediaCrawler
   ```

4. **按回车键**或点击其他地方，路径会自动保存

**怎么找自己的 MediaCrawler 在哪里？**

- **Windows**：在 MediaCrawler 文件夹上右键 → 属性 → 复制"位置"
- **Mac**：打开 Finder，找到 MediaCrawler 文件夹，按 `Cmd + Option + C` 复制路径

---

## 第六步：开始爬取

**左侧边栏选择：**
- **平台**：抖音、小红书、B站等
- **模式**：
  - 🔍 **搜索模式**：输入关键词（如"美食"）
  - 📝 **详情模式**：粘贴具体视频链接
  - 👤 **作者模式**：粘贴作者主页链接

**填好信息后**，点击页面下方的**"开始爬取"**按钮。

**您会看到：**
- 下方出现黑色日志窗口
- 显示"启动爬虫"、"正在爬取"等文字
- 最后显示"爬取完成"和数据保存位置

---

## 第七步：数据解析

如果想看爬到的数据：

1. 点击页面左上角的"**数据解析**"
2. 输入 MediaCrawler 的 `data` 文件夹路径
3. 点击"**解析数据**"
4. 可以在网页上直接看表格

---

## 常见问题

### Q1：提示 "MediaCrawler 路径不存在"

- 检查路径是否填对（特别是斜杠方向，Windows 用 `\`，Mac 用 `/`）
- 确保路径指向的是 MediaCrawler 的**根文件夹**（里面有 `main.py` 的那个）

### Q2：提示 "command not found: uv"

- uv 安装后需要**重新打开命令行窗口**
- 还不行就重启电脑

### Q3：启动后浏览器没自动打开

- 手动在浏览器地址栏输入：`http://localhost:8501`

### Q4：扫码登录后卡住

- 这是正常的，MediaCrawler 在后台运行
- 看日志窗口，有数据在跑就是正常的

### Q5：怎么停止爬取？

- 点击网页上的"**停止**"按钮
- 或者直接关闭命令行窗口

---

## 数据在哪里？

爬取的数据保存在：
```
您的 MediaCrawler 文件夹/data/平台名称/日期/
```

可以直接在工具的"**数据解析**"页面查看，不用去找文件夹。

---

## 下次使用

以后只需要两步：

1. 打开命令行，进入 `media-analyst` 文件夹
2. 运行 `uv run streamlit run src/media_analyst/ui/app.py`

路径已经保存好了，不用再配置。
