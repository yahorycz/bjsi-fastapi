"""Temat 2, Zadanie 2 - "Dla chętnych": NOWE testy dopisane po analizie pokrycia i mutacji.

Każdy test odpowiada na konkretną lukę znalezioną w analizie:
  * M5 (>= -> >) nie została wykryta, bo test porównywał Decimal("10") == 10,
    a 10.0 == 10 w Pythonie -> sprawdzamy także TYP wyniku,
  * niepokryte gałęzie jsonable_encoder: custom_encoder, dataclass, PurePath,
    obiekt niemożliwy do zakodowania (ValueError),
  * niepokryta gałąź HTTPBasic: niepoprawny base64 (wyjątek przy dekodowaniu),
    nagłówek WWW-Authenticate z parametrem realm.
"""
import asyncio
import dataclasses
from decimal import Decimal
from pathlib import PurePosixPath

import pytest
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBasic
from starlette.requests import Request


def make_request(headers):
    return Request({
        "type": "http", "method": "GET", "path": "/", "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    })


@pytest.mark.parametrize("value", [Decimal("10"), Decimal("0"), Decimal("1E+2")])
def test_decimal_without_fraction_is_encoded_as_int(value):
    result = jsonable_encoder(value)
    assert result == int(value)
    assert type(result) is int


def test_custom_encoder_has_priority():
    assert jsonable_encoder(Decimal("1.50"), custom_encoder={Decimal: str}) == "1.50"


def test_dataclass_is_encoded_as_dict():
    @dataclasses.dataclass
    class Point:
        x: int
        y: int

    assert jsonable_encoder(Point(1, 2)) == {"x": 1, "y": 2}


def test_path_is_encoded_as_string():
    assert jsonable_encoder(PurePosixPath("/tmp/plik.txt")) == "/tmp/plik.txt"


def test_unencodable_object_raises_value_error():
    with pytest.raises(ValueError):
        jsonable_encoder(object())


def test_http_basic_rejects_invalid_base64():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(HTTPBasic()(make_request({"Authorization": "Basic abc"})))
    assert exc_info.value.status_code == 401


def test_http_basic_realm_is_returned_in_www_authenticate_header():
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(HTTPBasic(realm="BJSI")(make_request({})))
    assert exc_info.value.headers["WWW-Authenticate"] == 'Basic realm="BJSI"'
