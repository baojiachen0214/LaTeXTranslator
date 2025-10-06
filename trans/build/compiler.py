import subprocess
import shutil
import re
from pathlib import Path
from trans.utils.logger import logger


def fix_mismatched_delimiters(tex: str) -> str:
    """
    检测并修复以下不匹配问题（仅在安全区域）：
      - \begin{env} / \end{env} 配对（支持嵌套）
      - { / } 配对（仅在非 math/verbatim/verb 区域）
      - $ / $$ 配对（仅在非 math/verbatim/verb 区域）

    策略：
      - 使用状态机跳过 verbatim、math、verb 区域
      - 在普通文本区域：
          * 用栈记录 \begin{...}，遇到 \end{...} 时检查是否匹配
          * 用计数器跟踪 { 和 }（不能为负）
          * 用状态跟踪 $ 和 $$（不能嵌套）
      - 修复方式：删除多余的符号（保守策略）
    """
    import re

    # 输出字符列表（用于删除）
    out = []
    i = 0
    n = len(tex)

    # === 状态标志 ===
    in_verbatim_env = False
    verbatim_env_name = None
    in_verb = False
    verb_delim = None
    in_inline_math = False   # $
    in_display_math = False  # $$

    # === 栈和计数器（仅在普通文本区域有效）===
    env_stack = []      # 存储环境名，用于 \begin/\end 配对
    brace_count = 0     # { +1, } -1，不能为负
    dollar_state = 0    # 0: outside, 1: in $, 2: in $$

    verbatim_envs = {"verbatim", "lstlisting", "minted"}

    while i < n:
        ch = tex[i]

        # ========== 1. 检测 \begin{...} / \end{...} ==========
        # 注意：即使在 math/verb 中，\begin 通常无效，但为安全起见，我们只在非 verbatim 中处理
        if not (in_verbatim_env or in_verb):
            if tex.startswith(r'\begin{', i):
                m = re.match(r'\\begin\{([a-zA-Z*]+)\}', tex[i:])
                if m:
                    env_name = m.group(1)
                    full_match = m.group(0)
                    # 在普通区域：压入栈
                    env_stack.append(env_name)
                    out.append(full_match)
                    i += len(full_match)
                    # 检查是否进入 verbatim 环境
                    if env_name in verbatim_envs:
                        in_verbatim_env = True
                        verbatim_env_name = env_name
                    continue

            if tex.startswith(r'\end{', i):
                m = re.match(r'\\end\{([a-zA-Z*]+)\}', tex[i:])
                if m:
                    env_name = m.group(1)
                    full_match = m.group(0)
                    if env_stack and env_stack[-1] == env_name:
                        # 正常匹配
                        env_stack.pop()
                        out.append(full_match)
                        i += len(full_match)
                        # 检查是否退出 verbatim 环境
                        if in_verbatim_env and env_name == verbatim_env_name:
                            in_verbatim_env = False
                            verbatim_env_name = None
                    else:
                        # 多余的 \end{...}：删除（不添加到 out）
                        logger.warning(f"Detected unmatched \\end{{{env_name}}}, removing.")
                        i += len(full_match)
                    continue

        # ========== 2. 处理 verbatim 环境内部 ==========
        if in_verbatim_env:
            if tex.startswith(r'\end{', i):
                m = re.match(r'\\end\{([a-zA-Z*]+)\}', tex[i:])
                if m and m.group(1) == verbatim_env_name:
                    out.append(m.group(0))
                    i += len(m.group(0))
                    in_verbatim_env = False
                    verbatim_env_name = None
                    continue
            out.append(ch)
            i += 1
            continue

        # ========== 3. 处理 \verb 命令 ==========
        if not in_verb and tex.startswith(r'\verb', i):
            j = i + len(r'\verb')
            if j < n:
                if tex[j] == '*':
                    j += 1
                if j < n:
                    delim = tex[j]
                    in_verb = True
                    verb_delim = delim
                    out.append(tex[i:j+1])
                    i = j + 1
                    continue

        if in_verb:
            if ch == verb_delim:
                out.append(ch)
                in_verb = False
                verb_delim = None
                i += 1
            else:
                out.append(ch)
                i += 1
            continue

        # ========== 4. 处理数学模式（$ 和 $$）==========
        # 注意：我们在此处更新数学状态，并决定是否跳过配对检查
        current_in_math = in_inline_math or in_display_math

        if not current_in_math:
            # 检查 $$ 开始
            if tex.startswith('$$', i):
                if dollar_state == 0:
                    in_display_math = True
                    dollar_state = 2
                    out.append('$$')
                    i += 2
                    continue
                else:
                    # 多余的 $$：删除
                    logger.warning("Detected unmatched $$, removing.")
                    i += 2
                    continue
            # 检查 $ 开始
            elif ch == '$':
                if dollar_state == 0:
                    in_inline_math = True
                    dollar_state = 1
                    out.append('$')
                    i += 1
                    continue
                else:
                    # 多余的 $：删除
                    logger.warning("Detected unmatched $, removing.")
                    i += 1
                    continue
        else:
            # 在数学模式中
            if in_display_math and tex.startswith('$$', i):
                in_display_math = False
                dollar_state = 0
                out.append('$$')
                i += 2
                continue
            elif in_inline_math and ch == '$':
                in_inline_math = False
                dollar_state = 0
                out.append('$')
                i += 1
                continue
            else:
                # 数学模式内部：直接复制，不检查 {}/$
                out.append(ch)
                i += 1
                continue

        # ========== 5. 普通文本区域：处理 { 和 } ==========
        # 此时：不在 verbatim, 不在 verb, 不在 math
        if ch == '{':
            brace_count += 1
            out.append(ch)
            i += 1
        elif ch == '}':
            if brace_count > 0:
                brace_count -= 1
                out.append(ch)
                i += 1
            else:
                # 多余的 }：删除
                logger.warning("Detected unmatched }, removing.")
                i += 1
        else:
            # 其他字符
            out.append(ch)
            i += 1

    # ========== 6. 文件末尾：处理未闭合的符号 ==========
    # 删除未闭合的 {
    if brace_count > 0:
        logger.warning(f"Detected {brace_count} unmatched {{ at end, removing.")
        # 从末尾删除 brace_count 个 '{'
        temp_out = out[:]
        count = brace_count
        new_out = []
        for char in reversed(temp_out):
            if char == '{' and count > 0:
                count -= 1
                continue
            new_out.append(char)
        out = list(reversed(new_out))

    # 删除未闭合的 \begin{...}
    if env_stack:
        logger.warning(f"Detected unmatched \\begin{{{', '.join(env_stack)}}} at end, removing.")
        # 简单策略：由于我们无法精确定位 \begin 的位置，这里不删除（风险高）
        # 更安全的做法是保留，让 LaTeX 报错，或在日志中警告
        # 此处选择：不删除 \begin，只记录警告（避免破坏结构）
        pass

    # 删除未闭合的 $
    if dollar_state != 0:
        logger.warning("Detected unmatched $ or $$ at end, removing.")
        # 已经在状态机中处理了内部，末尾的 $ 会被忽略（因为不在 out 中）
        # 所以无需额外操作

    return ''.join(out)


