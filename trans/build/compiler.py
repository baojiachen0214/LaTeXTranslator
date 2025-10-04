import subprocess
import shutil
import re
from pathlib import Path
from trans.utils.logger import logger


# --- Added: Conservatively escape underscores (skip math/verbatim/\\verb etc.) ---
def escape_underscores(tex: str) -> str:
    """
    Escape unescaped underscores '_' in the main text to '\_', but preserve:
      - Already escaped '\_'
      - Underscores within math modes ($...$, $$...$$, \[...\], \(...\))
      - Content within verbatim / lstlisting / verb commands (do not process these regions)
    Use character-by-character scanning with state machine approach, as conservative as possible to avoid incorrect modifications.
    """
    # Output list to store processed characters
    out = []
    # Current index in the input string
    i = 0
    # Total length of input string
    n = len(tex)

    # Set of environment names: add common verbatim-like environments to skip list
    verbatim_envs = {"verbatim", "lstlisting", "minted"}
    # Math mode states
    in_inline_math = False  # Single $ math mode
    in_display_math = False  # Double $$ or \[ ... \] display math mode
    # Track \[ ... \] specifically
    in_bracket_math = False
    # Verbatim environment states
    in_verbatim_env = False
    verbatim_env_name = None
    # Verb command states
    in_verb = False
    verb_delim = None

    # Process each character in the input string
    while i < n:
        ch = tex[i]

        # --- Detect \begin{env} to enter verbatim environment ---
        if not (in_verbatim_env or in_verb) and tex.startswith(r'\begin{', i):
            # Match the pattern \begin{environment_name}
            m = re.match(r'\\begin\{([a-zA-Z*]+)\}', tex[i:])
            if m:
                env = m.group(1)
                # Add the matched begin command to output
                out.append(m.group(0))
                i += len(m.group(0))
                # If environment is in verbatim list, set verbatim state
                if env in verbatim_envs:
                    in_verbatim_env = True
                    verbatim_env_name = env
                continue

        # --- Detect \end{env} to exit verbatim environment ---
        if in_verbatim_env and tex.startswith(r'\end{', i):
            # Match the pattern \end{environment_name}
            m = re.match(r'\\end\{([a-zA-Z*]+)\}', tex[i:])
            if m:
                env = m.group(1)
                # Add the matched end command to output
                out.append(m.group(0))
                i += len(m.group(0))
                # If environment name matches current verbatim environment, exit verbatim state
                if env == verbatim_env_name:
                    in_verbatim_env = False
                    verbatim_env_name = None
                continue

        # --- If in verbatim environment, copy everything until \end{verbatim_env} ---
        if in_verbatim_env:
            # In verbatim mode, just copy all characters without processing
            out.append(ch)
            i += 1
            continue

        # --- Handle \verb command: \verb<delim> ... <delim> ---
        if not in_verb and tex.startswith(r'\verb', i):
            # Get position after \verb command
            j = i + len(r'\verb')
            if j < n:
                # Check if star is present (like \verb*)
                if tex[j] == '*':
                    j += 1
                if j < n:
                    # Get the delimiter character
                    delim = tex[j]
                    # Start verb mode
                    in_verb = True
                    verb_delim = delim
                    # Add \verb...delim to output (including the delimiter)
                    out.append(tex[i:j + 1])
                    i = j + 1
                    continue
        # If currently in verb command
        if in_verb:
            # Copy characters until matching delimiter is found (not escaped)
            if ch == verb_delim:
                # Found end delimiter, add it and exit verb mode
                out.append(ch)
                in_verb = False
                verb_delim = None
                i += 1
                continue
            else:
                # Still inside verb command, just copy character
                out.append(ch)
                i += 1
                continue

        # --- Handle math mode starts: $$, $, \[ or \] ---
        # Detect if not currently in any math mode
        if not (in_inline_math or in_display_math or in_bracket_math):
            # Detect $$ (display math mode)
            if tex.startswith('$$', i):
                in_display_math = True
                out.append('$$')
                i += 2
                continue
            # Detect \[ (display math mode)
            if tex.startswith('\\[', i):
                in_bracket_math = True
                out.append('\\[')
                i += 2
                continue
            # Detect single $ (inline math mode)
            if ch == '$':
                in_inline_math = True
                out.append(ch)
                i += 1
                continue
        else:
            # If in display math mode, look for $$ end
            if in_display_math and tex.startswith('$$', i):
                in_display_math = False
                out.append('$$')
                i += 2
                continue
            # If in bracket math mode, look for \] end
            if in_bracket_math and tex.startswith('\\]', i):
                in_bracket_math = False
                out.append('\\]')
                i += 2
                continue
            # Inline math mode end: single $
            if in_inline_math and ch == '$':
                in_inline_math = False
                out.append(ch)
                i += 1
                continue
            # If inside any math mode, just copy character (do not escape underscores)
            out.append(ch)
            i += 1
            continue

        # --- Not in verbatim or math: perform underscore handling ---
        # If current character is backslash, copy and skip next token (to avoid altering commands like \alpha or \_)
        if ch == '\\':
            # Copy the backslash and the following token (either single non-letter or letters)
            out.append(ch)
            i += 1
            if i < n:
                # If next character is letters (command), copy all letters
                if re.match(r'[A-Za-z]+', tex[i: i + 1]):
                    # Copy continuous letters that form a command
                    j = i
                    while j < n and re.match(r'[A-Za-z]+', tex[j:j + 1]):
                        out.append(tex[j])
                        j += 1
                    i = j
                else:
                    # Copy single character (could be _ or other special character)
                    out.append(tex[i])
                    i += 1
            continue

        # If underscore and not escaped, replace with \_
        if ch == '_':
            # Replace single underscore with escaped version
            out.append(r'\_')
            i += 1
            continue

        # Default case: copy character as is
        out.append(ch)
        i += 1

    # Join all processed characters into final string
    return ''.join(out)


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


