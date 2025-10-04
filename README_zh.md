# TransTeX 📚  
![LOGO](img/LOGO.png)

**基于大语言模型的智能 LaTeX 翻译工具 —— 保留结构，精准翻译内容**

[![License: MIT](https://img.shields.io/badge/许可证-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-green)]()
[![支持 arXiv](https://img.shields.io/badge/arXiv-支持-orange)]()

TransTeX 利用大语言模型（LLM）智能翻译 LaTeX 文档，**确保编译不中断**。它能自动识别并保护 LaTeX 命令、数学公式、参考文献和环境结构，使翻译后的文档像原文一样顺利编译。

---

## 🌐 语言版本

- [English](README.md)
- [简体中文（当前页面）](README_zh.md)

---

## ✨ 核心特性

- **📥 arXiv 一键翻译**：通过 arXiv 链接自动下载并翻译论文  
- **📁 项目级支持**：处理多文件 LaTeX 项目（`.tex`、`.bib`、`.cls` 等）  
- **🛡️ 智能保护机制**：  
  - 数学环境（`$...$`、`$$...$$`、`\begin{equation}`）完全保留  
  - 命令如 `\cite{}`、`\ref{}`、`\label{}` 不被翻译  
  - 环境（`figure`、`table`、`algorithm`）结构不受干扰  
- **🌐 多 LLM 后端支持**：OpenAI、DeepSeek、阿里云、腾讯混元等  
- **⚡ 并行翻译**：并发调用 API，显著提升翻译速度  
- **💾 智能缓存**：相同内容仅翻译一次，节省时间和配额  
- **🖨️ 自动编译 PDF**：翻译后自动调用 `latexmk` 生成 PDF

---

## 📸 翻译示例

| 原文（英文） | 翻译结果（中文） |
|--------------|------------------|
| ![Before](img/before.png) | ![After](img/after.png) |

---

## 🚀 快速开始

### 1. 克隆与安装

```bash
git clone https://github.com/your-username/trans_tex.git
cd trans_tex
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
pip install .
```

### 2. 配置

```bash
cp config.example.yaml config.yaml
# 编辑 config.yaml（设置 API 密钥、目标语言等）
export LLM_API_KEY="sk-xxxx"
```

### 3. 运行

```bash
python -m trans --config config.yaml
```

---

## ⚙️ 配置概览

```yaml
mode: "arxiv"  # arxiv | single | project

input:
  url: "https://arxiv.org/abs/2301.12345"

output:
  dir: "./output"
  compile: true

translation:
  target_lang: "Chinese"
  chunk_size: 3800

llm:
  backend: "openai"
  model: "gpt-4o-mini"
  api_key_env: "LLM_API_KEY"
```
---

## 📁 运行模式

| 模式        | 输入                     | 适用场景                     |
|-------------|--------------------------|------------------------------|
| `arxiv`     | arXiv 论文链接           | 翻译已发表论文               |
| `single`    | 单个 `.tex` 文件路径     | 单篇手稿翻译                 |
| `project`   | LaTeX 项目目录           | 学位论文、书籍或复杂排版项目 |

---

## ⚠️ 已知限制

- **行内公式**：如 `$x_i$` 中的下划线 `_` 可能被错误转义  
- **TikZ 图形**：`\draw{...}` 中的花括号 `{}` 可能被误解析  
- **复杂表格**：含 `\multicolumn` 或嵌套结构的表格可能格式错乱  

---

## 📄 许可证

MIT © [Jiachen Bao]。详见 [LICENSE](LICENSE)。
