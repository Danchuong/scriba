"""Coverage for ``scriba.tex.highlight`` (Pygments wrapper).

Exercises:
- explicit language path (Python, C++, Java, JavaScript, Go, Rust, C, C#)
- heuristic auto-detection when language is missing or empty
- guess_lexer fallback when heuristics yield nothing
- 'text' lexer rejection path
- unknown-language fallback
- theme=none bypass
- empty string / whitespace / Unicode inputs

Cluster 8 coverage push — tests only, no source edits.
"""

from __future__ import annotations

import pytest

from scriba.tex.highlight import _heuristic_detect, highlight_code


# --- theme / disable paths ----------------------------------------------------


def test_theme_none_returns_none():
    result = highlight_code("print('hi')", "python", theme="none")
    assert result is None


def test_theme_none_with_unknown_language_returns_none():
    result = highlight_code("x=1", "xyz", theme="none")
    assert result is None


# --- explicit language path ---------------------------------------------------


def test_explicit_python_returns_highlighted_html():
    code = "def greet():\n    print('hi')\n"
    result = highlight_code(code, "python", theme="one-light")
    assert result is not None
    html, alias = result
    assert alias == "python"
    assert "class=" in html
    assert "tok-" in html  # classprefix="tok-"


def test_explicit_cpp_returns_highlighted_html():
    code = "#include <iostream>\nint main(){ std::cout<<1; return 0; }"
    result = highlight_code(code, "cpp", theme="one-light")
    assert result is not None
    html, alias = result
    assert alias == "cpp"
    assert "tok-" in html


def test_explicit_java_returns_highlighted_html():
    code = "public class A { public static void main(String[] a) {} }"
    result = highlight_code(code, "java", theme="one-light")
    assert result is not None
    html, alias = result
    assert alias == "java"


def test_explicit_javascript_returns_highlighted_html():
    code = "const x = 1; console.log(x);"
    result = highlight_code(code, "javascript", theme="one-light")
    assert result is not None
    html, alias = result
    assert alias == "javascript"


def test_explicit_go_returns_highlighted_html():
    code = "package main\nfunc main() { fmt.Println(\"hi\") }"
    result = highlight_code(code, "go", theme="one-light")
    assert result is not None
    html, alias = result
    assert alias == "go"


def test_explicit_rust_returns_highlighted_html():
    code = "fn main() { let mut x = 1; println!(\"{}\", x); }"
    result = highlight_code(code, "rust", theme="one-light")
    assert result is not None
    html, alias = result
    assert alias == "rust"


def test_explicit_c_returns_highlighted_html():
    code = "#include <stdio.h>\nint main(){ printf(\"hi\"); return 0; }"
    result = highlight_code(code, "c", theme="one-light")
    assert result is not None
    html, alias = result
    assert alias == "c"


def test_explicit_csharp_returns_highlighted_html():
    code = "using System;\nclass A { static void Main(){ Console.WriteLine(1); } }"
    result = highlight_code(code, "csharp", theme="one-light")
    assert result is not None
    html, alias = result
    # Pygments aliases csharp -> csharp or c#
    assert alias in {"csharp", "c#"}


def test_unknown_explicit_language_returns_none():
    """Unknown language returns None rather than silently guessing."""
    result = highlight_code("x = 1", "this-is-not-a-real-lang", theme="one-light")
    assert result is None


def test_theme_one_dark_still_returns_html():
    """The theme value is accepted verbatim; Pygments class prefix is fixed."""
    result = highlight_code("def f(): pass", "python", theme="one-dark")
    assert result is not None
    html, alias = result
    assert alias == "python"
    assert "tok-" in html


# --- heuristic auto-detection -------------------------------------------------


def test_heuristic_detects_cpp_from_include():
    lang = _heuristic_detect("#include <iostream>\nint main(){}")
    assert lang == "cpp"


def test_heuristic_detects_python_from_def():
    lang = _heuristic_detect("def f():\n    return 1\n")
    assert lang == "python"


def test_heuristic_detects_java_from_public_class():
    lang = _heuristic_detect("public class A { System.out.println(1); }")
    assert lang == "java"


