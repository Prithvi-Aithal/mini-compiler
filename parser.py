# ─────────────────────────────────────────
#  MINI COMPILER  —  Stage 2: Parser
# ─────────────────────────────────────────
#
# Job: take the flat token list produced by the Lexer and build an
# Abstract Syntax Tree (AST).  The tree captures the *structure* and
# *operator precedence* of the program — something a flat list cannot.
#
# Grammar we implement (informal BNF):
#
#   program      → statement* EOF
#   statement    → assignment | print_stmt | if_stmt | while_stmt
#   assignment   → ID ASSIGN expression NEWLINE
#   print_stmt   → PRINT expression NEWLINE
#   if_stmt      → IF expression NEWLINE block (ELSE NEWLINE block)?
#   while_stmt   → WHILE expression NEWLINE block
#   block        → statement+          (indented, but we don't enforce indentation
#                                       — we stop at EOF / ELSE / a dedent-like
#                                         heuristic explained below)
#   expression   → comparison
#   comparison   → additive ((==|!=|<|>|<=|>=) additive)*
#   additive     → term     ((+|-)  term)*
#   term         → factor   ((*|/)  factor)*
#   factor       → NUMBER | STRING | TRUE | FALSE | ID | LPAREN expression RPAREN

from lexer import (
    Lexer, Token,
    TT_INT, TT_FLOAT, TT_STRING, TT_ID,
    TT_ASSIGN, TT_PLUS, TT_MINUS, TT_MUL, TT_DIV,
    TT_LPAREN, TT_RPAREN,
    TT_EQ, TT_NEQ, TT_LT, TT_GT, TT_LTE, TT_GTE,
    TT_NEWLINE, TT_EOF,
)


# ── AST node classes ──────────────────────────────────────────────────────────
# Each class represents one kind of node in the tree.
# They are plain data containers — no logic lives here.

class NumberNode:
    """A literal integer or float.  value: int | float"""
    def __init__(self, value): self.value = value
    def __repr__(self): return f'Num({self.value})'

class StringNode:
    """A literal string.  value: str"""
    def __init__(self, value): self.value = value
    def __repr__(self): return f'Str("{self.value}")'

class BoolNode:
    """A literal boolean.  value: bool"""
    def __init__(self, value): self.value = value
    def __repr__(self): return f'Bool({self.value})'

class VarNode:
    """A variable reference.  name: str"""
    def __init__(self, name): self.name = name
    def __repr__(self): return f'Var({self.name})'

class BinOpNode:
    """A binary operation: left op right.  op: str ('+', '-', …)"""
    def __init__(self, left, op, right):
        self.left  = left
        self.op    = op
        self.right = right
    def __repr__(self): return f'BinOp({self.left} {self.op} {self.right})'

class AssignNode:
    """Variable assignment: name = expr"""
    def __init__(self, name, expr):
        self.name = name
        self.expr = expr
    def __repr__(self): return f'Assign({self.name} = {self.expr})'

class PrintNode:
    """print <expr>"""
    def __init__(self, expr): self.expr = expr
    def __repr__(self): return f'Print({self.expr})'

class IfNode:
    """if <condition> { then_block } [else { else_block }]"""
    def __init__(self, condition, then_block, else_block=None):
        self.condition  = condition
        self.then_block = then_block
        self.else_block = else_block
    def __repr__(self):
        return f'If({self.condition}, then={self.then_block}, else={self.else_block})'

class WhileNode:
    """while <condition> { body }"""
    def __init__(self, condition, body):
        self.condition = condition
        self.body      = body
    def __repr__(self): return f'While({self.condition}, body={self.body})'

class ProgramNode:
    """The root node — a list of top-level statements."""
    def __init__(self, statements): self.statements = statements
    def __repr__(self): return f'Program({self.statements})'


# ── ParseError ────────────────────────────────────────────────────────────────

class ParseError(Exception):
    def __init__(self, msg: str, line: int):
        super().__init__(f'Parse error on line {line}: {msg}')
        self.line = line


# ── Parser ────────────────────────────────────────────────────────────────────