def escape_underscores_skip_keys(tex: str) -> str:
    """
    Escape underscores except inside:
      - math modes, verbatim/lstlisting/minted, \verb...
      - arguments of commands that should not be altered (cite/label/ref/addbibresource/includegraphics/url/...).
    """
    # Split the document into preamble and body
    doc_begin_match = re.search(r'\\begin\s*{\s*document\s*}', tex)
    doc_end_match = re.search(r'\\end\s*{\s*document\s*}', tex)

    # Helper function to process a chunk (body, preamble, or postamble)
    def _process_chunk(chunk: str, is_preamble_or_postamble: bool = False) -> str:
        skip_cmds = {
            'cite', 'citet', 'citep', 'citeyear', 'bibitem', 'label', 'ref',
            'pageref', 'addbibresource', 'bibliography', 'includegraphics',
            'url', 'href', 'path', 'lstinputlisting'
        }

        # Commands that should have underscores escaped in their arguments
        process_cmds = {
            'texttt', 'textbf', 'textit', 'emph'
        }

        out = []
        i = 0
        n = len(chunk)

        # reuse states from your original code
        verbatim_envs = {"verbatim", "lstlisting", "minted"}
        in_inline_math = False
        in_display_math = False
        in_bracket_math = False
        in_verbatim_env = False
        verbatim_env_name = None
        in_verb = False
        verb_delim = None

        while i < n:
            ch = chunk[i]

            # begin{env}
            if not (in_verbatim_env or in_verb) and chunk.startswith(r'\begin{', i):
                m = re.match(r'\\begin\{([a-zA-Z*]+)\}', chunk[i:])
                if m:
                    env = m.group(1)
                    out.append(m.group(0))
                    i += len(m.group(0))
                    if env in verbatim_envs:
                        in_verbatim_env = True
                        verbatim_env_name = env
                    continue

            # end{env}
            if in_verbatim_env and chunk.startswith(r'\end{', i):
                m = re.match(r'\\end\{([a-zA-Z*]+)\}', chunk[i:])
                if m:
                    env = m.group(1)
                    out.append(m.group(0))
                    i += len(m.group(0))
                    if env == verbatim_env_name:
                        in_verbatim_env = False
                        verbatim_env_name = None
                    continue

            if in_verbatim_env:
                out.append(ch)
                i += 1
                continue

            # \verb handling
            if not in_verb and chunk.startswith(r'\verb', i):
                j = i + len(r'\verb')
                if j < n:
                    if chunk[j] == '*':
                        j += 1
                    if j < n:
                        delim = chunk[j]
                        in_verb = True
                        verb_delim = delim
                        out.append(chunk[i:j + 1])
                        i = j + 1
                        continue
            if in_verb:
                if ch == verb_delim:
                    out.append(ch)
                    in_verb = False
                    verb_delim = None
                    i += 1
                    continue
                else:
                    out.append(ch)
                    i += 1
                    continue

            # math modes (same logic)
            if not (in_inline_math or in_display_math or in_bracket_math):
                if chunk.startswith('$$', i):
                    in_display_math = True
                    out.append('$$')
                    i += 2
                    continue
                if chunk.startswith('\\[', i):
                    in_bracket_math = True
                    out.append('\\[')
                    i += 2
                    continue
                if ch == '$':
                    in_inline_math = True
                    out.append(ch)
                    i += 1
                    continue
            else:
                if in_display_math and chunk.startswith('$$', i):
                    in_display_math = False
                    out.append('$$')
                    i += 2
                    continue
                if in_bracket_math and chunk.startswith('\\]', i):
                    in_bracket_math = False
                    out.append('\\]')
                    i += 2
                    continue
                if in_inline_math and ch == '$':
                    in_inline_math = False
                    out.append(ch)
                    i += 1
                    continue
                out.append(ch)
                i += 1
                continue

            # If backslash command with { ... } argument, maybe skip argument if command in skip_cmds
            if ch == '\\':
                # capture command name
                j = i + 1
                cmd_name = []
                while j < n and re.match(r'[A-Za-z]+', chunk[j]):
                    cmd_name.append(chunk[j])
                    j += 1
                cmd_name = ''.join(cmd_name)
                # Append command name
                out.append('\\' + cmd_name)
                i = j
                # If next non-space char is {, we have an argument; decide whether to skip it
                # preserve spacing
                while i < n and chunk[i].isspace():
                    out.append(chunk[i])
                    i += 1
                if i < n and chunk[i] == '{':
                    # find matching brace (simple stack)
                    brace_start = i
                    depth = 0
                    k = i
                    while k < n:
                        if chunk[k] == '{':
                            depth += 1
                        elif chunk[k] == '}':
                            depth -= 1
                            if depth == 0:
                                break
                        k += 1
                    # k now at matching }
                    if k < n:
                        arg = chunk[brace_start:k + 1]
                        if cmd_name in skip_cmds:
                            # copy raw argument
                            out.append(arg)
                        elif cmd_name in process_cmds:
                            # process argument: replace unescaped '_' -> '\_'
                            processed_arg = []
                            ii = 0
                            while ii < len(arg):
                                c = arg[ii]
                                if c == '\\':  # keep escape sequences as-is
                                    if ii + 1 < len(arg):
                                        processed_arg.append(c)
                                        processed_arg.append(arg[ii + 1])
                                        ii += 2
                                        continue
                                    else:
                                        processed_arg.append(c)
                                        ii += 1
                                        continue
                                if c == '_':
                                    processed_arg.append(r'\_')
                                    ii += 1
                                    continue
                                processed_arg.append(c)
                                ii += 1
                            out.append(''.join(processed_arg))
                        else:
                            # For all other commands, also escape underscores in arguments
                            processed_arg = []
                            ii = 0
                            while ii < len(arg):
                                c = arg[ii]
                                if c == '\\':  # keep escape sequences as-is
                                    if ii + 1 < len(arg):
                                        processed_arg.append(c)
                                        processed_arg.append(arg[ii + 1])
                                        ii += 2
                                        continue
                                    else:
                                        processed_arg.append(c)
                                        ii += 1
                                        continue
                                if c == '_':
                                    processed_arg.append(r'\_')
                                    ii += 1
                                    continue
                                processed_arg.append(c)
                                ii += 1
                            out.append(''.join(processed_arg))
                        i = k + 1
                        continue
                    else:
                        # unmatched brace -> just append rest
                        out.append(chunk[i:])
                        break
                else:
                    # no brace-arg, continue loop
                    continue

            # default underscore handling outside protected contexts
            if ch == '_':
                out.append(r'\_')
                i += 1
                continue

            out.append(ch)
            i += 1

        return ''.join(out)

    if doc_begin_match and doc_end_match:
        preamble = tex[:doc_begin_match.end()]
        body = tex[doc_begin_match.end():doc_end_match.start()]
        postamble = tex[doc_end_match.start():]

        # Process ALL parts: preamble, body, postamble
        processed_preamble = _process_chunk(preamble, is_preamble_or_postamble=True)
        processed_body = _process_chunk(body)
        processed_postamble = _process_chunk(postamble, is_preamble_or_postamble=True)

        return processed_preamble + processed_body + processed_postamble
    else:
        # If document structure not found, process the entire document
        return _process_chunk(tex)


