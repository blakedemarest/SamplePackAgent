#!/usr/bin/env python3
"""
scripts/gitingest_export.py

Generates:
  1) A plaintext dump of the entire codebase (codebase.txt)
  2) A directory tree listing (tree.txt)

Ignores patterns from .gitignore plus any “venv” directory.
"""

import os
import fnmatch
from pathlib import Path

# ——————————————— CONFIG ————————————————
# PROJECT ROOT and OUTPUT DIRECTORY both point to SamplePackAgent
ROOT        = Path(r"C:\Users\Earth\BEDROT PRODUCTIONS\SamplePackAgent")
IGNORE_FILE = ROOT / ".gitignore"
EXTRA_IGNORES = ["venv/*", "*/venv/*"]
OUT_DIR      = ROOT
CODEBASE_DOC = OUT_DIR / "codebase.txt"
TREE_DOC     = OUT_DIR / "tree.txt"


def load_ignore_patterns():
    patterns = set(EXTRA_IGNORES)
    if IGNORE_FILE.exists():
        for line in IGNORE_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            patterns.add(line)
    return list(patterns)


def is_ignored(rel_path: str, patterns: list[str]) -> bool:
    for pat in patterns:
        if fnmatch.fnmatch(rel_path, pat):
            return True
    return False


def write_codebase(patterns: list[str]):
    with CODEBASE_DOC.open("w", encoding="utf-8") as out:
        for root, dirs, files in os.walk(ROOT):
            rel_dir = os.path.relpath(root, ROOT)
            if is_ignored(rel_dir + "/", patterns):
                dirs[:] = []
                continue

            for fname in files:
                rel_file = os.path.normpath(os.path.join(rel_dir, fname))
                if is_ignored(rel_file, patterns):
                    continue

                file_path = ROOT / rel_file
                out.write(f"--- {rel_file} ---\n")
                try:
                    text = file_path.read_text(encoding="utf-8")
                except Exception:
                    text = f"[Could not read file: {file_path}]\n"
                out.write(text + "\n\n")


def write_tree(patterns: list[str]):
    lines = []

    def recurse(dir_path: Path, prefix=""):
        entries = sorted(dir_path.iterdir())
        filtered = [e for e in entries if not is_ignored(str(e.relative_to(ROOT)), patterns)]
        for i, entry in enumerate(filtered):
            connector = "└── " if i == len(filtered) - 1 else "├── "
            lines.append(f"{prefix}{connector}{entry.name}")
            if entry.is_dir():
                extension = "    " if i == len(filtered) - 1 else "│   "
                recurse(entry, prefix + extension)

    lines.append(".")
    recurse(ROOT)
    with TREE_DOC.open("w", encoding="utf-8") as out:
        out.write("\n".join(lines))


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    patterns = load_ignore_patterns()
    write_codebase(patterns)
    write_tree(patterns)
    print(f"✅ Generated codebase at {CODEBASE_DOC}")
    print(f"✅ Generated tree view at {TREE_DOC}")


if __name__ == "__main__":
    main()
