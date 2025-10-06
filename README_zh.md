# TransTeX 📚  
![LOGO](img/LOGO.png)  
**基于大语言模型的智能 LaTeX 翻译工具 —— 保留结构，翻译内容**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)  [![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-green)]()  [![arXiv 支持](https://img.shields.io/badge/arXiv-支持-orange)]()

TransTeX 利用大语言模型（LLM）智能翻译 LaTeX 文档，**确保翻译后的文档仍能正常编译**。它能精准识别并保护 LaTeX 命令、数学公式、引用和环境，让翻译后的论文与原文一样可靠。

> ✅ **超过 90% 的真实 LaTeX 项目可一次性翻译并成功编译。**

---

## 🌐 语言版本

- [English](README.md)
- [简体中文（本页）](README_zh.md)

---

## ✨ 核心特性

### 🧠 智能翻译引擎
- **结构感知解析**：仅将可翻译文本送入 LLM，所有 LaTeX 语法均被保留。
- **数学安全**：`$...$`、`$$...$$`、`\begin{equation}`、`\cite{}`、`\ref{}`、`\label{}` 等绝不改动。
- **环境识别**：标准环境（`figure`、`table`、`theorem`、`itemize` 等）被正确处理。

### ⚙️ 工业级编译流水线
- **自适应 XeLaTeX 编译**：自动运行 2–5 轮，直到 `.aux` 文件收敛（布局稳定）。
- **参考文献自动检测**：支持经典 BibTeX 和 `biblatex`。
- **非关键缓存清理**：每次编译前自动清除 `.log`、`.toc`、`.aux.bak` 等文件，确保可复现性。

### 📤 双路径 Word 导出（可选）
1. **首选**：Pandoc（`.tex` → `.docx`），自动注入兼容层以支持自定义命令（如 `\naturals`、`\ts`）。
2. **兜底**：PDF → DOCX，通过：
   - **LibreOffice**（高保真，若已安装）
   - **`pdf2docx`**（纯 Python，始终可用）

> 💡 **确保在任何环境下都能生成 Word 文档**。

### 🌐 灵活的 LLM 后端支持
| 后端 | 配置名 | 说明 |
|------|--------|------|
| OpenAI | `openai` | 官方 API |
| 阿里云 | `aliyun` | DashScope 平台，支持联网搜索 |
| 通用 OpenAI 兼容 | `generic` | 支持 **腾讯混元**、**火山引擎**、**Azure OpenAI**、**本地模型** 等 |

所有后端均支持：
- 并发翻译与速率控制  
- 可配置 `temperature`、`top_p`、`max_tokens`  
- 通过环境变量管理 API 密钥（如 `LLM_API_KEY`）

### 📁 项目模式
- **`arxiv`**：通过 URL 翻译论文（自动下载+解包）
- **`single`**：单个 `.tex` 文件
- **`project`**：完整项目目录（含 `.bib`、`.cls`、子文件等）

---

## 📸 示例

| 原文（英文） | 翻译（中文） |
|-------------|------------|
| ![Before](img/before.png) | ![After](img/after.png) |
> **完整翻译效果对比可以在 [示例TeX数据](demo) 和 [示例输出结果](output) 中查看。**

---

## 🚀 快速开始

```bash
git clone https://gitee.com/bao-jiachen/LaTeXTranslator.git
```
```bash
pip install -r requirements.txt
```
```bash
python -m trans --config config.yaml
```

---

## ⚙️ 配置示例（`config.yaml`）

```yaml
# ======== 通用设置 ========
# 项目名称（可选，用于标识项目）
# 指定时，结果将保存在 output.dir 下的时间戳子目录中
project_name: "MyLaTeXProject"
mode: "project"  # arxiv | single | project

# ======== 输入设置 ========
input:
  url: "https://arxiv.org/..."        # arxiv URL 或本地路径
  path: "./demo/document.tex"         # 用于 mode=single 模式
  dir: "./demo/demo_project"          # 用于 mode=project 模式

# ======== 输出设置 ========
output:
  dir: "./my_output"
  compile: true

# ======== 翻译设置 ========
translation:
  target_lang: "Chinese"
  chunk_size: 3800
  use_cot: false
  fix_hyphen: true
  fix_command_adhesion: true

# ===== LLM 设置 ===
llm:
  backend: "aliyun"
  model: "qwen-max"
  api_key: <-- 请替换为您的API密钥 -->
  base_url: "https://dashscope.aliyuncs.com/api/v1"
  temperature: 0.1
  top_p: 0.9
  max_concurrent: 15
  max_retries: 3

# ======== 提示词设置 =======
prompts:
  system: "您是一位专业的LaTeX翻译员。"
  user: "请将以下LaTeX内容翻译为{target_lang}..."

```

---

## ⚠️ 已知限制

- **自定义环境**（如用户定义的 `\begin{proof}...\end{proof}`）可能被部分翻译。  
  → *临时方案：用 `\begin{verbatim}...\end{verbatim}` 包裹，或跳过翻译。*
- 极复杂的 TikZ 图形或嵌套表格可能需要手动调整。

> 🔒 **原始文件永不修改**，所有操作均为非破坏性。

---

## 📄 许可证

MIT © [Jiachen Bao]。详见 [LICENSE](LICENSE)。