# --- Added: Replace documentclass with ctexart (preserve options) ---
def replace_documentclass(tex: str) -> str:
    """
    Replace any \\documentclass[...]{...} with \\documentclass[...]{ctexart}
    If there are no square bracket options, only replace the class name part.
    """

    def _repl(m):
        # Extract options group (could be None if no options)
        opts = m.group(1) or ''
        # Keep original options unchanged
        return f"\\documentclass{opts}{{ctexart}}"

    # Compile regex pattern to match documentclass with optional options
    pattern = re.compile(r'\\documentclass(\[[^\]]*\])?\{[^\}]*\}')
    # Replace only the first occurrence of documentclass
    return pattern.sub(_repl, tex, count=1)  # Only replace the first documentclass


def fix_citation_issues(tex: str) -> str:
    """
    trans \cite{\cite{...}} to \cite{...}
    """
    tex = re.sub(r'\\ref\{sec:\\ref\{([^}]*)\}\}', r'\\ref{\1}', tex)
    tex = re.sub(r'\\cite\{\\cite\{([^}]*)\}\}', r'\\cite{\1}', tex)
    return tex


def fix_tikz_issues(tex: str) -> str:
    # 处理 \newcommand{\mainpicturedata}{...} 中的内容
    def process_mainpicturedata(match):
        command_def = match.group(0)
        content = match.group(1)
        
        # 处理 .s++ 问题，避免影响包含类似模式的引用
        content = re.sub(r'(\.s\s*\+\+)(?![^}]*\\cite)', r'.controls \1', content)
        
        # 修复 TikZ 中的 \node 命令问题
        def fix_node_command(node_match):
            node_content = node_match.group(0)
            # 检查是否包含引用，若包含则不处理
            if r'\cite' in node_content:
                return node_content

            semicolon_pos = node_content.find(';')
            if semicolon_pos != -1:
                before_semicolon = node_content[:semicolon_pos]
                if '{}' not in before_semicolon:
                    return node_content[:semicolon_pos] + ' {}' + node_content[semicolon_pos:]
            return node_content

        # 处理 node 命令
        content = re.sub(r'\\node[^;]*;', fix_node_command, content)
        
        # 重新构造命令定义
        return f'\\newcommand{{\\mainpicturedata}}{{{content}}}'
    
    # 匹配 \newcommand{\mainpicturedata}{...} 并处理其中的内容
    mainpicturedata_pattern = re.compile(r'\\newcommand\{\\mainpicturedata\}\{(.*?)\}', re.DOTALL)
    tex = mainpicturedata_pattern.sub(process_mainpicturedata, tex)
    
    # 匹配整个 tikzpicture 环境
    tikz_pattern = re.compile(r'\\begin\{tikzpicture\}(.*?)\\end\{tikzpicture\}', re.DOTALL)

    def process_tikz_content(match):
        tikz_content = match.group(1)

        # # 修复 \\mainpicturedata 命令问题
        # tikz_content = re.sub(r'\\mainpicturedata', r'%\\mainpicturedata', tikz_content)

        # 处理 .s++ 问题，避免影响包含类似模式的引用
        tikz_content = re.sub(r'(\.s\s*\+\+)(?![^}]*\\cite)', r'.controls \1', tikz_content)

        # 修复 TikZ 中的 \node 命令问题
        def fix_node_command(node_match):
            node_content = node_match.group(0)
            # 检查是否包含引用，若包含则不处理
            if r'\cite' in node_content:
                return node_content

            semicolon_pos = node_content.find(';')
            if semicolon_pos != -1:
                before_semicolon = node_content[:semicolon_pos]
                if '{}' not in before_semicolon:
                    return node_content[:semicolon_pos] + ' {}' + node_content[semicolon_pos:]
            return node_content

        # 只在 tikz 环境内处理 node 命令
        tikz_content = re.sub(r'\\node[^;]*;', fix_node_command, tikz_content)
        return f'\\begin{{tikzpicture}}{tikz_content}\\end{{tikzpicture}}'

    # 只对 tikzpicture 环境内部的内容进行处理
    fixed_tex = tikz_pattern.sub(process_tikz_content, tex)
    return fixed_tex


