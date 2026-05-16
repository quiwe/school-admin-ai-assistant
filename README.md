# 高校行政 AI 回复助手

一个面向高校行政老师的 Windows 桌面端助手，用于把学生微信咨询粘贴到软件中，基于本地知识库和 FAQ 生成可人工审核的回复草稿。当前版本不接入微信、企业微信、公众号，也不模拟微信窗口。

## 功能说明

- 回复工作台：粘贴学生问题，生成回复，改写为更正式、更简短、更温和，一键复制。
- 知识库管理：上传 PDF、DOC、DOCX、PPT、PPTX、TXT、XLS、XLSX，自动解析、切分 chunk、建立本地检索依据。
- FAQ 管理：新增、编辑、删除、搜索、导入导出 FAQ，并设置是否允许作为自动回复依据；新增时会提示相似问题，批量导入会跳过重复项。
- 历史记录：保存每次生成结果，支持搜索、分类筛选、复制、标记为常见问题。
- 系统设置：在页面中配置和测试常用大模型 API，包括 OpenAI、Claude、Gemini、DeepSeek、通义千问、智谱 GLM、Kimi、豆包、腾讯混元、硅基流动、MiniMax、Mistral、Cohere、华为云盘古、小米 MiMo、OpenRouter、Ollama、LM Studio 和自定义 OpenAI 兼容接口。
- 数据备份：支持导出和导入 FAQ、知识库解析文本、历史记录和非密钥设置，API Key 不会写入备份。
- 桌面更新：启动时检查 GitHub Release，新版本可在软件内下载并启动安装包；0.3.0 起支持远程最低版本策略。
- 安全控制：成绩、处分、奖助学金结果、学籍状态、个人隐私、投诉申诉、情绪危机等问题强制提示人工核实。

## 本地启动

后端：

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

前端：

```bash
cd frontend
npm install
npm run dev
```

访问 `http://localhost:5173`，API 文档在 `http://localhost:8000/docs`。

## Docker 启动

```bash
cd school-admin-ai-assistant
copy backend\.env.example backend\.env
docker compose up --build
```

访问 `http://localhost:8000`。

## Windows 安装包在线打包

仓库内置 GitHub Actions：`.github/workflows/windows-installer.yml`。

触发方式：

- 修改版本时先只在本地提交，不自动推送、不自动打包。
- 确认发布时再推送代码，并在 GitHub 仓库页面进入 `Actions`，手动运行 `Build Windows Installer`。
- 只有手动运行打包任务后，才会创建或更新对应版本的 GitHub Release。

打包产物：

- Artifact 名称：`SchoolAdminAIAssistant-Windows-Installer-v版本号`
- 安装包文件：`SchoolAdminAIAssistant-Setup-v版本号.exe`
- GitHub Release：每次 `main` 分支打包成功后，会按 `VERSION` 文件创建或更新 `v版本号` Release，并把安装包上传到 Release 附件。

安装包默认安装目录：

```text
D:\SchoolAdminAIAssistant
```

安装后会生成开始菜单快捷方式，可选创建桌面快捷方式。启动后会打开 Windows 桌面窗口，不再跳转到默认浏览器；后台服务只监听本机地址。数据默认保存在安装目录下的 `data` 文件夹中，避免默认写入 C 盘。

桌面版依赖 Microsoft Edge WebView2 Runtime。Windows 10/11 通常已自带；Release 安装包会自动检测，如果目标电脑没有 WebView2，会使用安装包内置的 WebView2 Runtime 安装器自动静默安装。

如果你不是通过 Release 安装包安装，而是自己本地编译了不含内置运行时的安装包，可手动安装 WebView2：

```text
https://developer.microsoft.com/microsoft-edge/webview2/
```

## macOS DMG 在线打包

仓库内置 GitHub Actions：`.github/workflows/macos-app.yml`。

触发方式：

- 确认发布时在 GitHub 仓库页面进入 `Actions`，手动运行 `Build macOS App`。
- 打包任务会读取 `VERSION`、`DEVELOPER` 和 `CHANGELOG.md`，并创建或更新对应版本的 GitHub Release。

打包产物：

- Artifact 名称：`SchoolAdminAIAssistant-macOS-v版本号`
- DMG 文件：`SchoolAdminAIAssistant-macOS-v版本号.dmg`
- GitHub Release：把 `.dmg` 上传到 `v版本号` Release 附件。

macOS 版本暂未签名，首次打开可能需要在系统设置中允许。

## 版本发布规范

每次更新前维护三个文件：

- `VERSION`：当前软件版本号，例如 `0.2.0`。
- `DEVELOPER`：开发者或团队名称，会写入安装器发布者和 Release Notes。
- `CHANGELOG.md`：更新信息，新增 `## 版本号 - 日期` 小节。

发布时 GitHub Actions 会读取这些信息：

