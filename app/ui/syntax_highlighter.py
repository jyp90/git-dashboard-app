"""SyntaxHighlighter — Diff 뷰어 내 코드 구문 강조."""
from __future__ import annotations

import re

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument


class SyntaxHighlighter(QSyntaxHighlighter):
    """Diff 뷰어 내 코드 구문 강조.

    지원 언어 (확장자 기반 자동 감지):
    - Python (.py)
    - Java (.java)
    - JavaScript/TypeScript (.js, .ts, .tsx, .jsx)
    - SQL (.sql)
    - Shell (.sh, .bash)
    - YAML/JSON (.yml, .yaml, .json)
    - XML/HTML (.xml, .html)
    """

    EXTENSION_MAP = {
        ".py": "python",
        ".java": "java",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".jsx": "javascript",
        ".sql": "sql",
        ".sh": "shell",
        ".bash": "shell",
        ".zsh": "shell",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".json": "json",
        ".xml": "xml",
        ".html": "html",
        ".htm": "html",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".gradle": "groovy",
    }

    # 색상 팔레트 (다크 테마 기준)
    COLORS = {
        "keyword":  "#cc99cd",   # 보라
        "string":   "#7ec8a0",   # 초록
        "comment":  "#6a9955",   # 짙은 초록 (회색)
        "number":   "#b5cea8",   # 연두
        "function": "#dcdcaa",   # 노랑
        "type":     "#4ec9b0",   # 청록
        "operator": "#d4d4d4",   # 밝은 회색
        "decorator":"#c586c0",   # 분홍
    }

    def __init__(self, document: QTextDocument, language: str = "python") -> None:
        super().__init__(document)
        self._language = language
        self._rules: list[tuple[re.Pattern, QTextCharFormat]] = []
        self._setup_rules()

    def set_language(self, language: str) -> None:
        """언어 변경 후 재강조."""
        self._language = language
        self._setup_rules()
        self.rehighlight()

    @classmethod
    def detect_language(cls, file_path: str) -> str:
        """파일 경로에서 언어 감지."""
        from pathlib import Path
        ext = Path(file_path).suffix.lower()
        return cls.EXTENSION_MAP.get(ext, "plain")

    def highlightBlock(self, text: str) -> None:
        """QSyntaxHighlighter 콜백 — 한 블록(줄) 강조."""
        for pattern, fmt in self._rules:
            for m in pattern.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)

    # ─── 규칙 정의 ──────────────────────────────────────────────────────────

    def _setup_rules(self) -> None:
        self._rules = []
        lang = self._language

        if lang == "python":
            self._add_python_rules()
        elif lang in ("java", "kotlin"):
            self._add_java_rules()
        elif lang in ("javascript", "typescript"):
            self._add_js_rules()
        elif lang == "sql":
            self._add_sql_rules()
        elif lang == "shell":
            self._add_shell_rules()
        elif lang in ("yaml", "json"):
            self._add_yaml_rules()
        elif lang in ("xml", "html"):
            self._add_xml_rules()
        # plain: 규칙 없음

    def _fmt(self, color: str, bold: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        return fmt

    def _add_rule(self, pattern: str, color_key: str, bold: bool = False) -> None:
        fmt = self._fmt(self.COLORS[color_key], bold)
        self._rules.append((re.compile(pattern), fmt))

    def _add_python_rules(self) -> None:
        kw = r"\b(?:def|class|import|from|as|return|if|elif|else|for|while|try|except|finally|with|in|not|and|or|is|None|True|False|pass|break|continue|raise|yield|lambda|async|await|global|nonlocal|del|assert)\b"
        self._add_rule(kw, "keyword", bold=True)
        self._add_rule(r"@\w+", "decorator")
        self._add_rule(r'"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\'|"[^"\\]*"|\'[^\'\\]*\'', "string")
        self._add_rule(r"#[^\n]*", "comment")
        self._add_rule(r"\b\d+\.?\d*\b", "number")
        self._add_rule(r"\bdef\s+(\w+)", "function")
        self._add_rule(r"\b[A-Z]\w*\b", "type")

    def _add_java_rules(self) -> None:
        kw = r"\b(?:class|interface|extends|implements|import|package|public|private|protected|static|final|new|return|if|else|for|while|do|try|catch|finally|throw|throws|void|int|long|double|float|boolean|char|String|null|true|false|this|super|abstract|synchronized|volatile|transient|instanceof|enum|break|continue|switch|case|default|override|val|var|fun|object|companion|data|sealed|open|internal|lateinit|by|get|set|init|constructor|when|is|as)\b"
        self._add_rule(kw, "keyword", bold=True)
        self._add_rule(r'"[^"\\]*"', "string")
        self._add_rule(r"//[^\n]*", "comment")
        self._add_rule(r"/\*[\s\S]*?\*/", "comment")
        self._add_rule(r"\b\d+\.?\d*[fLdF]?\b", "number")
        self._add_rule(r"\b[A-Z]\w*\b", "type")
        self._add_rule(r"@\w+", "decorator")

    def _add_js_rules(self) -> None:
        kw = r"\b(?:const|let|var|function|return|if|else|for|while|do|try|catch|finally|throw|new|class|extends|import|export|default|from|async|await|of|in|typeof|instanceof|null|undefined|true|false|this|super|switch|case|break|continue|void|delete|yield|get|set|static|abstract|interface|type|enum|implements|declare|namespace|module|as|is)\b"
        self._add_rule(kw, "keyword", bold=True)
        self._add_rule(r'`[^`]*`|"[^"\\]*"|\'[^\'\\]*\'', "string")
        self._add_rule(r"//[^\n]*", "comment")
        self._add_rule(r"/\*[\s\S]*?\*/", "comment")
        self._add_rule(r"\b\d+\.?\d*\b", "number")
        self._add_rule(r"\b[A-Z]\w*\b", "type")

    def _add_sql_rules(self) -> None:
        kw = r"\b(?:SELECT|FROM|WHERE|JOIN|LEFT|RIGHT|INNER|OUTER|ON|GROUP BY|ORDER BY|HAVING|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER|TABLE|INDEX|VIEW|DATABASE|AND|OR|NOT|IN|EXISTS|BETWEEN|LIKE|IS|NULL|AS|DISTINCT|COUNT|SUM|AVG|MAX|MIN|CASE|WHEN|THEN|ELSE|END|LIMIT|OFFSET)\b"
        self._add_rule(kw, "keyword", bold=True)
        self._add_rule(r"'[^']*'", "string")
        self._add_rule(r"--[^\n]*", "comment")
        self._add_rule(r"\b\d+\.?\d*\b", "number")

    def _add_shell_rules(self) -> None:
        kw = r"\b(?:if|then|else|elif|fi|for|do|done|while|until|case|esac|function|return|export|local|readonly|declare|typeset|echo|printf|cd|ls|mkdir|rm|cp|mv|grep|sed|awk|cat|source|\.)\b"
        self._add_rule(kw, "keyword", bold=True)
        self._add_rule(r'"[^"]*"', "string")
        self._add_rule(r"'[^']*'", "string")
        self._add_rule(r"#[^\n]*", "comment")
        self._add_rule(r"\$\w+|\$\{[^}]+\}", "type")

    def _add_yaml_rules(self) -> None:
        self._add_rule(r"^\s*[\w\-]+(?=\s*:)", "keyword")
        self._add_rule(r'"[^"]*"|\'[^\']*\'', "string")
        self._add_rule(r"#[^\n]*", "comment")
        self._add_rule(r"\b\d+\.?\d*\b", "number")
        self._add_rule(r"\b(?:true|false|null|yes|no)\b", "type")

    def _add_xml_rules(self) -> None:
        self._add_rule(r"</?[\w:-]+", "keyword")
        self._add_rule(r'[\w:-]+=', "function")
        self._add_rule(r'"[^"]*"', "string")
        self._add_rule(r"<!--[\s\S]*?-->", "comment")
