"""Custom Pygments syntax highlighting style mapped strictly to CouchPilot tokens."""
from pygments.formatters import HtmlFormatter
from pygments.lexers import DiffLexer, PythonLexer
from pygments.style import Style
from pygments.token import (
    Comment,
    Error,
    Generic,
    Keyword,
    Name,
    Number,
    Operator,
    Punctuation,
    String,
    Text,
)


class CouchPilotStyle(Style):
    """Pygments style conforming to the mandated developer utility palette."""

    background_color = "#F7F5F0"
    default_style = ""

    styles = {
        Text: "#1F2A33",
        Comment: "italic #55616B",
        Keyword: "bold #5B2C6F",
        Keyword.Constant: "#1B4F72",
        Keyword.Declaration: "bold #5B2C6F",
        Keyword.Namespace: "#5B2C6F",
        Name: "#1F2A33",
        Name.Builtin: "#1B4F72",
        Name.Function: "bold #1B4F72",
        Name.Class: "bold #5B2C6F",
        Name.Decorator: "#5B2C6F",
        String: "#55616B",
        String.Doc: "italic #55616B",
        Number: "#1B4F72",
        Operator: "#55616B",
        Punctuation: "#55616B",
        Error: "border:#B83227 #B83227",
        # Diff tokens
        Generic.Inserted: "bold #236B3E bg:#EBF5EE",
        Generic.Deleted: "#B83227 bg:#FCEBEA",
        Generic.Heading: "bold #1B4F72",
        Generic.Subheading: "#55616B",
    }


def highlight_diff(diff_text: str) -> str:
    """Render unified diff string to syntax-highlighted HTML."""
    from pygments import highlight
    lexer = DiffLexer()
    formatter = HtmlFormatter(
        style=CouchPilotStyle,
        noclasses=True,
        nowrap=False,
    )
    return highlight(diff_text, lexer, formatter)


def highlight_python(code_text: str) -> str:
    """Render Python code snippet to syntax-highlighted HTML."""
    from pygments import highlight
    lexer = PythonLexer()
    formatter = HtmlFormatter(
        style=CouchPilotStyle,
        noclasses=True,
        nowrap=False,
    )
    return highlight(code_text, lexer, formatter)
