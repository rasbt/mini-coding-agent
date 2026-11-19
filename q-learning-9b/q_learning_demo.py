"""Prepare a Lab 5 checkout for the Project 2 Q-learning demo."""

import argparse
import ast
import json
from pathlib import Path
import subprocess
import sys


NOTEBOOK = Path("q_learning.ipynb")
LEARNER = Path("learning_todos.py")
LEARNER_CELL = "learning-todos"
TRAINING_CELLS = ("imports", "environment", "parameters", LEARNER_CELL,
                  "policy-display", "cacc3ebd", "45565a49")


def write_notebook(notebook):
    NOTEBOOK.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def prepare(notebook, cell):
    lines = "".join(cell["source"]).splitlines(keepends=True)
    functions = ast.parse("".join(lines)).body
    for func in reversed(functions):
        if not isinstance(func, ast.FunctionDef) or not ast.get_docstring(func):
            raise ValueError("Expected documented learner functions in the notebook.")
        docstring = func.body[0]
        lines[docstring.end_lineno:func.end_lineno] = [
            f'    raise NotImplementedError("TODO: implement {func.name}")\n',
        ]
    with LEARNER.open("x", encoding="utf-8") as output:
        output.writelines(lines)
    cell["source"] = lines
    for entry in notebook["cells"]:
        if entry["cell_type"] == "code":
            entry["execution_count"] = None
            entry["outputs"] = []
    write_notebook(notebook)
    Path("results.json").unlink(missing_ok=True)


def sync(notebook, cell):
    source = LEARNER.read_text(encoding="utf-8")
    ast.parse(source, filename=str(LEARNER))
    cell["source"] = source.splitlines(keepends=True)
    write_notebook(notebook)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "sync", "verify"))
    args = parser.parse_args()
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    cells = {cell.get("id"): cell for cell in notebook["cells"]}
    learner = cells[LEARNER_CELL]
    if args.action == "prepare":
        prepare(notebook, learner)
        return

    sync(notebook, learner)
    if args.action == "verify":
        subprocess.run([sys.executable, "scripts/check_project.py"], check=True)
        subprocess.run([sys.executable, "-m", "unittest", "scripts.test_q_learning"], check=True)
        namespace = {"__name__": "q_learning_notebook"}
        for cell_id in TRAINING_CELLS:
            source = "".join(cells[cell_id]["source"])
            exec(compile(source, f"<{cell_id}>", "exec"), namespace)


if __name__ == "__main__":
    main()
