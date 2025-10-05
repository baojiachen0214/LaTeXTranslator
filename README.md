# TransTeX 📚  
![LOGO](img/LOGO.png)
**Smart LaTeX Translation Powered by LLMs — Preserve Structure, Translate Content**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-green)]()
[![arXiv Support](https://img.shields.io/badge/arXiv-Supported-orange)]()

TransTeX leverages Large Language Models (LLMs) to translate LaTeX documents **without breaking compilation**. It intelligently protects LaTeX commands, math formulas, citations, and environments — so your translated paper compiles just like the original.

---

## 🌐 Language Versions

- [English (this page)](README.md)
- [简体中文](README_zh.md)

---

## ✨ Key Features

- **📥 arXiv Integration**: Fetch and translate papers directly from arXiv by URL  
- **📁 Project-Aware**: Handle multi-file LaTeX projects (`.tex`, `.bib`, `.cls`, etc.)  
- **🛡️ Smart Protection**:  
  - Math mode (`$...$`, `$$...$$`, `\begin{equation}`) untouched  
  - Commands like `\cite{}`, `\ref{}`, `\label{}` preserved  
  - Environments (`figure`, `table`, `algorithm`) respected  
- **🌐 Multi-LLM Backend**: OpenAI, DeepSeek, Alibaba Cloud, Tencent HunYuan, and more  
- **⚡ Parallel Translation**: Concurrent API calls for faster processing  
- **💾 Smart Caching**: Skip re-translation of identical chunks  
- **🖨️ Auto-Compile**: Generate PDF from translated source (via `latexmk`)

---

## 📸 Example

| Original (English) | Translated (Chinese) |
|--------------------|----------------------|
| ![Before](img/before.png) | ![After](img/after.png) |

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/your-username/trans_tex.git
cd trans_tex
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows
pip install .
```

### 2. Configure

```bash
cp config.example.yaml config.yaml
# Edit config.yaml (set API key, target language, etc.)
export LLM_API_KEY="sk-xxxx"
```

### 3. Run

```bash
python -m trans --config config.yaml
```

---

## ⚙️ Configuration Overview

```yaml
mode: "arxiv"  # arxiv | single | project

# Project name (optional)
# When specified, results will be saved in a timestamped subdirectory under output.dir
project_name: "MyLaTeXProject"

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

## 📁 Operation Modes

| Mode       | Input                     | Use Case                          |
|------------|---------------------------|-----------------------------------|
| `arxiv`    | arXiv URL                 | Translate published papers        |
| `single`   | `.tex` file path          | Single manuscript                 |
| `project`  | Project directory         | Thesis, book, or complex layout   |

---

## ⚠️ Known Limitations

- **Inline math**: `_` in `$x_i$` may be escaped incorrectly  
- **TikZ**: Curly braces in `\draw{...}` can be misparsed  
- **Nested tables**: Complex `tabular` with `\multicolumn` may break  

---

## 📄 License

MIT © [Jiachen Bao]. See [LICENSE](LICENSE).