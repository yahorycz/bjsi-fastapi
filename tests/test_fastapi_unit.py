"""Temat 1, Zadanie 2 - testy jednostkowe (czarnoskrzynkowe) wybranych funkcji systemu FastAPI.

Wybrane funkcje (uzasadnienie w notebooku BJSI_raport.ipynb):
  1. fastapi.encoders.jsonable_encoder(obj, include, exclude, by_alias, exclude_none, ...) -> Any
     - przez tę funkcję przechodzi KAŻDA odpowiedź zwracana z endpointu.
  2. fastapi.security.utils.get_authorization_scheme_param(header: str | None) -> tuple[str, str]
     - rozbiór nagłówka Authorization, wykorzystywany przez wszystkie schematy bezpieczeństwa.
  3. fastapi.security.HTTPBasic.__call__(request) -> HTTPBasicCredentials | None
     - uwierzytelnianie HTTP Basic (dekodowanie loginu i hasła lub błąd 401).

Testy powstały tylko na podstawie wejścia i wyjścia (dokumentacji), bez analizy kodu.
"""
import asyncio
import base64
import datetime as dt
import enum
import uuid
from decimal import Decimal

import pytest
from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.security.utils import get_authorization_scheme_param
from pydantic import BaseModel, Field
from starlette.requests import Request


# ---------------------------------------------------------------------------
# Fixtures - dane testowe wielokrotnego użytku
# ---------------------------------------------------------------------------
class Color(enum.Enum):
    RED = "red"
    GREEN = "green"


class User(BaseModel):
    name: str
    email: str = Field(alias="emailAddress")
    age: int | None = None


@pytest.fixture
def sample_user():
    return User(name="Jan", emailAddress="jan@example.com", age=30)


@pytest.fixture
def basic_auth():
    return HTTPBasic()


def make_request(headers: dict[str, str]) -> Request:
    """Buduje minimalny obiekt żądania HTTP (bez uruchamiania serwera)."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    return Request(scope)


def basic_header(user_and_password: str) -> dict[str, str]:
    token = base64.b64encode(user_and_password.encode()).decode()
    return {"Authorization": f"Basic {token}"}


# ---------------------------------------------------------------------------
# 1. jsonable_encoder
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("value", [1, 1.5, "tekst", True, None])
def test_encoder_keeps_json_primitives_unchanged(value):
    assert jsonable_encoder(value) == value


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (dt.datetime(2026, 11, 10, 12, 30), "2026-11-10T12:30:00"),
        (dt.date(2026, 11, 10), "2026-11-10"),
        (uuid.UUID("12345678-1234-5678-1234-567812345678"), "12345678-1234-5678-1234-567812345678"),
        (Color.RED, "red"),
    ],
)
def test_encoder_converts_special_types_to_strings(value, expected):
    assert jsonable_encoder(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("10.50"), 10.5),
        (Decimal("10"), 10),
    ],
)
def test_encoder_converts_decimal_to_number(value, expected):
    assert jsonable_encoder(value) == expected


def test_encoder_converts_tuple_and_set_to_list():
    assert jsonable_encoder((1, 2, 3)) == [1, 2, 3]
    result = jsonable_encoder({3, 1, 2})
    assert isinstance(result, list)
    assert sorted(result) == [1, 2, 3]


def test_encoder_encodes_nested_structures():
    data = {"when": dt.date(2026, 1, 1), "items": [Decimal("1.5"), Color.GREEN]}
    assert jsonable_encoder(data) == {"when": "2026-01-01", "items": [1.5, "green"]}


def test_encoder_converts_pydantic_model_to_dict_using_aliases(sample_user):
    assert jsonable_encoder(sample_user) == {
        "name": "Jan",
        "emailAddress": "jan@example.com",
        "age": 30,
    }


def test_encoder_can_use_field_names_instead_of_aliases(sample_user):
    result = jsonable_encoder(sample_user, by_alias=False)
    assert result == {"name": "Jan", "email": "jan@example.com", "age": 30}


def test_encoder_include_and_exclude_fields(sample_user):
    assert jsonable_encoder(sample_user, include={"name"}) == {"name": "Jan"}
    assert "age" not in jsonable_encoder(sample_user, exclude={"age"})


def test_encoder_keeps_none_by_default_and_drops_it_with_exclude_none():
    data = {"a": 1, "b": None}
    assert jsonable_encoder(data) == {"a": 1, "b": None}
    assert jsonable_encoder(data, exclude_none=True) == {"a": 1}


# ---------------------------------------------------------------------------
# 2. get_authorization_scheme_param
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("header", "expected"),
    [
        ("Bearer abc123", ("Bearer", "abc123")),          # typowy nagłówek
        ("Basic dXNlcjpwYXNz", ("Basic", "dXNlcjpwYXNz")),  # inny schemat
        ("Bearer", ("Bearer", "")),                       # brak parametru
        ("Bearer a b c", ("Bearer", "a b c")),            # dzielenie tylko po 1. spacji
        ("", ("", "")),                                   # pusty nagłówek
        (None, ("", "")),                                 # brak nagłówka
    ],
)
def test_get_authorization_scheme_param(header, expected):
    assert get_authorization_scheme_param(header) == expected


# ---------------------------------------------------------------------------
# 3. HTTPBasic.__call__
# ---------------------------------------------------------------------------
def test_http_basic_returns_credentials_for_valid_header(basic_auth):
    request = make_request(basic_header("jan:tajne"))
    credentials = asyncio.run(basic_auth(request))
    assert isinstance(credentials, HTTPBasicCredentials)
    assert credentials.username == "jan"
    assert credentials.password == "tajne"


def test_http_basic_password_may_contain_colon(basic_auth):
    credentials = asyncio.run(basic_auth(make_request(basic_header("jan:ta:jne"))))
    assert credentials.username == "jan"
    assert credentials.password == "ta:jne"


@pytest.mark.parametrize(
    "headers",
    [
        {},                                    # brak nagłówka
        {"Authorization": "Bearer xyz"},       # inny schemat
        basic_header("janbezhasla"),           # brak dwukropka
        {"Authorization": "Basic"},            # brak danych po schemacie
    ],
    ids=["no-header", "wrong-scheme", "no-colon", "empty-param"],
)
def test_http_basic_rejects_invalid_credentials_with_401(basic_auth, headers):
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(basic_auth(make_request(headers)))
    assert exc_info.value.status_code == 401


def test_http_basic_without_auto_error_returns_none():
    security = HTTPBasic(auto_error=False)
    assert asyncio.run(security(make_request({}))) is None
