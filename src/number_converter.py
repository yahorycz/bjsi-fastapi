"""Zamiana liczby całkowitej z przedziału <0, 999 999> na jej polską nazwę.

Implementacja referencyjna, na której uruchamiane są testy z pliku
number_converter_tester.py (Temat 1, Zadanie 1).
"""

UNITS = ["", "jeden", "dwa", "trzy", "cztery", "pięć", "sześć", "siedem", "osiem", "dziewięć"]
TEENS = [
    "dziesięć", "jedenaście", "dwanaście", "trzynaście", "czternaście",
    "piętnaście", "szesnaście", "siedemnaście", "osiemnaście", "dziewiętnaście",
]
TENS = [
    "", "", "dwadzieścia", "trzydzieści", "czterdzieści", "pięćdziesiąt",
    "sześćdziesiąt", "siedemdziesiąt", "osiemdziesiąt", "dziewięćdziesiąt",
]
HUNDREDS = [
    "", "sto", "dwieście", "trzysta", "czterysta", "pięćset",
    "sześćset", "siedemset", "osiemset", "dziewięćset",
]

MIN_VALUE = 0
MAX_VALUE = 999_999


def _below_thousand(n: int) -> list[str]:
    """Słowa dla liczby 0..999 (dla 0 zwraca pustą listę)."""
    words = []
    hundreds, rest = divmod(n, 100)
    if hundreds:
        words.append(HUNDREDS[hundreds])
    if 10 <= rest <= 19:
        words.append(TEENS[rest - 10])
    else:
        tens, units = divmod(rest, 10)
        if tens:
            words.append(TENS[tens])
        if units:
            words.append(UNITS[units])
    return words


def _thousands_word(n: int) -> str:
    """Poprawna forma słowa 'tysiąc' dla liczby tysięcy n (1..999)."""
    if n == 1:
        return "tysiąc"
    last_two = n % 100
    last = n % 10
    if 2 <= last <= 4 and not 12 <= last_two <= 14:
        return "tysiące"
    return "tysięcy"


def convert_to_polish_name(number: int) -> str:
    if isinstance(number, bool) or not isinstance(number, int):
        raise TypeError("number musi być liczbą całkowitą (int)")
    if number < MIN_VALUE or number > MAX_VALUE:
        raise ValueError(f"number musi należeć do przedziału <{MIN_VALUE}, {MAX_VALUE}>")
    if number == 0:
        return "zero"

    thousands, rest = divmod(number, 1000)
    words = []
    if thousands:
        if thousands > 1:
            words.extend(_below_thousand(thousands))
        words.append(_thousands_word(thousands))
    words.extend(_below_thousand(rest))
    return " ".join(words)
