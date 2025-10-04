import re

# Command adhesion pattern: ensure commands immediately followed by CJK are safe
command_adhesion_pattern = re.compile(r'([a-zA-Z\d_-]*)(?=[\u4e00-\u9fa5\u3000-\u303f\uFF00-\uFFEF])')


def fix_command_adhesion(text: str) -> str:
    """
    在 LaTeX 命令后插入 {} 以避免与后续中文粘连导致的问题：
    e.g., "基于\modelname的数据" -> "基于\modelname{}的数据"
    """
    return command_adhesion_pattern.sub(r'\1{}', text)


def fix_hyphen_spacing(text: str) -> str:
    """
    修复 LLM 可能引入的连字符空格问题（例如 "gpt - 4o" -> "gpt-4o"）。
    保守替换：把连续空格两侧是连字符的情形处理掉。
    """
    return re.sub(r'\s*-\s*', '-', text)


def remove_llm_artifacts(text: str, original_text: str = "") -> str:
    """
    移除 LLM 生成中常见的非 LaTeX 内容（如多余的代码块标记、重复的 \end{document} 等）。
    original_text 用于判断哪些是 LLM 新增的 artifacts。
    """
    if "`" not in original_text:
        text = text.replace("`", "")
    # 只在原始文本没有 \end{document} 的情况下，删除 LLM 额外插入的 \end{document}
    if "\end{document}" in text and "\end{document}" not in original_text:
        # 只删除多于一个的，保留一个（如果需要）
        parts = text.split("\end{document}")
        if len(parts) > 1:
            text = parts[0] + "\end{document}" + "".join(parts[1:]).replace("\end{document}", "")
    return text


def fix_llm_latex_artifacts(translated_text: str, original_text: str = "") -> str:
    """
    更稳健的 LaTeX 翻译后修复函数（保守原则）。
    - 保留 \begin{env}[opts] 的方括号选项（避免拆成单独一行）
    - 删除 equation 内被插入的 [ ]（保留内部公式/label）
    - 合并紧邻重复的 \begin 或 \end
    - 避免盲目删除 \end{document}（只在确实是 LLM 插入多余项时处理）
    """
    text = translated_text

    # Remove accidental Markdown fences if not present originally
    if "```" not in original_text:
        text = text.replace("```", "")

    # Clean equation: remove \[ \] inside equation environment but keep its content
    def _clean_equation(match):
        begin = match.group(1)
        content = match.group(2)
        end = match.group(3)
        # 移除 \[ 和 \] 标记
        content = content.replace('\\[', '').replace('\\]', '')
        # 将 \_ 替换为 _
        content = content.replace('\\_', '')
        return f"{begin}{content}{end}"

    text = re.sub(r'(\\begin\{equation\*?\})(.*?)(\\end\{equation\*?\})', _clean_equation, text, flags=re.DOTALL)

    # Conservative merge: if \begin{env}[opts] followed by \begin{env} (duplicate), remove duplicate
    text = re.sub(r'(\\begin\{([a-zA-Z*]+)\}(?:\[[^\]]*\])?)\s*\\begin\{\2\}(?:\[[^\]]*\])?', r'\1', text)
    text = re.sub(r'(\\begin\{([a-zA-Z*]+)\})\s*\\begin\{\2\}(\[[^\]]*\])', r'\1\3', text)

    # Prevent split of \begin{env} and its [opts] onto separate lines:
    # Merge a line with only [opts] into previous begin line if any
    lines = text.splitlines()
    new_lines = []
    for line in lines:
        if re.fullmatch(r'\s*\[[^\]]+\]\s*', line) and new_lines:
            # append to previous line
            new_lines[-1] = new_lines[-1].rstrip() + line.strip()
        else:
            new_lines.append(line)
    text = "\n".join(new_lines)

    # Remove immediate duplicate \end{env}
    text = re.sub(r'(\\end\{([a-zA-Z*]+)\})\s*\\end\{\2\}', r'\1', text)

    # Conservative \end{document} cleanup: if more than 1 occurrence, keep only first
    if text.count(r'\end{document}') > 1:
        first_idx = text.find(r'\end{document}')
        text = text[:first_idx + len(r'\end{document}')] + "\n" + text[first_idx + len(r'\end{document}'):].replace(
            r'\end{document}', '')

    # Avoid accidental single-char prefix characters before \begin (like lines starting with '+ \begin')
    text = re.sub(r'(?m)^[ \t]*[+\-*/=]{1,2}\s*(\\begin\{)', r'\1', text)

    # 最后处理所有数学环境中的 \_
    def _replace_underscore_in_math(match):
        content = match.group(0)
        return content.replace('\\_', '_')

    # 匹配各种数学环境
    # 匹配各种数学环境，包括行内和行间数学模式
    math_patterns = [
        r'\\begin\{equation\}.*?\\end\{equation\}',
        r'\\begin\{align\}.*?\\end\{align\}',
        r'\\begin\{gather\}.*?\\end\{gather\}',
        r'\\begin\{equation\*\}.*?\\end\{equation\*\}',
        r'\\begin\{align\*\}.*?\\end\{align\*\}',
        r'\\begin\{gather\*\}.*?\\end\{gather\*\}',
        r'\\begin\{multline\}.*?\\end\{multline\}',
        r'\\begin\{multline\*\}.*?\\end\{multline\*\}',
        r'\\begin\{flalign\}.*?\\end\{flalign\}',
        r'\\begin\{flalign\*\}.*?\\end\{flalign\*\}',
        r'\$\$.*?\$\$',
        r'\$.*?\$',
        r'\\\[.*?\\\]'
    ]

    def remove_empty_braces_smart(text):
        # 找到所有特殊环境的位置
        special_envs = [
            r'\\begin\{tikzpicture\}.*?\\end\{tikzpicture\}',
            r'\\begin\{verbatim\}.*?\\end\{verbatim\}',
            r'\\begin\{lstlisting\}.*?\\end\{lstlisting\}',
            r'\\begin\{minted\}.*?\\end\{minted\}',
            r'\\begin\{alltt\}.*?\\end\{alltt\}'
        ]

        # 保存特殊环境内容
        saved_envs = {}
        for i, env_pattern in enumerate(special_envs):
            matches = re.findall(env_pattern, text, flags=re.DOTALL)
            for j, match in enumerate(matches):
                placeholder = f'<<SPECIAL_ENV_{i}_{j}>>'
                saved_envs[placeholder] = match
                text = text.replace(match, placeholder, 1)

        # 在正文区域移除空的 {}
        text = re.sub(r'(?<!\\)\{\}', '', text)

        # 恢复特殊环境
        for placeholder, env_content in saved_envs.items():
            text = text.replace(placeholder, env_content)

        return text

    # 使用智能移除方法替代原来的简单替换
    text = remove_empty_braces_smart(text)

    for pattern in math_patterns:
        text = re.sub(pattern, _replace_underscore_in_math, text, flags=re.DOTALL)

    # 为 \begin{} 命令添加换行 - 如果前面有字符则在前面添加换行
    text = re.sub(r'(?<=\S)(\s*)(\\begin\{)', r'\n\2', text)

    # 为 \end{} 命令添加换行 - 如果前面有字符则在前面添加换行
    text = re.sub(r'(?<=\S)(\s*)(\\end\{)', r'\n\2', text)
    return text

