# ─────────────────────────────────────────
#  MINI COMPILER  —  Stages 3 & 4
#  Semantic Analyzer + Interpreter
# ─────────────────────────────────────────
#
# Stage 3 – Semantic Analyzer
#   Walks the AST BEFORE execution and catches logical errors:
#   • Use of a variable before it is assigned
#   • Division by zero (if detectable at compile time)
#
# Stage 4 – Interpreter
#   Walks the AST and evaluates every node, producing actual output.
#   Maintains a symbol table (dict) that maps variable names to values.

from parser import (
    Parser,
    ProgramNode, AssignNode, PrintNode, IfNode, WhileNode,
    BinOpNode, NumberNode, StringNode, BoolNode, VarNode,
)
from lexer import Lexer


# ─────────────────────────────────────────────────────────────────────────────
#  Stage 3 — Semantic Analyzer
# ─────────────────────────────────────────────────────────────────────────────

class SemanticError(Exception):
    pass


class SemanticAnalyzer:
    """
    Single-pass AST walk that populates a set of 'declared' variable names
    and raises SemanticError when a variable is used before assignment.

    We also do a lightweight constant-folding check for division by the
    literal zero.

    Usage
    -----
        SemanticAnalyzer().analyze(ast)   # raises SemanticError or returns None
    """

    def __init__(self):
        # Variables that have been assigned at least once
        self.declared: set[str] = set()

    def analyze(self, node):
        """Entry point — call with the ProgramNode."""
        self._visit(node)

    # ── dispatcher ────────────────────────────────────────────────────────────

    def _visit(self, node):
        method_name = f'_visit_{type(node).__name__}'
        visitor = getattr(self, method_name, self._generic_visit)
        return visitor(node)

    def _generic_visit(self, node):
        raise SemanticError(f"No analyzer rule for {type(node).__name__}")

    # ── visitors ──────────────────────────────────────────────────────────────

    def _visit_ProgramNode(self, node: ProgramNode):
        for stmt in node.statements:
            self._visit(stmt)

    def _visit_AssignNode(self, node: AssignNode):
        self._visit(node.expr)          # RHS must be valid first
        self.declared.add(node.name)    # now the variable is declared

    def _visit_PrintNode(self, node: PrintNode):
        self._visit(node.expr)

    def _visit_IfNode(self, node: IfNode):
        self._visit(node.condition)
        # We analyze both branches; variables assigned in one branch are NOT
        # guaranteed to be declared after the if (conservative approach).
        saved = set(self.declared)
        for stmt in node.then_block:
            self._visit(stmt)
        then_declared = set(self.declared)

        self.declared = set(saved)
        if node.else_block:
            for stmt in node.else_block:
                self._visit(stmt)
            else_declared = set(self.declared)
            # Only variables assigned in BOTH branches are guaranteed declared
            self.declared = then_declared & else_declared
        else:
            # Without else, nothing from the then-branch is guaranteed
            self.declared = saved

    def _visit_WhileNode(self, node: WhileNode):
        # Pre-scan: any variable assigned in the body is considered declared
        # BEFORE we check the condition.  This allows the classic loop-counter
        # pattern: x = 1 \n while x < 10 \n x = x + 1
        # We do this by doing a first pass over the body to collect assignments.
        self._pre_declare_assignments(node.body)
        self._visit(node.condition)
        for stmt in node.body:
            self._visit(stmt)

    def _pre_declare_assignments(self, stmts):
        """Shallow scan: collect all variable names assigned at this block level."""
        for stmt in stmts:
            if isinstance(stmt, AssignNode):
                self.declared.add(stmt.name)

    def _visit_BinOpNode(self, node: BinOpNode):
        self._visit(node.left)
        self._visit(node.right)
        # Catch literal division by zero
        if node.op == '/' and isinstance(node.right, NumberNode) and node.right.value == 0:
            raise SemanticError("division by zero detected at compile time")

    def _visit_NumberNode(self, node: NumberNode):
        pass   # always valid

    def _visit_StringNode(self, node: StringNode):
        pass

    def _visit_BoolNode(self, node: BoolNode):
        pass

    def _visit_VarNode(self, node: VarNode):
        if node.name not in self.declared:
            raise SemanticError(f"variable '{node.name}' used before assignment")


# ─────────────────────────────────────────────────────────────────────────────
#  Stage 4 — Interpreter
# ─────────────────────────────────────────────────────────────────────────────

class RuntimeError_(Exception):
    """Custom runtime error so we don't shadow Python's built-in RuntimeError."""
    pass


