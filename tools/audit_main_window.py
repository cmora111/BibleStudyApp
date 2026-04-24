#!/usr/bin/env python3
import ast
import re
from collections import Counter, defaultdict
from pathlib import Path

PATH = Path("app/ui/main_window.py")
src = PATH.read_text(encoding="utf-8")

print(f"Auditing {PATH}\n")

# ---- duplicate class methods ----
mod = ast.parse(src)
classes = [n for n in mod.body if isinstance(n, ast.ClassDef)]

for cls in classes:
    methods = [n.name for n in cls.body if isinstance(n, ast.FunctionDef)]
    counts = Counter(methods)
    dupes = {name: count for name, count in counts.items() if count > 1}

    print(f"Class {cls.name}:")
    if dupes:
        print("  Duplicate methods:")
        for name, count in sorted(dupes.items()):
            lines = [n.lineno for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == name]
            print(f"    {name}: {count} copies at lines {lines}")
    else:
        print("  No duplicate methods found.")

print()

# ---- top-level defs that probably fell out of class ----
top_defs = [n for n in mod.body if isinstance(n, ast.FunctionDef)]
if top_defs:
    print("Top-level functions found:")
    for n in top_defs:
        print(f"  line {n.lineno}: def {n.name}(...):")
else:
    print("No top-level functions found.")

print()

# ---- duplicate tag_bind bindings by widget/tag/event ----
bind_re = re.compile(
    r'(?P<widget>self\.\w+|\w+)\.tag_bind\(\s*'
    r'(?P<tag>[^,]+),\s*'
    r'(?P<event>["\']<[^"\']+>["\'])',
    re.MULTILINE,
)

bindings = defaultdict(list)
for match in bind_re.finditer(src):
    line = src.count("\n", 0, match.start()) + 1
    key = (
        match.group("widget").strip(),
        match.group("tag").strip(),
        match.group("event").strip(),
    )
    bindings[key].append(line)

dupe_binds = {k: v for k, v in bindings.items() if len(v) > 1}

if dupe_binds:
    print("Potential duplicate tag_bind calls:")
    for (widget, tag, event), lines in sorted(dupe_binds.items(), key=lambda x: x[1][0]):
        print(f"  {widget}.tag_bind({tag}, {event}) at lines {lines}")
else:
    print("No obvious duplicate tag_bind calls found.")

print()

# ---- suspicious direct semantic reader-open bindings ----
print("Semantic click routing checks:")
for i, line in enumerate(src.splitlines(), start=1):
    if "_open_semantic_hit_in_reader(h)" in line:
        print(f"  WARNING line {i}: direct semantic reader-open binding remains:")
        print(f"    {line.strip()}")

print("\nDone.")