def fix_special_chars(tex: str) -> str:
    # 定义需要处理的环境列表（表格和绘图相关）
    environments = [
        'tabular', 'tabular*', 'tabu', 'array',  # 表格环境
        'tikzpicture', 'pgfpicture',  # TikZ绘图环境
        'figure', 'table',  # 浮动体环境
        'tabularx', 'tabulary', 'longtable'  # 其他表格环境
    ]

    # 构建匹配这些环境的正则表达式（修正转义问题）
    # 正确处理带星号的环境，如tabular*、figure*等
    env_patterns = [
        fr'\\begin\{{{env}(?:\*)?\}}.*?\\end\{{{env}(?:\*)?\}}'
        for env in environments
    ]
    combined_pattern = re.compile('|'.join(env_patterns), re.DOTALL)

    def process_environment(match):
        content = match.group(0)

        # 保护引用内容不被处理
        cite_pattern = re.compile(r'\\cite(?:\w+)?\{[^\}]+\}')
        protected_cites = []

        def protect_cite(m):
            cite = m.group(0)
            # 替换引用中的特殊字符为临时标记
            protected = cite.replace('{@', '___CITE_AT_OPEN___') \
                .replace('@}', '___CITE_AT_CLOSE___') \
                .replace('.)', '___CITE_DOT_PAREN___')
            protected_cites.append(protected)
            return f'___PROTECTED_CITE_{len(protected_cites) - 1}___'

        # 先保护所有引用
        content = cite_pattern.sub(protect_cite, content)

        # 只在环境内部进行特殊字符替换
        content = content.replace('{@', '{@{}')
        content = content.replace('@}', '@{}}')
        content = content.replace('.)', '..')

        # 恢复受保护的引用
        for i, cite in enumerate(protected_cites):
            restored_cite = cite.replace('___CITE_AT_OPEN___', '{@') \
                .replace('___CITE_AT_CLOSE___', '@}') \
                .replace('___CITE_DOT_PAREN___', '.)')
            content = content.replace(f'___PROTECTED_CITE_{i}___', restored_cite)

        return content

    # 只对指定环境内的内容进行处理
    fixed_tex = combined_pattern.sub(process_environment, tex)
    return fixed_tex


def comment_out_placeholder_lines(tex: str) -> str:
    """
    注释掉单独一行的占位符，如 __TGTEX_EQU_...
    这是一个简单粗暴的修复方法，防止占位符导致编译错误
    """
    lines = tex.split('\n')
    processed_lines = []
    
    placeholder_pattern = re.compile(r'^\s*__TGTEX_[A-Z0-9_]+__\s*$')
    
    for line in lines:
        if placeholder_pattern.match(line):
            # 注释掉整行
            processed_lines.append('% ' + line)
        else:
            processed_lines.append(line)
            
    return '\n'.join(processed_lines)


