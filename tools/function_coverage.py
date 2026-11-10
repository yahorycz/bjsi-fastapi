"""Raport pokrycia dla WYBRANYCH FUNKCJI (a nie całych modułów).

coverage.py raportuje pokrycie dla całych plików. Moduły FastAPI zawierają wiele
funkcji, których nie testujemy, więc ten skrypt wycina z raportu JSON tylko linie
należące do wskazanych funkcji i pokazuje:
  * liczbę instrukcji, liczbę pominiętych instrukcji i % pokrycia,
  * numery i treść niepokrytych linii,
  * niepokryte gałęzie (jeśli pomiar był z --branch / --cov-branch),
  * (opcjonalnie, gdy raport ma konteksty) które testy wykonują które linie.

Użycie:
  pytest tests/test_fastapi_unit.py --cov=fastapi --cov-branch --cov-context=test
  coverage json --show-contexts -o coverage.json
  python tools/function_coverage.py coverage.json \
      fastapi/encoders.py:jsonable_encoder \
      fastapi/security/utils.py:get_authorization_scheme_param \
      fastapi/security/http.py:HTTPBasic.__call__

Cel "plik.py:*" oznacza cały plik.
"""
from __future__ import annotations

import ast
import json
import sys
from collections import defaultdict
from pathlib import Path


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def find_file_entry(report: dict, suffix: str) -> tuple[str, dict]:
    suffix = _norm(suffix)
    for name, entry in report["files"].items():
        if _norm(name).endswith(suffix):
            return name, entry
    raise SystemExit(f"Nie znaleziono pliku '{suffix}' w raporcie coverage.json")


def find_function_range(source: str, qualname: str) -> tuple[int, int]:
    """Zwraca (pierwsza_linia, ostatnia_linia) funkcji, np. 'HTTPBasic.__call__'."""
    if qualname == "*":
        return 1, len(source.splitlines())
    parts = qualname.split(".")
    nodes = ast.parse(source).body
    node = None
    for part in parts:
        node = next(
            (n for n in nodes
             if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.name == part),
            None,
        )
        if node is None:
            raise SystemExit(f"Nie znaleziono '{qualname}' w pliku")
        nodes = node.body
    start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
    return start, node.end_lineno


def ranges(numbers: list[int]) -> str:
    out, numbers = [], sorted(numbers)
    i = 0
    while i < len(numbers):
        j = i
        while j + 1 < len(numbers) and numbers[j + 1] == numbers[j] + 1:
            j += 1
        out.append(str(numbers[i]) if i == j else f"{numbers[i]}-{numbers[j]}")
        i = j + 1
    return ", ".join(out) or "-"


def clean_context(ctx: str) -> str:
    return ctx.split("|")[0]


def analyse(report: dict, target: str, show_contexts: bool = True) -> dict:
    file_suffix, _, qualname = target.partition(":")
    qualname = qualname or "*"
    filename, entry = find_file_entry(report, file_suffix)
    source = Path(filename).read_text(encoding="utf-8")
    lines = source.splitlines()
    first, last = find_function_range(source, qualname)
    inside = lambda n: first <= n <= last  # noqa: E731

    executed = sorted(n for n in entry["executed_lines"] if inside(n))
    missing = sorted(n for n in entry["missing_lines"] if inside(n))
    total = len(executed) + len(missing)
    missing_branches = [b for b in entry.get("missing_branches", []) if inside(b[0])]

    print("=" * 78)
    print(f"{target}   (linie {first}-{last} pliku {filename})")
    print("=" * 78)
    pct = 100.0 * len(executed) / total if total else 100.0
    print(f"Instrukcje: {total}   pokryte: {len(executed)}   NIEPOKRYTE: {len(missing)}   pokrycie: {pct:.1f}%")
    print(f"Niepokryte linie: {ranges(missing)}")
    for n in missing:
        print(f"   {n:>5} | {lines[n - 1].rstrip()}")
    if "missing_branches" in entry:
        print(f"Niepokryte gałęzie ({len(missing_branches)}):")
        for src, dst in missing_branches:
            dst_txt = "wyjście z funkcji" if dst < 0 else f"linia {dst}"
            print(f"   {src:>5} -> {dst_txt:<18} | {lines[src - 1].strip()}")

    contexts = entry.get("contexts")
    per_test: dict[str, set[int]] = defaultdict(set)
    if contexts and show_contexts:
        for line_no, ctx_list in contexts.items():
            n = int(line_no)
            if not inside(n):
                continue
            for ctx in ctx_list:
                ctx = clean_context(ctx)
                if ctx:
                    per_test[ctx].add(n)
        if per_test:
            print("\nPokrycie uzyskiwane przez POJEDYNCZE testy (od największego):")
            for name, hit in sorted(per_test.items(), key=lambda kv: (-len(kv[1]), kv[0])):
                print(f"   {len(hit):>3}/{total:<3} ({100 * len(hit) / total:5.1f}%)  {name}")
            print("\nKtóre testy wykonują poszczególne linie:")
            for n in executed:
                tests = sorted(t for t, hit in per_test.items() if n in hit)
                short = ", ".join(t.split("::")[-1] for t in tests[:4])
                more = f" (+{len(tests) - 4})" if len(tests) > 4 else ""
                print(f"   {n:>5} [{len(tests):>2} testów] {lines[n - 1].strip()[:45]:<45} <- {short}{more}")
    print()
    return {"target": target, "total": total, "missing": missing,
            "missing_branches": missing_branches, "per_test": per_test}


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        print(__doc__)
        raise SystemExit(1)
    report = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    results = [analyse(report, target) for target in argv[2:]]
    total = sum(r["total"] for r in results)
    missed = sum(len(r["missing"]) for r in results)
    print(f"SUMA dla badanych funkcji: {total} instrukcji, niepokryte: {missed}, "
          f"pokrycie: {100 * (total - missed) / total if total else 100:.1f}%")


if __name__ == "__main__":
    main(sys.argv)
