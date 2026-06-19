# ─────────────────────────────────────────
#  MINI COMPILER  —  Stage 1: Lexer
# ─────────────────────────────────────────
#
# Job: turn raw source text into a flat list of Token objects.
# Every later stage (parser, analyser, interpreter) works on tokens,
# never on raw strings.

import re

# ── Token types ───────────────────────────────────────────────────────────────
# We use plain string constants so they're easy to print and compare.

TT_INT    = 'INT'       # integer literal, e.g. 42
TT_FLOAT  = 'FLOAT'     # float literal,   e.g. 3.14
TT_STRING = 'STRING'    # string literal,  e.g. "hello"
TT_ID     = 'ID'        # identifier,      e.g. x  myVar
TT_ASSIGN = 'ASSIGN'    # =
TT_PLUS   = 'PLUS'      # +
TT_MINUS  = 'MINUS'     # -
TT_MUL    = 'MUL'       # *
TT_DIV    = 'DIV'       # /
TT_LPAREN = 'LPAREN'    # (
TT_RPAREN = 'RPAREN'    # )
TT_EQ     = 'EQ'        # ==
TT_NEQ    = 'NEQ'       # !=
TT_LT     = 'LT'        # <
TT_GT     = 'GT'        # >
TT_LTE    = 'LTE'       # <=
TT_GTE    = 'GTE'       # >=
TT_NEWLINE= 'NEWLINE'   # end of statement
TT_EOF    = 'EOF'       # end of file (sentinel)

# Keywords — these look like identifiers but mean something special
KEYWORDS = {'if', 'else', 'while', 'print', 'true', 'false'}


# ── Token dataclass ───────────────────────────────────────────────────────────

class Token:
    """
    A single meaningful unit of source code.

    Attributes
    ----------
    type  : one of the TT_* constants above (or a keyword string)
    value : the actual text / number the token represents (may be None)
    line  : 1-based line number in the source (useful for error messages)
    """

    def __init__(self, type_: str, value=None, line: int = 0):
        self.type  = type_
        self.value = value
        self.line  = line

    def __repr__(self):
        if self.value is not None:
            return f'[{self.type}:{self.value}]'
        return f'[{self.type}]'


# ── LexerError ────────────────────────────────────────────────────────────────

class LexerError(Exception):
    def __init__(self, msg: str, line: int):
        super().__init__(f'Lexer error on line {line}: {msg}')
        self.line = line


# ── Lexer ─────────────────────────────────────────────────────────────────────

class Lexer:
    """
    Converts a source string into a list of Token objects.

    Usage
    -----
        tokens = Lexer(source_code).tokenize()
    """

    def __init__(self, source: str):
        self.source = source
        self.pos    = 0          # current character index
        self.line   = 1          # current line (for error messages)

    # ── public interface ──────────────────────────────────────────────────────

    def tokenize(self) -> list[Token]:
        tokens = []
        while self.pos < len(self.source):
            tok = self._next_token()
            if tok:                     # None means "whitespace — skip"
                tokens.append(tok)
        tokens.append(Token(TT_EOF, line=self.line))
        return tokens

    # ── internal helpers ──────────────────────────────────────────────────────

    def _current(self) -> str:
        """Return the character at the current position (or '' at end)."""
        return self.source[self.pos] if self.pos < len(self.source) else ''

    def _advance(self) -> str:
        """Consume the current character and return it."""
        ch = self.source[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
        return ch

    def _peek(self, offset: int = 1) -> str:
        """Look ahead without consuming."""
        idx = self.pos + offset
        return self.source[idx] if idx < len(self.source) else ''

    # ── token dispatch ────────────────────────────────────────────────────────

    def _next_token(self):
        ch = self._current()

        # ── whitespace (not newlines) ──────────────────────────────────────
        if ch in (' ', '\t', '\r'):
            self._advance()
            return None

        # ── newlines act as statement terminators ──────────────────────────
        if ch == '\n':
            self._advance()
            return Token(TT_NEWLINE, line=self.line - 1)

        # ── single-line comments  # … ──────────────────────────────────────
        if ch == '#':
            while self._current() and self._current() != '\n':
                self._advance()
            return None

        # ── string literals  "…" ──────────────────────────────────────────
        if ch == '"':
            return self._read_string()

        # ── numbers ───────────────────────────────────────────────────────
        if ch.isdigit():
            return self._read_number()

        # ── identifiers and keywords ──────────────────────────────────────
        if ch.isalpha() or ch == '_':
            return self._read_identifier()

        # ── two-character operators ───────────────────────────────────────
        two = ch + self._peek()
        if two == '==': self._advance(); self._advance(); return Token(TT_EQ,  '==', self.line)
        if two == '!=': self._advance(); self._advance(); return Token(TT_NEQ, '!=', self.line)
        if two == '<=': self._advance(); self._advance(); return Token(TT_LTE, '<=', self.line)
        if two == '>=': self._advance(); self._advance(); return Token(TT_GTE, '>=', self.line)

        # ── single-character operators / punctuation ──────────────────────
        simple = {
            '=': TT_ASSIGN, '+': TT_PLUS, '-': TT_MINUS,
            '*': TT_MUL,    '/': TT_DIV,
            '(': TT_LPAREN, ')': TT_RPAREN,
            '<': TT_LT,     '>': TT_GT,
        }
        if ch in simple:
            self._advance()
            return Token(simple[ch], ch, self.line)

        # ── unknown character ─────────────────────────────────────────────
        raise LexerError(f"unexpected character '{ch}'", self.line)

    # ── readers ───────────────────────────────────────────────────────────────

    def _read_number(self) -> Token:
        """Read an integer or float literal."""
        start = self.pos
        is_float = False
        while self._current().isdigit():
            self._advance()
        if self._current() == '.' and self._peek().isdigit():
            is_float = True
            self._advance()           # consume '.'
            while self._current().isdigit():
                self._advance()
        raw = self.source[start:self.pos]
        if is_float:
            return Token(TT_FLOAT, float(raw), self.line)
        return Token(TT_INT, int(raw), self.line)

    def _read_identifier(self) -> Token:
        """Read an identifier or keyword."""
        start = self.pos
        while self._current().isalnum() or self._current() == '_':
            self._advance()
        name = self.source[start:self.pos]
        # Keywords get their own token type equal to the keyword itself
        tok_type = name.upper() if name in KEYWORDS else TT_ID
        value    = name if tok_type == TT_ID else None
        return Token(tok_type, value, self.line)

    def _read_string(self) -> Token:
        """Read a double-quoted string literal."""
        line = self.line
        self._advance()               # consume opening "
        chars = []
        while self._current() and self._current() != '"':
            if self._current() == '\\':   # simple escape sequences
                self._advance()
                esc = self._advance()
                chars.append({'n': '\n', 't': '\t', '\\': '\\'}.get(esc, esc))
            else:
                chars.append(self._advance())
        if not self._current():
            raise LexerError("unterminated string literal", line)
        self._advance()               # consume closing "
        return Token(TT_STRING, ''.join(chars), line)


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    source = """\
# Simple test program
x = 5 + 3
y = x * 2
print "result"
print y
if x > 4
    print "big"
"""

    print("Source:")
    print(source)
    print("Tokens:")
    tokens = Lexer(source).tokenize()
    for tok in tokens:
        print(' ', tok)