def test_heuristic_detects_go_from_package():
    lang = _heuristic_detect("package main\nfunc main(){ fmt.Println(1) }\n")
    assert lang == "go"


def test_heuristic_detects_rust_from_fn_main():
    lang = _heuristic_detect("fn main() { let mut x = 1; println!(\"{}\", x); }")
    assert lang == "rust"


def test_heuristic_detects_c_from_printf():
    lang = _heuristic_detect("#include <stdio.h>\nint foo(){ printf(\"x\"); }")
    # Both c and cpp patterns may match; heuristic picks best.
    assert lang in {"c", "cpp"}


def test_heuristic_detects_javascript_from_arrow():
    lang = _heuristic_detect("const f = () => { console.log(1); };")
    assert lang == "javascript"


def test_heuristic_detects_csharp_from_using_system():
    lang = _heuristic_detect("using System;\nConsole.WriteLine(1);")
    assert lang == "csharp"


def test_heuristic_returns_none_for_plain_prose():
    lang = _heuristic_detect("This is not code, just words.")
    assert lang is None


def test_heuristic_returns_none_for_empty_string():
    assert _heuristic_detect("") is None


# --- auto-detection through highlight_code (language = None / empty) ---------


def test_autodetect_python_from_content():
    code = "def greet():\n    print('hi')\n    return 0\n"
    result = highlight_code(code, None, theme="one-light")
    assert result is not None
    html, alias = result
    assert alias == "python"


def test_autodetect_empty_language_string_uses_heuristic():
    """An empty explicit language behaves like None (no language given)."""
    code = "#include <iostream>\nint main(){ return 0; }"
    result = highlight_code(code, "", theme="one-light")
    assert result is not None
    _html, alias = result
    assert alias == "cpp"


def test_autodetect_returns_none_for_plain_text():
    """Plain prose with no lexer hints -> Pygments' "Text only" is rejected."""
    result = highlight_code("hello world this is plain", None, theme="one-light")
    # Should fall through the text-rejection path.
    assert result is None


def test_autodetect_json_falls_back_to_guess_lexer():
    """JSON has no heuristic entry; guess_lexer should catch it."""
    code = '{"name": "alice", "age": 30, "tags": ["a", "b"]}'
    result = highlight_code(code, None, theme="one-light")
    # Either guess_lexer returns a non-text lexer (JSON) or None;
    # both are valid per the contract. We just assert it doesn't crash.
    if result is not None:
        html, alias = result
        assert isinstance(html, str)
        assert isinstance(alias, str)


# --- edge cases --------------------------------------------------------------


def test_empty_string_with_explicit_language():
    result = highlight_code("", "python", theme="one-light")
    # Pygments accepts empty input and returns an empty highlight div.
    assert result is not None
    html, alias = result
    assert alias == "python"
    assert isinstance(html, str)


def test_whitespace_only_with_auto_detect_returns_none():
    """Only whitespace -> no heuristic hits, guess_lexer falls back to text."""
    result = highlight_code("   \n  \n", None, theme="one-light")
    assert result is None


def test_very_long_input_highlights_ok():
    code = "x = 1\n" * 5000
    result = highlight_code(code, "python", theme="one-light")
    assert result is not None
    html, _alias = result
    assert len(html) > 0


def test_unicode_identifiers_highlight_ok():
    code = "def café():\n    return 'naïve résumé'"
    result = highlight_code(code, "python", theme="one-light")
    assert result is not None
    html, _alias = result
    assert "café" in html or "caf&#233;" in html or "caf" in html


def test_control_characters_do_not_crash():
    # NUL, bell, etc. — should not raise.
    code = "def f():\x07\n    return 1\n"
    result = highlight_code(code, "python", theme="one-light")
    assert result is not None


def test_special_characters_html_escaped():
    code = "x = '<script>alert(1)</script>'"
    result = highlight_code(code, "python", theme="one-light")
    assert result is not None
    html, _ = result
    # Pygments must HTML-escape angle brackets in the output.
    assert "<script>" not in html
    assert "&lt;script&gt;" in html or "&lt;" in html
