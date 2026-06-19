#!/usr/bin/env python3
# ─────────────────────────────────────────
#  MINI COMPILER  —  main.py
#  Entry point: run a .mini source file
#  through all 4 pipeline stages.
# ─────────────────────────────────────────
#
#  Usage:
#    python main.py program.mini          ← run a file
#    python main.py --debug program.mini  ← also print tokens + AST
#    python main.py --repl                ← interactive REPL

import sys
import os

from lexer        import Lexer, LexerError
from parser       import Parser, ParseError, pretty
from interpreter  import SemanticAnalyzer, SemanticError, Interpreter, RuntimeError_


# ── Pipeline ──────────────────────────────────────────────────────────────────

def run(source: str, debug: bool = False) -> bool:
    """
    Run source code through the full pipeline.
    Returns True on success, False on any error.
    """
    # ── Stage 1: Lex ──────────────────────────────────────────────────────────
    try:
        tokens = Lexer(source).tokenize()
    except LexerError as e:
        print(f"\n[LEXER ERROR] {e}")
        return False

    if debug:
        print("\n── Tokens ──────────────────────────────────────────")
        for tok in tokens:
            print(' ', tok)

    # ── Stage 2: Parse ────────────────────────────────────────────────────────
    try:
        ast = Parser(tokens).parse()
    except ParseError as e:
        print(f"\n[PARSE ERROR] {e}")
        return False

    if debug:
        print("\n── AST ─────────────────────────────────────────────")
        pretty(ast)

    # ── Stage 3: Semantic Analysis ────────────────────────────────────────────
    try:
        SemanticAnalyzer().analyze(ast)
    except SemanticError as e:
        print(f"\n[SEMANTIC ERROR] {e}")
        return False

    # ── Stage 4: Interpret ────────────────────────────────────────────────────
    try:
        if debug:
            print("\n── Output ──────────────────────────────────────────")
        Interpreter().run(ast)
    except RuntimeError_ as e:
        print(f"\n[RUNTIME ERROR] {e}")
        return False

    return True


# ── REPL ──────────────────────────────────────────────────────────────────────

def repl():
    """
    Interactive Read-Eval-Print Loop.
    Maintains a persistent interpreter so variables survive across inputs.
    Multi-line input: end with a blank line.
    """
    print("Mini Compiler REPL  (type 'exit' to quit, blank line to run)")
    print("────────────────────────────────────────────────────────────")
    analyzer = SemanticAnalyzer()
    interp = Interpreter()

    while True:
        lines = []
        try:
            while True:
                prompt = '>>> ' if not lines else '... '
                line = input(prompt)
                if line.lower() == 'exit':
                    print("Goodbye!")
                    sys.exit(0)
                if line == '' and lines:
                    break
                lines.append(line)
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        source = '\n'.join(lines) + '\n'

        try:
            tokens = Lexer(source).tokenize()
            ast    = Parser(tokens).parse()
            analyzer.analyze(ast)
            interp.run(ast)
        except (LexerError, ParseError, SemanticError, RuntimeError_) as e:
            # Print a compact error tag
            tag = type(e).__name__.replace('Error_', ' Error').replace('Error', ' Error').strip()
            print(f"[{tag}] {e}")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    args = sys.argv[1:]

    if '--repl' in args:
        repl()
        return

    debug = '--debug' in args
    args  = [a for a in args if not a.startswith('--')]

    if not args:
        print("Usage:")
        print("  python main.py program.mini")
        print("  python main.py --debug program.mini")
        print("  python main.py --repl")
        sys.exit(1)

    path = args[0]
    if not os.path.exists(path):
        print(f"Error: file not found: {path!r}")
        sys.exit(1)

    with open(path) as f:
        source = f.read()

    success = run(source, debug=debug)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