- 安装器版本号来自 `VERSION`。
- 安装器开发者/发布者来自 `DEVELOPER`。
- Release tag 使用 `v版本号`。
- Release Notes 使用 `CHANGELOG.md` 中当前版本的小节。

软件内“系统设置 - 版本信息”也会显示对应版本号、开发者和更新信息。

## .env 配置

复制 `backend/.env.example` 为 `backend/.env`，也可以启动后在“系统设置”页面填写 API 配置。页面保存的配置会写入 SQLite 的 `settings` 表，并优先于 `.env` 生效。设置页支持为每个 Provider 单独保存 API Key、Base URL 和模型名称，API Key 留空不会覆盖旧值。

OpenAI：

```env
AI_PROVIDER=openai
OPENAI_API_KEY=你的 API Key
OPENAI_MODEL=gpt-4o-mini
```

本地模型，例如 Ollama：

```env
AI_PROVIDER=ollama
LOCAL_MODEL_BASE_URL=http://localhost:11434
LOCAL_MODEL_NAME=llama3.1
```

API Key 不要写入代码或提交到仓库。

## 上传知识库

进入“知识库管理”，选择文件和分类后上传。支持：

- PDF：使用 `pypdf`
- DOCX：使用 `python-docx`
- DOC：旧版 Office OLE 文本抽取，建议优先另存为 DOCX 或 PDF 以获得更稳定解析效果
- PPTX：使用 `python-pptx`
- PPT：旧版 Office OLE 文本抽取，建议优先另存为 PPTX 或 PDF
- XLSX：使用 `openpyxl`
- XLS：使用 `xlrd`
- TXT：直接读取文本

如果 XLSX 或 XLS 第一行包含“问题”“答案”“分类”列，可勾选“Excel 导入 FAQ”，系统会把表格内容导入 FAQ。

## 使用回复工作台

1. 从微信复制学生问题。
2. 粘贴到“学生问题”输入框。
3. 点击“生成回复”。
4. 查看右侧回复、问题分类、置信度和检索依据。
5. 老师确认或修改后，点击“复制回复”发回微信。

## 使用学生网页端

桌面端启动后，主页会显示带访问码的“网页端地址”。老师可把这个完整地址发给同一局域网内的学生，学生打开后即可在网页端提交咨询问题。

注意：

- 老师电脑需要和学生设备处在同一局域网，且系统防火墙允许当前端口访问。
- 网页端地址中的访问码用于限制学生入口，请不要把地址公开到无关群组或公网。
- 局域网远程访问只开放学生网页端和学生回复接口，知识库、FAQ、设置、历史等管理功能仍限制为老师电脑本机使用。

## AI Provider 切换

AI 调用集中在 `backend/app/services/ai_provider.py` 和 `backend/app/services/runtime_config.py`。当前内置 Provider：

- `openai`：OpenAI Chat Completions。
- `anthropic`：Claude / Anthropic Messages API。
- `gemini`：Google Gemini 原生 API。
- `deepseek`：DeepSeek OpenAI 兼容接口。
- `qwen`：通义千问 / 阿里百炼 OpenAI 兼容接口。
- `zhipu`：智谱 GLM OpenAI 兼容接口。
- `kimi`：Kimi / Moonshot OpenAI 兼容接口。
- `doubao`：豆包 / 火山方舟 OpenAI 兼容接口。
- `hunyuan`：腾讯混元 OpenAI 兼容接口。
- `siliconflow`：硅基流动 OpenAI 兼容接口。
- `minimax`：MiniMax OpenAI 兼容接口。
- `mistral`：Mistral AI OpenAI 兼容接口。
- `cohere`：Cohere OpenAI 兼容接口。
- `pangu`：华为云盘古 / ModelArts OpenAI 格式接口。
- `xiaomi`：小米 MiMo OpenAI 兼容接口。
- `openrouter`：OpenRouter OpenAI 兼容接口。
- `ollama`：Ollama 原生 `/api/chat`。
- `lmstudio`：LM Studio OpenAI 兼容接口。
- `custom`：自定义 OpenAI 兼容接口。

后续如需接入 Azure OpenAI、学校私有模型或新的网关，可优先使用 `custom`，也可以在 `runtime_config.py` 增加 Provider 预设。

## 注意事项

- 当前版本是桌面端半自动助手，所有 AI 回复都需要老师审核。
- 自动更新依赖 GitHub Release。如果网络无法访问 GitHub，可在发布页手动下载安装包。
- 系统不得替代正式行政判断，不得在无依据时编造政策、截止时间、名单或审核结果。
- SQLite 适合 MVP 起步，生产环境建议迁移 PostgreSQL。
- 当前检索为轻量 BM25-like 本地检索，后续可替换 Chroma、FAISS 或 pgvector。
- MVP 会把页面填写的 API Key 保存到 SQLite；生产环境建议增加加密存储或使用专门的密钥管理服务。