class Parser:
    """
    Recursive-descent parser.

    Usage
    -----
        ast = Parser(tokens).parse()

    The key insight of recursive descent: each grammar rule becomes a method.
    Operator precedence is handled *structurally* — additive calls term, which
    calls factor, so * / bind tighter than + - automatically.
    """

    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.pos    = 0

    # ── public interface ──────────────────────────────────────────────────────

    def parse(self) -> ProgramNode:
        self._skip_newlines()
        statements = []
        while not self._check(TT_EOF):
            statements.append(self._statement())
            self._skip_newlines()
        return ProgramNode(statements)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _current(self) -> Token:
        return self.tokens[self.pos]

    def _check(self, *types) -> bool:
        return self._current().type in types

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def _expect(self, type_: str) -> Token:
        """Consume the next token and raise if it isn't the expected type."""
        tok = self._current()
        if tok.type != type_:
            raise ParseError(
                f"expected {type_!r} but got {tok.type!r} ({tok.value!r})",
                tok.line,
            )
        return self._advance()

    def _skip_newlines(self):
        while self._check(TT_NEWLINE):
            self._advance()

    # ── grammar rules — one method per rule ──────────────────────────────────

    def _statement(self):
        """Dispatch to the correct statement parser based on the current token."""
        tok = self._current()

        if tok.type == 'PRINT':
            return self._print_stmt()
        if tok.type == 'IF':
            return self._if_stmt()
        if tok.type == 'WHILE':
            return self._while_stmt()
        if tok.type == TT_ID:
            # Could be an assignment (ID = …).  Peek ahead to decide.
            if self.pos + 1 < len(self.tokens) and self.tokens[self.pos + 1].type == TT_ASSIGN:
                return self._assignment()
            # Otherwise it's an expression-statement (rare but valid)
            return self._expression_stmt()

        raise ParseError(f"unexpected token {tok.type!r} ({tok.value!r})", tok.line)

    def _assignment(self) -> AssignNode:
        name_tok = self._advance()          # ID
        self._advance()                     # ASSIGN  =
        expr = self._expression()
        self._expect(TT_NEWLINE)
        return AssignNode(name_tok.value, expr)

    def _print_stmt(self) -> PrintNode:
        self._advance()                     # consume PRINT keyword
        expr = self._expression()
        self._expect(TT_NEWLINE)
        return PrintNode(expr)

    def _if_stmt(self) -> IfNode:
        self._advance()                     # consume IF
        condition = self._expression()
        self._expect(TT_NEWLINE)
        self._skip_newlines()
        then_block = self._block()
        else_block = None
        if self._check('ELSE'):
            self._advance()                 # consume ELSE
            self._expect(TT_NEWLINE)
            self._skip_newlines()
            else_block = self._block()
        return IfNode(condition, then_block, else_block)

    def _while_stmt(self) -> WhileNode:
        self._advance()                     # consume WHILE
        condition = self._expression()
        self._expect(TT_NEWLINE)
        self._skip_newlines()
        body = self._block()
        return WhileNode(condition, body)

    def _block(self) -> list:
        """
        A block ends at ELSE, EOF, or a blank line (a NEWLINE token still
        present after skip_newlines consumed the statement terminator).
        A blank line in the source becomes two consecutive NEWLINE tokens;
        after _statement() consumes its own trailing NEWLINE, skip_newlines()
        eats the first extra one, leaving the second as the dedent signal.
        Writers must separate a block from the next top-level statement with
        one blank line.
        """
        statements = []
        while not self._check(TT_EOF, 'ELSE'):
            if self._check(TT_NEWLINE):   # blank line = dedent signal
                break
            statements.append(self._statement())
            # After a statement, check if the NEXT token is ALSO a NEWLINE.
            # _statement already consumed its own trailing NEWLINE, so another
            # NEWLINE here means there is a blank line -- end of block.
            if self._check(TT_NEWLINE):
                self._advance()           # consume the blank-line marker
                break
            self._skip_newlines()
        if not statements:
            raise ParseError("expected at least one statement in block", self._current().line)
        return statements

    def _expression_stmt(self):
        """An expression used as a statement (e.g. bare variable read)."""
        expr = self._expression()
        self._expect(TT_NEWLINE)
        return expr

    # ── expression hierarchy (encodes precedence) ─────────────────────────────

    def _expression(self):
        return self._comparison()

    def _comparison(self):
        """comparison → additive ((==|!=|<|>|<=|>=) additive)*"""
        left = self._additive()
        while self._check(TT_EQ, TT_NEQ, TT_LT, TT_GT, TT_LTE, TT_GTE):
            op  = self._advance().value
            right = self._additive()
            left = BinOpNode(left, op, right)
        return left

    def _additive(self):
        """additive → term ((+ | -) term)*"""
        left = self._term()
        while self._check(TT_PLUS, TT_MINUS):
            op    = self._advance().value
            right = self._term()
            left  = BinOpNode(left, op, right)
        return left

    def _term(self):
        """term → factor ((* | /) factor)*"""
        left = self._factor()
        while self._check(TT_MUL, TT_DIV):
            op    = self._advance().value
            right = self._factor()
            left  = BinOpNode(left, op, right)
        return left

    def _factor(self):
        """factor → NUMBER | STRING | TRUE | FALSE | ID | '(' expression ')'"""
        tok = self._current()

        if tok.type == TT_INT:
            self._advance()
            return NumberNode(tok.value)

        if tok.type == TT_FLOAT:
            self._advance()
            return NumberNode(tok.value)

        if tok.type == TT_STRING:
            self._advance()
            return StringNode(tok.value)

        if tok.type == 'TRUE':
            self._advance()
            return BoolNode(True)

        if tok.type == 'FALSE':
            self._advance()
            return BoolNode(False)

        if tok.type == TT_ID:
            self._advance()
            return VarNode(tok.value)

        if tok.type == TT_LPAREN:
            self._advance()             # consume '('
            expr = self._expression()
            self._expect(TT_RPAREN)     # consume ')'
            return expr

        if tok.type == TT_MINUS:        # unary minus
            self._advance()
            operand = self._factor()
            return BinOpNode(NumberNode(0), '-', operand)

        raise ParseError(
            f"expected a value but got {tok.type!r} ({tok.value!r})",
            tok.line,
        )


