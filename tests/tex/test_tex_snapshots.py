"""30 snapshot tests for TexRenderer per docs/scriba/02-tex-plugin.md §8.

Each test calls Pipeline.render(...) (not TexRenderer in isolation) so the
Pipeline orchestration is exercised on every snapshot. Snapshots live under
``tests/tex/snapshots/<name>.html`` and start out empty in Phase 2a — the
GREEN-phase agent fills them in after reviewing actual output against the
spec contract in §3 of 02-tex-plugin.md.
"""

from __future__ import annotations

from tests.tex.conftest import assert_snapshot_match


# 1
def test_inline_math_basic(pipeline, ctx):
    tex = r"Let $x^2 + y^2 = r^2$ be a circle."
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "inline_math_basic")


# 2
def test_inline_math_with_subscript(pipeline, ctx):
    tex = r"The element $a_i$ for index $i$."
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "inline_math_with_subscript")


# 3
def test_display_math_double_dollar(pipeline, ctx):
    tex = r"$$\sum_{i=1}^{n} a_i$$"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "display_math_double_dollar")


# 4
def test_display_math_triple_dollar(pipeline, ctx):
    tex = r"$$$\sum_{i=1}^{n} a_i$$$"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "display_math_triple_dollar")


# 5
def test_math_with_macros(pipeline_with_macros, ctx):
    tex = r"$\RR$"
    doc = pipeline_with_macros.render(tex, ctx)
    assert_snapshot_match(doc.html, "math_with_macros")


# 6
def test_escaped_dollar_is_literal(pipeline, ctx):
    tex = r"The price is \$5."
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "escaped_dollar_is_literal")


# 7
def test_textbf_nested_in_textit(pipeline, ctx):
    tex = r"\textit{\textbf{A}}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "textbf_nested_in_textit")


# 8
def test_sout_and_underline(pipeline, ctx):
    tex = r"\sout{\underline{A}}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "sout_and_underline")


# 9
def test_all_size_commands(pipeline, ctx):
    tex = (
        r"\tiny a \scriptsize b \small c \normalsize d \large e "
        r"\Large f \LARGE g \huge h \Huge i"
    )
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "all_size_commands")


# 10
def test_section_with_id_slug(pipeline, ctx):
    tex = r"\section{My Section}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "section_with_id_slug")


# 11
def test_duplicate_section_ids(pipeline, ctx):
    tex = r"\section{A}\section{A}\section{A}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "duplicate_section_ids")


# 12
def test_itemize_simple(pipeline, ctx):
    tex = r"\begin{itemize}\item A\item B\end{itemize}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "itemize_simple")


# 13
def test_enumerate_nested_in_itemize(pipeline, ctx):
    tex = (
        r"\begin{itemize}\item A\begin{enumerate}"
        r"\item x\item y\end{enumerate}\end{itemize}"
    )
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "enumerate_nested_in_itemize")


# 14
def test_lstlisting_cpp_pygments(pipeline, ctx):
    tex = r"\begin{lstlisting}[language=cpp]int main(){return 0;}\end{lstlisting}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "lstlisting_cpp_pygments")


# 15
def test_lstlisting_python_pygments(pipeline, ctx):
    tex = r"\begin{lstlisting}[language=python]def f(): pass\end{lstlisting}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "lstlisting_python_pygments")


# 16
def test_lstlisting_java_pygments(pipeline, ctx):
    tex = r"\begin{lstlisting}[language=java]class A{}\end{lstlisting}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "lstlisting_java_pygments")


# 17
def test_lstlisting_unknown_language_fallback(pipeline, ctx):
    tex = r"\begin{lstlisting}[language=xyz]hello\end{lstlisting}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "lstlisting_unknown_language_fallback")


# 18
def test_lstlisting_no_pygments(pipeline_no_highlight, ctx):
    tex = r"\begin{lstlisting}[language=cpp]int main(){return 0;}\end{lstlisting}"
    doc = pipeline_no_highlight.render(tex, ctx)
    assert_snapshot_match(doc.html, "lstlisting_no_pygments")


# 19
def test_tabular_with_hlines_and_borders(pipeline, ctx):
    tex = r"\begin{tabular}{|l|c|r|}\hline A&B&C\\\hline\end{tabular}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "tabular_with_hlines_and_borders")


# 20
def test_tabular_with_multicolumn(pipeline, ctx):
    tex = r"\begin{tabular}{|l|l|l|}\multicolumn{2}{|c|}{Header} & X\\\end{tabular}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "tabular_with_multicolumn")


# 21
def test_tabular_with_cline(pipeline, ctx):
    tex = r"\begin{tabular}{ll}A&B\\\cline{2-2} C&D\\\end{tabular}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "tabular_with_cline")


# 22
def test_includegraphics_with_scale(pipeline, ctx):
    tex = r"\includegraphics[scale=0.5]{fig.png}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "includegraphics_with_scale")


# 23
def test_includegraphics_with_width_cm(pipeline, ctx):
    tex = r"\includegraphics[width=5cm]{fig.png}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "includegraphics_with_width_cm")


# 24
def test_includegraphics_missing_resource(pipeline, ctx_missing_resource):
    tex = r"\includegraphics{gone.png}"
    doc = pipeline.render(tex, ctx_missing_resource)
    assert_snapshot_match(doc.html, "includegraphics_missing_resource")


# 25
def test_epigraph(pipeline, ctx):
    tex = r"\epigraph{Simplicity is prerequisite for reliability.}{Dijkstra}"
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "epigraph")


# 26
def test_url_and_href(pipeline, ctx):
    tex = r"See \url{https://a.example} and \href{https://b.example}{B}."
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "url_and_href")


# 27
def test_unicode_vietnamese_with_math(pipeline, ctx):
    tex = r"Bài toán 1: tìm $x$ sao cho $x^2 = 4$."
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "unicode_vietnamese_with_math")


# 28
def test_dashes_and_quotes(pipeline, ctx):
    tex = "The quick---brown fox -- and ``this'' too."
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "dashes_and_quotes")


# 29
def test_empty_input(pipeline, ctx):
    doc = pipeline.render("", ctx)
    assert_snapshot_match(doc.html, "empty_input")


# 30
def test_very_long_input_10k_chars(pipeline, ctx):
    chunks = []
    for i in range(225):
        chunks.append(f"Paragraph {i} with math $x_{i} = {i}$ and text.\n\n")
    tex = "".join(chunks)
    assert len(tex) >= 10_000
    doc = pipeline.render(tex, ctx)
    assert_snapshot_match(doc.html, "very_long_input_10k_chars")
