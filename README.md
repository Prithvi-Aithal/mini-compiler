# Mini Compiler

A compiler for a custom language built from scratch in pure Python — no external libraries.

Implements the full compiler pipeline:
- **Lexer** — tokenizes raw source text
- **Parser** — builds an Abstract Syntax Tree using recursive descent
- **Semantic Analyzer** — catches errors before execution (undeclared variables, division by zero)
- **Interpreter** — tree-walk evaluator that executes the AST

## Language Features
- Variables and arithmetic (`+`, `-`, `*`, `/`)
- String concatenation
- `if` / `else`
- `while` loops
- `print` statements
- Comparisons (`==`, `!=`, `<`, `>`, `<=`, `>=`)
- Comments with `#`
- Floats and booleans

## Usage

```bash
python main.py program.mini          # run a file
python main.py --debug program.mini  # show tokens + AST + output
python main.py --repl                # interactive mode
```

## Example

```
x = 10
y = 3
result = x + y * 2
print result

if result > 15
    print "big"
else
    print "small"
```

Output:
```
16
big
```

## How it works

```text
source code ─► Lexer ─► tokens ─► Parser ─► AST ─► Semantic analyzer ─► Interpreter ─► output
              lexer.py           parser.py         interpreter.py       interpreter.py
```

- **Lexer** (`lexer.py`): turns raw text into tokens such as `[ID:x]`, `[INT:2]` and `[PLUS:+]`, and reports the line number of anything it doesn't recognise.
- **Parser** (`parser.py`): recursive descent. Operator precedence is encoded in the grammar itself (comparisons call additive expressions, additive calls term, term calls factor), so `2 + 3 * 4` parses as `2 + (3 * 4)`.
- **Semantic analyzer** (`interpreter.py`): walks the AST before anything runs and rejects variables used before assignment and division by a constant zero.
- **Interpreter** (`interpreter.py`): a tree-walk evaluator that executes the checked AST.

## Errors caught before execution

```text
$ python main.py bad.mini          # x = 5 / print y
[SEMANTIC ERROR] variable 'y' used before assignment

$ python main.py bad.mini          # a = 10 / 0
[SEMANTIC ERROR] division by zero detected at compile time
```

## Debug mode

`--debug` prints every stage of the pipeline:

```text
$ python main.py --debug prog.mini   # x = 2 + 3 * 4 / print x

── Tokens ──────────────────────────────────────────
  [ID:x]
  [ASSIGN:=]
  [INT:2]
  [PLUS:+]
  [INT:3]
  [MUL:*]
  [INT:4]
  [NEWLINE]
  [PRINT]
  [ID:x]
  [NEWLINE]
  [EOF]

── AST ─────────────────────────────────────────────
Program
    Assign: x =
        BinOp: +
            Num(2)
            BinOp: *
                Num(3)
                Num(4)
    Print:
        Var(x)

── Output ──────────────────────────────────────────
14
```

`sample.mini` exercises every language feature: arithmetic, string concatenation, if/else, while loops (a countdown and the first 8 Fibonacci numbers) and comparisons. Run it with `python main.py sample.mini`.

## Project structure

```text
main.py          entry point: run a file, --debug, or --repl
lexer.py         tokenizer
parser.py        recursive-descent parser and AST node classes
interpreter.py   semantic analyzer and tree-walk interpreter
sample.mini      sample program covering every feature
```

Around 1,100 lines of Python in total, using only the standard library.
