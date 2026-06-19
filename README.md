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