def compile_project(project_dir: Path, output_pdf_path: Path):
    """
    Compile a LaTeX project directory to generate a PDF file.

    Args:
        project_dir (Path): Path to the project directory containing .tex files
        output_pdf_path (Path): Path where the output PDF should be saved
    """
    # Find all .tex files in the project directory
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

    # 1) Replace documentclass (preserve options if any)
    tex_content = replace_documentclass(tex_content)

    # 2) Escape underscores conservatively (avoid math, verbatim, etc.)
    tex_content = escape_underscores(tex_content)

    # Write back the processed file (overwrite the main .tex file)
    with open(main_path, 'w', encoding='utf-8') as f:
        f.write(tex_content)

    logger.info("Post-processing complete. Starting compilation...")

    # Determine if bibtex is needed for bibliography processing
    need_bibtex = any((project_dir / f).suffix == '.bib' for f in project_dir.iterdir())
    if not need_bibtex:
        # Also check if any tex file contains bibliography commands
        for content in candidate_tex_files.values():
            if "\\bibliography{" in content:
                need_bibtex = True
                break

    try:
        # Step 1: First xelatex compilation
        logger.info("Running first xelatex compilation...")
        subprocess.run(['xelatex', '-interaction=nonstopmode', main_tex], cwd=project_dir, check=True)

        # Step 2: Run bibtex if bibliography is needed
        if need_bibtex:
            logger.info("Running bibtex for bibliography processing...")
            aux_file = main_tex.replace('.tex', '.aux')
            subprocess.run(['bibtex', aux_file], cwd=project_dir, check=True)

        # Step 3: Second xelatex compilation (to resolve citations and cross-references)
        logger.info("Running second xelatex compilation...")
        subprocess.run(['xelatex', '-interaction=nonstopmode', main_tex], cwd=project_dir, check=True)

        # Step 4: Third xelatex compilation (final pass for perfect references)
        logger.info("Running third xelatex compilation...")
        subprocess.run(['xelatex', '-interaction=nonstopmode', main_tex], cwd=project_dir, check=True)

        # Expected PDF file path (same name as main tex file but with .pdf extension)
        expected_pdf = project_dir / main_tex.replace('.tex', '.pdf')

        # Check if PDF was successfully generated
        if expected_pdf.exists():
            # Create parent directories if they don't exist
            output_pdf_path.parent.mkdir(parents=True, exist_ok=True)
            # Move generated PDF to the specified output path
            shutil.move(expected_pdf, output_pdf_path)
            logger.info(f"PDF compiled successfully: {output_pdf_path}")
        else:
            logger.error(f"Expected output PDF not found: {expected_pdf}")

    except subprocess.CalledProcessError as e:
        # Log compilation failure and suggest checking log file
        logger.error(f"Compilation failed: {e}")
        logger.info(f"Check the .log file in {project_dir} for details.")