class Interpreter:
    """
    Tree-walk interpreter.  Evaluates the AST and produces side-effects
    (print output, variable mutation).

    Usage
    -----
        Interpreter().run(ast)
    """

    def __init__(self):
        # Symbol table: variable name → current value
        self.env: dict[str, object] = {}

    def run(self, node):
        """Entry point."""
        self._exec(node)

    # ── dispatcher (same pattern as the analyzer) ─────────────────────────────

    def _exec(self, node):
        """Execute a *statement* node — side effects, no return value."""
        method = f'_exec_{type(node).__name__}'
        getattr(self, method)(node)

    def _eval(self, node):
        """Evaluate an *expression* node — returns a Python value."""
        method = f'_eval_{type(node).__name__}'
        return getattr(self, method)(node)

    # ── statement executors ───────────────────────────────────────────────────

    def _exec_ProgramNode(self, node: ProgramNode):
        for stmt in node.statements:
            self._exec(stmt)

    def _exec_AssignNode(self, node: AssignNode):
        value = self._eval(node.expr)
        self.env[node.name] = value

    def _exec_PrintNode(self, node: PrintNode):
        value = self._eval(node.expr)
        print(value)

    def _exec_IfNode(self, node: IfNode):
        condition = self._eval(node.condition)
        if self._is_truthy(condition):
            for stmt in node.then_block:
                self._exec(stmt)
        elif node.else_block:
            for stmt in node.else_block:
                self._exec(stmt)

    def _exec_WhileNode(self, node: WhileNode):
        iteration_limit = 100_000      # safety guard against infinite loops
        count = 0
        while self._is_truthy(self._eval(node.condition)):
            for stmt in node.body:
                self._exec(stmt)
            count += 1
            if count >= iteration_limit:
                raise RuntimeError_("while loop exceeded iteration limit (possible infinite loop)")

    # ── expression evaluators ─────────────────────────────────────────────────

    def _eval_NumberNode(self, node: NumberNode):
        return node.value

    def _eval_StringNode(self, node: StringNode):
        return node.value

    def _eval_BoolNode(self, node: BoolNode):
        return node.value

    def _eval_VarNode(self, node: VarNode):
        if node.name not in self.env:
            raise RuntimeError_(f"undefined variable '{node.name}'")
        return self.env[node.name]

    def _eval_BinOpNode(self, node: BinOpNode):
        left  = self._eval(node.left)
        right = self._eval(node.right)
        op    = node.op

        # ── arithmetic ────────────────────────────────────────────────────
        if op == '+':
            # Support string concatenation too
            if isinstance(left, str) or isinstance(right, str):
                return str(left) + str(right)
            return left + right
        if op == '-': return left - right
        if op == '*': return left * right
        if op == '/':
            if right == 0:
                raise RuntimeError_("division by zero")
            # Integer division if both operands are ints
            if isinstance(left, int) and isinstance(right, int):
                return left // right
            return left / right

        # ── comparison ────────────────────────────────────────────────────
        if op == '==': return left == right
        if op == '!=': return left != right
        if op == '<':  return left <  right
        if op == '>':  return left >  right
        if op == '<=': return left <= right
        if op == '>=': return left >= right

        raise RuntimeError_(f"unknown operator '{op}'")

    # ── helper ────────────────────────────────────────────────────────────────

    @staticmethod
    def _is_truthy(value) -> bool:
        """
        Truthiness rules (similar to Python):
          • False, 0, 0.0, "", None  → falsy
          • Everything else           → truthy
        """
        return bool(value)


# ─────────────────────────────────────────────────────────────────────────────
#  Quick test
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    source = """\
x = 10
y = 3
result = x + y * 2
print result

if result > 15
    print "result is big"
else
    print "result is small"

counter = 1
while counter < 4
    print counter
    counter = counter + 1

name = "Prithvi"
print "Hello, " + name
"""

    print("=== Source ===")
    print(source)

    # Stage 1 — lex
    tokens = Lexer(source).tokenize()

    # Stage 2 — parse
    ast = Parser(tokens).parse()

    # Stage 3 — semantic analysis
    print("=== Semantic Analysis ===")
    try:
        SemanticAnalyzer().analyze(ast)
        print("No semantic errors found.\n")
    except SemanticError as e:
        print(f"SEMANTIC ERROR: {e}\n")

    # Stage 4 — interpret
    print("=== Output ===")
    try:
        Interpreter().run(ast)
    except RuntimeError_ as e:
        print(f"RUNTIME ERROR: {e}")
