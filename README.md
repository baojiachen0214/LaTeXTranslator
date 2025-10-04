# TransTeX 📚

TransTeX is a tool that uses Large Language Model (LLM) APIs to translate LaTeX documents while preserving LaTeX commands, formulas, and references from being translated, ensuring that the translated document can still be properly compiled.

## ✨ Features

- 📥 Download and translate LaTeX source code from arXiv papers
- 📄 Translate local LaTeX files or entire projects
- 🔒 Smart protection to keep LaTeX commands, formulas, and references from being translated
- 🌐 Support for multiple LLM providers (OpenAI, DeepSeek, Alibaba Cloud, Tencent, etc.)
- 🛠️ Automatic processing and compilation of translated documents to PDF
- ⚙️ Configurable translation parameters including chunk size, temperature, and more
- ⚡ Concurrent requests support for improved translation efficiency
- 💾 Caching mechanism to avoid re-translating identical content

## 📷 Translation Example

Here's an example of a translation from English to Chinese using TransTeX:

<style>
.image-container {
  width: 400px;
  height: 500px;
  object-fit: cover;
}
</style>

<div style="display: flex; justify-content: space-around;">
  <div style="text-align: center;">
    <img src="img/before.png" class="image-container" />
    <p><em>Original English Document</em></p>
  </div>
  <div style="text-align: center;">
    <img src="img/after.png" class="image-container" />
    <p><em>Translated Chinese Document</em></p>
  </div>
</div>


## 🚀 Installation

### Clone the repository

```bash
git clone https://github.com/your-username/trans_tex.git
cd trans_tex
```

### Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### Install dependencies

```bash
pip install .
```

## ⚙️ Configuration

1. Copy and edit the configuration file:

   ```bash
   cp config.example.yaml config.yaml
   ```

2. Edit the `config.yaml` file to set:

   - Mode (`mode`): arxiv | single | project
   - Input source (`input`): arxiv URL or local path
   - Output directory (`output.dir`)
   - Translation settings (`translation`): target language and other parameters
   - LLM settings (`llm`): provider, model, API key, etc.

3. Set API key environment variable or set it directly in the configuration file:

   ```bash
   # Set according to your provider
   export LLM_API_KEY="your-api-key"
   ```

### Configuration File Example

```yaml
# config.example.yaml
mode: "arxiv"  # arxiv | single | project

# Input
input:
  url: "https://arxiv.org/abs/2301.12345"  # arxiv URL or local path
  # path: "./my_paper.tex"                # for mode=single
  # dir: "./my_project/"                  # for mode=project

# Output
output:
  dir: "./translated_paper"
  compile: true

# Translation settings
translation:
  target_lang: "Chinese"
  chunk_size: 3800
  use_cot: false
  fix_hyphen: true
  fix_command_adhesion: true

# LLM settings
llm:
  backend: "openai"
  model: "gpt-4o-mini"
  api_key_env: "LLM_API_KEY"
  base_url: "https://api.openai.com/v1/"
  temperature: 0.1
  top_p: 0.9
  max_concurrent: 15
  max_retries: 3
```

## 📖 Usage

### Basic usage

```bash
python -m trans
```

### Specify configuration file

```bash
python -m trans --config path/to/your/config.yaml
```

## 📁 Modes of Operation

TransTeX supports three modes of operation:

1. **arXiv mode** 📥 - Automatically download and translate papers from arXiv
2. **single mode** 📄 - Translate a single TeX file
3. **project mode** 📁 - Translate an entire TeX project directory

## ⚠️ Known Issues

While TransTeX works well for most documents, there are still some known issues that need to be addressed:

1. **Inline formulas**: Subscripts in inline formulas may not be properly converted, causing underscores to remain as literal characters instead of being interpreted as subscripts.

2. **TikZ graphics**: When processing TikZ graphics, the tool may "consume" or improperly handle curly braces `{}` used in the drawing commands, which can break the graphics compilation.

3. **Complex table structures**: Very complex tables with nested structures may not be handled perfectly.

We are continuously working to improve these issues in future releases.

## 📄 License

[MIT](LICENSE)