def fix_underline_issues(tex: str) -> str:
    # 数学环境模式 - 包含更多常见的数学环境
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
        # r'\$\$.*?\$\$',  # 无编号公式
        # r'\$.*?\$',  # 行内公式
        # r'\\\[.*?\\\]'  # 另一种无编号公式
    ]

    # 使用非贪婪匹配并添加适当的边界，避免跨环境匹配
    combined_pattern = re.compile('|'.join(f'({p})' for p in math_patterns), re.DOTALL)

    def replace_underscore(match):
        # 找到第一个非None的匹配组
        content = next(g for g in match.groups() if g is not None)
        # 只替换数学环境中的\_为_，不影响其他部分
        return content.replace(r'\_', '_')

    # 执行替换
    fixed_tex = combined_pattern.sub(replace_underscore, tex)

    return fixed_tex


def add_title_spacing(tex: str) -> str:
    """
    强制添加titlesec包和标题间距设置到导言区
    """
    # 查找\begin{document}的位置
    doc_begin_match = re.search(r'\\begin\s*{\s*document\s*}', tex)
    if not doc_begin_match:
        # 如果没有找到\begin{document}，在文件末尾导言区添加（在\documentclass之后）
        docclass_match = re.search(r'\\documentclass(?:\[.*?\])?\{.*?\}', tex)
        if docclass_match:
            docclass_end = docclass_match.end()
            preamble_addition = "\n\\usepackage{titlesec}\n" + \
                               "\\titlespacing*{\\section}{0pt}{12pt}{8pt}\n" + \
                               "\\titlespacing*{\\subsection}{0pt}{10pt}{6pt}\n" + \
                               "\\titlespacing*{\\subsubsection}{0pt}{8pt}{4pt}\n" + \
                               "\\setlength{\\parskip}{0.5em}\n" + \
                               "\\setlength{\\parsep}{0.5em}\n"
            return tex[:docclass_end] + preamble_addition + tex[docclass_end:]
        else:
            # 如果连\documentclass都找不到，添加到文件开头
            preamble_addition = "\\usepackage{titlesec}\n" + \
                               "\\titlespacing*{\\section}{0pt}{12pt}{8pt}\n" + \
                               "\\titlespacing*{\\subsection}{0pt}{10pt}{6pt}\n" + \
                               "\\titlespacing*{\\subsubsection}{0pt}{8pt}{4pt}\n" + \
                               "\\setlength{\\parskip}{0.5em}\n" + \
                               "\\setlength{\\parsep}{0.5em}\n"
            return preamble_addition + tex
    
    # 在\begin{document}前添加包引入和设置
    insert_pos = doc_begin_match.start()
    
    # 检查是否已经存在titlesec包，避免重复添加
    if '\\usepackage{titlesec}' in tex[:insert_pos]:
        # 如果已经存在titlesec包，只添加间距设置
        preamble_addition = "\n% 标题间距设置\n" + \
                           "\\titlespacing*{\\section}{0pt}{12pt}{8pt}\n" + \
                           "\\titlespacing*{\\subsection}{0pt}{10pt}{6pt}\n" + \
                           "\\titlespacing*{\\subsubsection}{0pt}{8pt}{4pt}\n" + \
                           "\\setlength{\\parskip}{0.5em}\n" + \
                           "\\setlength{\\parsep}{0.5em}\n"
    else:
        # 添加包引入和间距设置
        preamble_addition = "\n\\usepackage{titlesec}\n" + \
                           "\\titlespacing*{\\section}{0pt}{12pt}{8pt}\n" + \
                           "\\titlespacing*{\\subsection}{0pt}{10pt}{6pt}\n" + \
                           "\\titlespacing*{\\subsubsection}{0pt}{8pt}{4pt}\n" + \
                           "\\setlength{\\parskip}{0.5em}\n" + \
                           "\\setlength{\\parsep}{0.5em}\n"
    
    return tex[:insert_pos] + preamble_addition + tex[insert_pos:]


def generate_pandoc_compatibility_preamble(tex_content: str) -> str:
    commands = set()

    # ✅ 正确：raw string + 双反斜杠（因为正则里 \ 本身要转义）
    newcmd_pattern = r'\\newcommand\s*\{\\([a-zA-Z]+)\}'
    for match in re.finditer(newcmd_pattern, tex_content):
        commands.add(match.group(1))

    def_pattern = r'\\def\\([a-zA-Z]+)\s*\{'
    for match in re.finditer(def_pattern, tex_content):
        commands.add(match.group(1))

    preamble_lines = ["% ===== Auto-generated Pandoc compatibility layer ====="]
    for cmd in sorted(commands):
        if cmd in {'naturals', 'N', 'reals', 'R', 'complex', 'C'}:
            mapping = {
                'naturals': r'\mathbb{N}',  # ✅ raw string
                'N': r'\mathbb{N}',
                'reals': r'\mathbb{R}',
                'R': r'\mathbb{R}',
                'complex': r'\mathbb{C}',
                'C': r'\mathbb{C}',
            }
            fallback = mapping.get(cmd, r'\text{??}')
            # ✅ 用双反斜杠或 raw string 拼接
            line = f"\\providecommand{{\\{cmd}}}{{{fallback}}}"
            preamble_lines.append(line)
        else:
            # Generic fallback: treat as text
            line = f"\\providecommand{{\\{cmd}}}{{\\texttt{{\\\\{cmd}}}}}"
            preamble_lines.append(line)

    preamble_lines.append("% ===== End compatibility layer =====\n")
    return "\n".join(preamble_lines)


