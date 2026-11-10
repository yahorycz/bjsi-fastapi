"""Temat 2, Zadanie 2 - niewielkie kontrolowane zmiany (mutacje) w badanych funkcjach FastAPI.

Dla każdej zmiany skrypt:
  1. kopiuje zainstalowany pakiet `fastapi` do katalogu tymczasowego,
  2. wprowadza w kopii JEDNĄ zmianę (np. `>=` -> `>`),
  3. uruchamia CAŁY zestaw testów jednostkowych na zmienionej kopii,
  4. sprawdza, czy testy wykryły zmianę i które testy ją wykryły,
  5. usuwa kopię -> kolejna zmiana startuje znowu od ORYGINALNEJ implementacji.
Oryginalna biblioteka w site-packages nigdy nie jest modyfikowana.

Użycie:
  python tools/mutation_runner.py                       # domyślnie tests/test_fastapi_unit.py
  python tools/mutation_runner.py tests/test_fastapi_unit.py tests/test_fastapi_unit_extra.py
"""
from __future__ import annotations

import difflib
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Mutation:
    id: str
    file: str          # ścieżka względem katalogu pakietu fastapi
    find: str          # fragment oryginalnego kodu
    replace: str       # fragment po zmianie
    kind: str          # rodzaj zmiany
    description: str


MUTATIONS = [
    Mutation("M1", "security/utils.py", "if not authorization_header_value:", "if authorization_header_value:",
             "odwrócenie warunku", "get_authorization_scheme_param: zanegowany warunek pustego nagłówka"),
    Mutation("M2", "security/utils.py", 'partition(" ")', 'partition(":")',
             "zmiana wartości (separator)", "get_authorization_scheme_param: podział po ':' zamiast spacji"),
    Mutation("M3", "security/utils.py", "return scheme, param", "return param, scheme",
             "zmiana zwracanej wartości", "get_authorization_scheme_param: zamiana kolejności wyniku"),
    Mutation("M4", "security/utils.py", "if not authorization_header_value:",
             "if authorization_header_value is None:",
             "zmiana warunku", "get_authorization_scheme_param: tylko None traktowany jako pusty nagłówek"),
    Mutation("M5", "encoders.py", "exponent >= 0", "exponent > 0",
             "zmiana wartości granicznej (>= na >)", "decimal_encoder: Decimal z wykładnikiem 0 -> float zamiast int"),
    Mutation("M6", "encoders.py", "(value is not None or not exclude_none)",
             "(value is not None and not exclude_none)",
             "zamiana or na and", "jsonable_encoder: obsługa exclude_none w słownikach"),
    Mutation("M7", "security/http.py", 'scheme.lower() != "basic"', 'scheme.lower() == "basic"',
             "odwrócenie warunku", "HTTPBasic.__call__: sprawdzenie schematu 'Basic'"),
    Mutation("M8", "security/http.py", "if not separator:", "if False:",
             "usunięcie zgłaszanego wyjątku", "HTTPBasic.__call__: brak błędu 401 przy braku ':'"),
]


def package_dir(name: str) -> Path:
    spec = importlib.util.find_spec(name)
    if spec is None or not spec.submodule_search_locations:
        raise SystemExit(f"Pakiet {name} nie jest zainstalowany (pip install {name})")
    return Path(list(spec.submodule_search_locations)[0])


def run_tests(test_files: list[str], extra_path: Path | None) -> tuple[int, list[str], str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if extra_path is not None:
        env["PYTHONPATH"] = str(extra_path) + os.pathsep + env.get("PYTHONPATH", "")
    cmd = [sys.executable, "-m", "pytest", *test_files, "-q", "-rf", "-p", "no:cacheprovider", "--no-header"]
    proc = subprocess.run(cmd, capture_output=True, text=True, env=env)
    out = proc.stdout + proc.stderr
    failed = [line.split(" ", 1)[1].split(" - ")[0] for line in out.splitlines() if line.startswith("FAILED ")]
    summary = next((l for l in reversed(out.splitlines()) if " in " in l and ("passed" in l or "failed" in l or "error" in l)), "")
    return proc.returncode, failed, summary.strip("= ")


def check_import_location(extra_path: Path) -> str:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(extra_path) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run([sys.executable, "-c", "import fastapi; print(fastapi.__file__)"],
                          capture_output=True, text=True, env=env)
    return proc.stdout.strip()


def main(test_files: list[str]) -> None:
    original = package_dir("fastapi")
    print(f"Oryginalny pakiet: {original}")
    code, failed, summary = run_tests(test_files, None)
    print(f"Przebieg bazowy (bez zmian): {summary}")
    if code != 0:
        print("UWAGA: testy nie przechodzą na oryginalnym kodzie - najpierw je popraw!")
        print("\n".join(failed))
        return

    rows = []
    for m in MUTATIONS:
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "fastapi"
            shutil.copytree(original, copy, ignore=shutil.ignore_patterns("__pycache__"))
            target = copy / m.file
            text = target.read_text(encoding="utf-8")
            occurrences = text.count(m.find)
            print("\n" + "-" * 78)
            print(f"{m.id}: {m.description}  [{m.kind}]")
            if occurrences == 0:
                print("   POMINIĘTO - ten fragment nie występuje w zainstalowanej wersji FastAPI")
                rows.append((m, "POMINIĘTO", []))
                continue
            mutated = text.replace(m.find, m.replace, 1)
            target.write_text(mutated, encoding="utf-8")
            for line in difflib.unified_diff(text.splitlines(), mutated.splitlines(), lineterm="", n=0):
                if line.startswith(("-", "+")) and not line.startswith(("---", "+++")):
                    print(f"   {line.strip()}")
            if not check_import_location(Path(tmp)).startswith(str(copy)):
                print("   UWAGA: testy nie importują zmienionej kopii - wynik niewiarygodny")
            code, failed, summary = run_tests(test_files, Path(tmp))
            status = "WYKRYTA" if code != 0 else "NIEWYKRYTA"
            print(f"   Wynik testów: {summary}")
            print(f"   ZMIANA {status}" + (f" przez {len(failed)} test(y):" if failed else ""))
            for name in failed:
                print(f"      - {name}")
            rows.append((m, status, failed))

    print("\n" + "=" * 78)
    print(f"{'ID':<4} {'Wynik':<11} {'Wykryło testów':<15} Zmiana")
    for m, status, failed in rows:
        print(f"{m.id:<4} {status:<11} {len(failed):<15} {m.find}  ->  {m.replace}")
    applied = [r for r in rows if r[1] != "POMINIĘTO"]
    killed = sum(1 for r in applied if r[1] == "WYKRYTA")
    if applied:
        print(f"\nWykryte zmiany: {killed}/{len(applied)} ({100 * killed / len(applied):.0f}%)")


if __name__ == "__main__":
    main(sys.argv[1:] or ["tests/test_fastapi_unit.py"])
