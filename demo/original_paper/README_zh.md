# 论文示例文件说明 📄

本目录包含的示例文件来源于 **arXiv** 上的学术论文：
- Neural Controlled Differential Equations for Irregular Time Series
- 论文地址：https://arxiv.org/pdf/2005.08926v2

## 文件清单 📋

这些是完整的 [LaTeX源文件](https://arxiv.org/src/2005.08926v2)，用于Python项目自动处理：

* **`main.tex`**: 论文的主文档，包含了完整的论文内容和结构。
* **`main.bbl`**: 由BibTeX生成的参考文献列表文件。
* **`main.bib`**: BibTeX参考文献数据库，存放所有引用的文献条目。
* **`custom.sty`**: 自定义的LaTeX宏包文件，用于定义特殊的格式和命令。

## 运行环境要求 ⚙️

在运行Python项目前，请确保你的系统满足以下条件之一：

1. **推荐配置：LaTeX环境**
   * 项目会自动调用LaTeX编译`.tex`文件
   * 请先安装LaTeX发行版，如TeX Live或MikTeX
   * **下载地址**：
     * TeX Live: [https://www.tug.org/texlive/](https://www.tug.org/texlive/)
     * MikTeX: [https://miktex.org/](https://miktex.org/)

2. **备选方案：LibreOffice**
   * 项目可使用LibreOffice将PDF转为Word
   * **下载地址**：[https://www.libreoffice.org/](https://www.libreoffice.org/)

## 使用方法 🚀

1. **配置YAML**：打开`config.yaml`，将`data_path`指向本目录
2. **运行项目**：执行`python -m trans`，程序会：
   * 优先使用LaTeX编译生成PDF
   * 然后尝试用LibreOffice转为Word
   * 若上述失败，自动调用`pdf2docx`库转换
3. **手动转换**：若自动转换失败，可手动将生成的PDF转为Word

## 引用说明 📝

如果你在研究中参考了此论文，请引用上述原始出处。