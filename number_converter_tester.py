"""Temat 1, Zadanie 1 - przypadki testowe (czarnoskrzynkowe) dla funkcji
convert_to_polish_name(number: int) -> str, obsługującej liczby z przedziału <0, 999 999>.

Przypadki zaprojektowano technikami:
  * podział na klasy równoważności (jedności, "nastki", dziesiątki, setki, tysiące,
    poprawne / niepoprawne wartości),
  * analiza wartości granicznych (0, 999 999, -1, 1 000 000, 9/10, 19/20, 99/100, 999/1000),
  * szczególne reguły języka polskiego (tysiąc / tysiące / tysięcy, dwieście, pięćset...).

Temat 2, Zadanie 1: jeśli prowadzący udostępnił plik number_converter_white_box.py,
wystarczy umieścić go obok tego pliku - zostanie zaimportowany zamiast implementacji z src/.
"""
import pytest

try:  # implementacja prowadzącego (Temat 2 - "white box")
    from number_converter_white_box import convert_to_polish_name
except ImportError:  # własna implementacja referencyjna
    from src.number_converter import convert_to_polish_name


@pytest.mark.parametrize(
    ("number", "expected"),
    [
        # --- granica dolna i jedności (klasa 0-9) ---
        (0, "zero"),
        (1, "jeden"),
        (5, "pięć"),
        (9, "dziewięć"),
        # --- "nastki" (klasa 10-19, nieregularne nazwy) ---
        (10, "dziesięć"),
        (11, "jedenaście"),
        (14, "czternaście"),
        (19, "dziewiętnaście"),
        # --- dziesiątki (klasa 20-99) ---
        (20, "dwadzieścia"),
        (21, "dwadzieścia jeden"),
        (45, "czterdzieści pięć"),
        (99, "dziewięćdziesiąt dziewięć"),
        # --- setki (klasa 100-999, nieregularne: dwieście, trzysta, pięćset) ---
        (100, "sto"),
        (101, "sto jeden"),
        (110, "sto dziesięć"),
        (115, "sto piętnaście"),
        (200, "dwieście"),
        (300, "trzysta"),
        (500, "pięćset"),
        (999, "dziewięćset dziewięćdziesiąt dziewięć"),
        # --- tysiące: odmiana tysiąc / tysiące / tysięcy ---
        (1000, "tysiąc"),
        (1001, "tysiąc jeden"),
        (2000, "dwa tysiące"),
        (4000, "cztery tysiące"),
        (5000, "pięć tysięcy"),
        (12000, "dwanaście tysięcy"),
        (21000, "dwadzieścia jeden tysięcy"),
        (22000, "dwadzieścia dwa tysiące"),
        (25000, "dwadzieścia pięć tysięcy"),
        (100000, "sto tysięcy"),
        (112000, "sto dwanaście tysięcy"),
        (123456, "sto dwadzieścia trzy tysiące czterysta pięćdziesiąt sześć"),
        # --- granica górna ---
        (999999, "dziewięćset dziewięćdziesiąt dziewięć tysięcy dziewięćset dziewięćdziesiąt dziewięć"),
    ],
)
def test_convert_valid_number(number, expected):
    assert convert_to_polish_name(number) == expected


@pytest.mark.parametrize("number", [-1, -500, 1_000_000, 5_000_000])
def test_convert_number_outside_supported_range(number):
    with pytest.raises(ValueError):
        convert_to_polish_name(number)