# ── pretty-printer (for debugging the AST) ───────────────────────────────────

def pretty(node, indent: int = 0):
    pad = '    ' * indent
    if isinstance(node, ProgramNode):
        print(pad + 'Program')
        for s in node.statements: pretty(s, indent + 1)
    elif isinstance(node, AssignNode):
        print(pad + f'Assign: {node.name} =')
        pretty(node.expr, indent + 1)
    elif isinstance(node, PrintNode):
        print(pad + 'Print:')
        pretty(node.expr, indent + 1)
    elif isinstance(node, IfNode):
        print(pad + 'If:')
        print(pad + '  condition:')
        pretty(node.condition, indent + 2)
        print(pad + '  then:')
        for s in node.then_block: pretty(s, indent + 2)
        if node.else_block:
            print(pad + '  else:')
            for s in node.else_block: pretty(s, indent + 2)
    elif isinstance(node, WhileNode):
        print(pad + 'While:')
        print(pad + '  condition:')
        pretty(node.condition, indent + 2)
        print(pad + '  body:')
        for s in node.body: pretty(s, indent + 2)
    elif isinstance(node, BinOpNode):
        print(pad + f'BinOp: {node.op}')
        pretty(node.left,  indent + 1)
        pretty(node.right, indent + 1)
    elif isinstance(node, (NumberNode, StringNode, BoolNode)):
        print(pad + repr(node))
    elif isinstance(node, VarNode):
        print(pad + repr(node))
    else:
        print(pad + repr(node))


# ── Quick test ────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    source = """\
x = 5 + 3
y = x * 2
print y
if x > 4
    print "big"
else
    print "small"
"""

    tokens = Lexer(source).tokenize()
    ast    = Parser(tokens).parse()
    print("AST:")
    pretty(ast)