def pdf_to_docx(pdf_path: Path, docx_path: Path) -> bool:
    """Convert PDF to DOCX using LibreOffice (fallback method)."""
    try:
        # Ensure output dir exists
        docx_path.parent.mkdir(parents=True, exist_ok=True)

        result = subprocess.run(
            [
                'soffice',
                '--headless',
                '--convert-to', 'docx',
                '--outdir', str(docx_path.parent),
                str(pdf_path)
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60  # 1 minute max
        )

        # LibreOffice outputs file as <basename>.docx in outdir
        expected_output = docx_path.parent / f"{pdf_path.stem}.docx"
        if expected_output.exists():
            if expected_output != docx_path:
                expected_output.replace(docx_path)  # rename to desired name
            return True
        else:
            logger.warning("LibreOffice conversion succeeded but output not found: %s", expected_output)
            return False

    except subprocess.TimeoutExpired:
        logger.warning("LibreOffice conversion timed out.")
        return False
    except FileNotFoundError:
        logger.warning("LibreOffice (soffice) not found. Install LibreOffice for PDF→DOCX fallback.")
        return False
    except Exception as e:
        logger.warning("LibreOffice conversion failed: %s", e)
        return False


# ==============================
# 1. Pandoc 兼容层生成
# ==============================
def generate_pandoc_compatibility_preamble(tex_content: str) -> str:
    """Generate \providecommand stubs for undefined LaTeX commands."""
    commands = set()

    # Match \newcommand{\name}...
    newcmd_pattern = r'\\newcommand\s*\{\\([a-zA-Z]+)\}'
    for match in re.finditer(newcmd_pattern, tex_content):
        commands.add(match.group(1))

    # Match \def\name{...
    def_pattern = r'\\def\\([a-zA-Z]+)\s*\{'
    for match in re.finditer(def_pattern, tex_content):
        commands.add(match.group(1))

    # Add common mathbb commands if referenced
    if r'\mathbb' in tex_content:
        if r'\naturals' in tex_content or r'\N' in tex_content:
            commands.update(['naturals', 'N'])
        if r'\reals' in tex_content or r'\R' in tex_content:
            commands.update(['reals', 'R'])
        if r'\complex' in tex_content or r'\C' in tex_content:
            commands.update(['complex', 'C'])

    preamble_lines = ["% ===== Auto-generated Pandoc compatibility layer ====="]
    for cmd in sorted(commands):
        if cmd in {'naturals', 'N', 'reals', 'R', 'complex', 'C'}:
            mapping = {
                'naturals': r'\mathbb{N}',
                'N': r'\mathbb{N}',
                'reals': r'\mathbb{R}',
                'R': r'\mathbb{R}',
                'complex': r'\mathbb{C}',
                'C': r'\mathbb{C}',
            }
            fallback = mapping.get(cmd, r'\text{??}')
            preamble_lines.append(f"\\providecommand{{\\{cmd}}}{{{fallback}}}")
        else:
            # Generic fallback: show command name in typewriter
            preamble_lines.append(f"\\providecommand{{\\{cmd}}}{{\\texttt{{\\\\{cmd}}}}}")

    preamble_lines.append("% ===== End compatibility layer =====\n")
    return "\n".join(preamble_lines)


# ==============================
# 2. LibreOffice 检测与转换
# ==============================
def is_libreoffice_available() -> bool:
    soffice_exe = shutil.which("soffice.exe")
    if not soffice_exe:
        return False

    # 创建临时用户配置目录（避免权限/中文路径问题）
    import tempfile
    user_profile = tempfile.mkdtemp(prefix="libreoffice_tmp_")

    try:
        result = subprocess.run(
            [
                soffice_exe,
                "-env:UserInstallation=file:///" + user_profile.replace("\\", "/"),
                "--headless",
                "--version"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=10
        )
        success = (result.returncode == 0 and "LibreOffice" in result.stdout)
        return success
    except:
        return False
    finally:
        # 可选：清理临时目录（或保留供调试）
        import shutil as sh
        try:
            sh.rmtree(user_profile, ignore_errors=True)
        except:
            pass


def convert_pdf_to_docx_with_libreoffice(pdf_path: Path, docx_path: Path) -> bool:
    # Find soffice.exe explicitly
    soffice_exe = shutil.which("soffice.exe") or shutil.which("soffice")
    if not soffice_exe:
        logger.debug("LibreOffice not found in PATH.")
        return False

    try:
        logger.info("🔄 Converting PDF→DOCX with LibreOffice...")
        docx_path.parent.mkdir(parents=True, exist_ok=True)

        # Use the full path we found
        result = subprocess.run(
            [
                soffice_exe,  # ✅ Use full path, not just "soffice"
                "--headless",
                "--convert-to", "docx",
                "--outdir", str(docx_path.parent),
                str(pdf_path)
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=60
        )

        expected_output = docx_path.parent / f"{pdf_path.stem}.docx"
        if expected_output.exists():
            if expected_output != docx_path:
                expected_output.replace(docx_path)
            logger.info("✅ LibreOffice conversion succeeded.")
            return True
        else:
            logger.warning("LibreOffice returned success but output not found.")
            return False

    except Exception as e:
        logger.warning("LibreOffice conversion failed: %s", e)
        return False

# ==============================
# 3. pdf2docx 兜底转换
# ==============================
def convert_pdf_to_docx_with_pdf2docx(pdf_path: Path, docx_path: Path) -> bool:
    try:
        from pdf2docx import Converter
        logger.info("🔄 Converting PDF→DOCX with pdf2docx (pure Python)...")
        docx_path.parent.mkdir(parents=True, exist_ok=True)
        cv = Converter(str(pdf_path))
        cv.convert(str(docx_path), start=0, end=None)
        cv.close()
        return docx_path.exists()
    except ImportError:
        logger.debug("pdf2docx not installed.")
        return False
    except Exception as e:
        logger.debug("pdf2docx conversion error: %s", e)
        return False


# ==============================
# 4. 统一 PDF→DOCX 入口
# ==============================
def convert_pdf_to_docx(pdf_path: Path, docx_path: Path) -> bool:
    if not pdf_path.exists():
        logger.error("PDF not found for DOCX conversion: %s", pdf_path)
        return False
    if convert_pdf_to_docx_with_libreoffice(pdf_path, docx_path):
        return True
    if convert_pdf_to_docx_with_pdf2docx(pdf_path, docx_path):
        return True
    return False


# ==============================
# 5. Pandoc 转换（带兼容层）
# ==============================
def try_pandoc_conversion(
        original_project_dir: Path,
        main_tex: str,
        output_pdf_path: Path,
        docx_output_path: Path,
        wants_bib: bool
) -> bool:
    try:
        basename = Path(main_tex).stem
        with open(original_project_dir / main_tex, 'r', encoding='utf-8') as f:
            raw_tex = f.read()
        compat_preamble = generate_pandoc_compatibility_preamble(raw_tex)

        if "\\documentclass" in raw_tex:
            compat_tex = raw_tex.replace("\\documentclass", compat_preamble + "\\documentclass", 1)
        else:
            compat_tex = compat_preamble + raw_tex

        temp_tex = original_project_dir / f"{basename}_pandoc_compat.tex"
        with open(temp_tex, 'w', encoding='utf-8') as f:
            f.write(compat_tex)

        # Build pandoc command
        pandoc_cmd = [
            'pandoc', str(temp_tex), '-o', str(docx_output_path),
            '--standalone', '--wrap=none',
            '--from', 'latex+tex_math_dollars'
        ]
        bib_files = [f for f in original_project_dir.iterdir() if f.suffix == '.bib']
        if wants_bib and bib_files:
            pandoc_cmd.extend(['--citeproc', '--bibliography', str(bib_files[0])])

        res = subprocess.run(
            pandoc_cmd,
            cwd=original_project_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=30
        )
        success = (res.returncode == 0)
        if success:
            logger.info("✅ Pandoc conversion succeeded: %s", docx_output_path)
        else:
            logger.warning("⚠️ Pandoc failed. Output:\n%s", res.stdout)
        return success
    except FileNotFoundError:
        logger.warning("⚠️ Pandoc not found. Install pandoc (https://pandoc.org).")
        return False
    except Exception as e:
        logger.warning("⚠️ Pandoc conversion error: %s", e)
        return False
    finally:
        temp_tex = original_project_dir / f"{Path(main_tex).stem}_pandoc_compat.tex"
        temp_tex.unlink(missing_ok=True)


def compile_project(project_dir: Path, output_pdf_path: Path):
    """
    Compile a LaTeX project directory to generate a PDF file.

    Args:
        project_dir (Path): Path to the project directory containing .tex files
        output_pdf_path (Path): Path where the output PDF should be saved
    """
    # Find all .tex files in the project directory
    original_project_dir = Path(project_dir).resolve()
    candidate_tex_files = {}
    for file in project_dir.iterdir():
        if file.is_file() and file.suffix == '.tex':
            with open(file, 'r', encoding='utf-8') as f:
                candidate_tex_files[file.name] = f.read()

    # Check if any .tex files were found
    if not candidate_tex_files:
        logger.error("No .tex files found in the project directory.")
        return

    # Simple heuristic: file with \documentclass is likely the main file
    main_tex = None
    for name, content in candidate_tex_files.items():
        if "\\documentclass" in content:
            main_tex = name
            break

    # If no main .tex file with \documentclass is found, exit
    if not main_tex:
        logger.error("Could not find main .tex file with \\documentclass.")
        return

    logger.info(f"Found main tex file: {main_tex}. Post-processing (escape underscores, set ctexart)...")

    # Post-process the main tex content (escape underscores and replace documentclass)
    main_path = project_dir / main_tex
    with open(main_path, 'r', encoding='utf-8') as f:
        tex_content = f.read()

    tex_content = replace_documentclass(tex_content)
    tex_content = fix_mismatched_delimiters(tex_content)
    tex_content = escape_underscores_skip_keys(tex_content)
    tex_content = fix_special_chars(tex_content)
    tex_content = fix_citation_issues(tex_content)
    tex_content = fix_tikz_issues(tex_content)
    tex_content = fix_underline_issues(tex_content)
    # 添加标题间距设置
    tex_content = add_title_spacing(tex_content)
    # 添加占位符行注释处理
    tex_content = comment_out_placeholder_lines(tex_content)

    # Write back the processed file (overwrite the main .tex file)
    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(tex_content)

    logger.info("Post-processing complete. Starting compilation...")

    # Determine if bibtex is needed for bibliography processing
    bib_files = [f for f in project_dir.iterdir() if f.suffix == '.bib']
    need_bibtex = len(bib_files) > 0

    # Check if any tex file contains bibliography commands
    force_bibtex = False
    bibliography_commands = []
    for content in candidate_tex_files.values():
        # Look for \bibliography command and extract the bib file names
        bib_matches = re.findall(r'\\bibliography\{([^}]+)\}', content)
        if bib_matches:
            force_bibtex = True
            for match in bib_matches:
                # Split multiple bib files separated by commas
                bib_files_names = match.split(',')
                bibliography_commands.extend(bib_files_names)

    # If we found bibliography commands, check if the bib files exist in parent directories
    if force_bibtex and not need_bibtex:
        for bib_file_name in bibliography_commands:
            # Check in the current project directory
            if (project_dir / f"{bib_file_name.strip()}.bib").exists():
                need_bibtex = True
                break
            # Check in parent directories
            parent = project_dir.parent
            while parent != parent.parent:  # Stop at root directory
                if (parent / f"{bib_file_name.strip()}.bib").exists():
                    need_bibtex = True
                    break
                parent = parent.parent

    # --- put this where main_tex, project_dir, output_pdf_path, logger are in scope ---
    try:
        basename = Path(main_tex).stem
        project_dir = Path(project_dir)
        aux_file = project_dir / f"{basename}.aux"
        pdf_file = project_dir / f"{basename}.pdf"

        # ===== 彻底清理非关键缓存（保留 .aux, .bbl, .bcf, .blg）=====
        non_critical_exts = [
            '.log', '.toc', '.lof', '.lot', '.out', '.fls', '.fdb_latexmk',
            '.idx', '.ind', '.ilg', '.thm', '.vrb', '.nav', '.snm', '.tdo', '.run.xml'
        ]
        for ext in non_critical_exts:
            f = project_dir / f"{basename}{ext}"
            if f.exists():
                try:
                    f.unlink()
                    logger.debug("Removed non-critical file: %s", f)
                except Exception as e:
                    logger.warning("Failed to remove %s: %s", f, e)

        # ===== Step 1: First xelatex =====
        logger.info("→ Running initial xelatex (pass 1)...")
        subprocess.run(
            ['xelatex', '-interaction=nonstopmode', main_tex],
            cwd=project_dir,
            stdout=subprocess.DEVNULL,  # 减少日志噪音，除非调试
            stderr=subprocess.STDOUT
        )

        # ===== Detect bibliography =====
        tex_source = (project_dir / main_tex).read_text(encoding='utf-8', errors='ignore')
        uses_biblatex = ('\\usepackage{biblatex}' in tex_source) or ('\\addbibresource' in tex_source)
        has_bib = any(f.suffix == '.bib' for f in project_dir.iterdir())
        wants_bib = has_bib or ('\\bibliography' in tex_source) or uses_biblatex or force_bibtex

        if wants_bib:
            if uses_biblatex:
                logger.info("→ Running biber...")
                subprocess.run(['biber', basename], cwd=project_dir, stdout=subprocess.DEVNULL)
            else:
                logger.info("→ Running bibtex...")
                subprocess.run(['bibtex', basename], cwd=project_dir, stdout=subprocess.DEVNULL)

        # ===== Step 2+: Adaptive xelatex passes (up to 5 total, including first) =====
        max_passes = 5
        prev_aux_hash = None
        converged = False

        for pass_num in range(2, max_passes + 1):
            # 保存当前 .aux 内容的哈希（如果存在）
            current_aux_hash = None
            if aux_file.exists():
                import hashlib
                current_aux_hash = hashlib.md5(aux_file.read_bytes()).hexdigest()

            logger.info(f"→ Running xelatex (pass {pass_num})...")

            result = subprocess.run(
                ['xelatex', '-interaction=nonstopmode', main_tex],
                cwd=project_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.STDOUT
            )

            # 检查是否收敛：.aux 未变化
            if prev_aux_hash is not None and current_aux_hash == prev_aux_hash:
                logger.info("✅  .aux file unchanged → layout converged after pass %d.", pass_num - 1)
                converged = True
                break

            prev_aux_hash = current_aux_hash

            # 如果是最后一次，也退出
            if pass_num == max_passes:
                logger.warning("⚠️ Max passes (%d) reached without convergence.", max_passes)

        # ===== Final check =====
        if pdf_file.exists():
            output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(str(pdf_file), str(output_pdf_path))
            logger.info("✅  PDF compiled successfully: %s", output_pdf_path)
        else:
            logger.error("❌ Final PDF not found: %s", pdf_file)

    except Exception as e:
        logger.exception("💥 Unexpected error during compilation: %s", e)

    # ===== After PDF is successfully generated =====
    if output_pdf_path.exists():
        docx_output_path = output_pdf_path.with_suffix('.docx')
        pandoc_success = try_pandoc_conversion(
            original_project_dir=project_dir,
            main_tex=main_tex,  # 确保 main_tex 在作用域内
            output_pdf_path=output_pdf_path,
            docx_output_path=docx_output_path,
            wants_bib=wants_bib  # 确保 wants_bib 在作用域内
        )

        if not pandoc_success:
            logger.info("🔄 Falling back to PDF → DOCX conversion...")
            if convert_pdf_to_docx(output_pdf_path, docx_output_path):
                logger.info("✅  Fallback conversion succeeded: %s", docx_output_path)
            else:
                logger.warning("❌ All DOCX conversion methods failed. Only PDF is available.")
    else:
        logger.info("📄 Skipping DOCX conversion: PDF not generated.")