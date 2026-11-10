"""Temat 3, Zadanie 2 (Wariant A) - automatyzacja testów integracyjnych.

Badana integracja: routing FastAPI + walidacja Pydantic + Depends
+ moduł rezerwacji (BookingRepository) + moduł dostępności (AvailabilityService)
+ powiadomienia (Notifier).

Elementy RZECZYWISTE: aplikacja FastAPI, routing, walidacja, mechanizm Depends,
                      BookingRepository, AvailabilityService.
Elementy zastąpione ATRAPĄ: Notifier -> FakeNotifier (nie wysyłamy e-maili,
                      tylko zapisujemy wywołania, żeby móc je sprawdzić).
Izolacja: każdy test dostaje NOWE, puste repozytorium (fixture `repository`),
          a po teście nadpisania zależności są usuwane -> testy można uruchamiać
          wielokrotnie i w dowolnej kolejności.
"""
import pytest
from fastapi.testclient import TestClient

from app_example.main import BookingRepository, app, get_notifier, get_repository

DAY = "2026-12-24"


class FakeNotifier:
    """Atrapa (fake) usługi e-mail - zapamiętuje, o czym miała powiadomić."""

    def __init__(self) -> None:
        self.sent = []

    def booking_created(self, booking) -> None:
        self.sent.append(booking)


@pytest.fixture
def repository():
    return BookingRepository()          # stan początkowy: brak rezerwacji


@pytest.fixture
def notifier():
    return FakeNotifier()


@pytest.fixture
def client(repository, notifier):
    app.dependency_overrides[get_repository] = lambda: repository
    app.dependency_overrides[get_notifier] = lambda: notifier
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()    # sprzątanie po teście


def availability(client, room_id=1, day=DAY):
    response = client.get(f"/rooms/{room_id}/availability", params={"day": day})
    assert response.status_code == 200
    return response.json()["available"]


# --- S1: happy path - pełny cykl życia rezerwacji -----------------------------
def test_s1_happy_path_booking_lifecycle(client, repository, notifier):
    assert availability(client) is True                       # stan początkowy

    created = client.post("/bookings", json={"room_id": 1, "guest": "Jan Kowalski", "day": DAY})
    assert created.status_code == 201
    body = created.json()
    assert body == {"id": 1, "room_id": 1, "guest": "Jan Kowalski", "day": DAY}

    # integracja: API -> repozytorium -> moduł dostępności -> powiadomienia
    assert repository.size() == 1
    assert availability(client) is False
    assert [b.id for b in notifier.sent] == [1]

    assert client.get("/bookings/1").json() == body           # odczyt tej samej rezerwacji

    assert client.delete("/bookings/1").status_code == 204    # anulowanie
    assert availability(client) is True
    assert client.get("/bookings/1").status_code == 404


# --- S2: błąd - podwójna rezerwacja tego samego pokoju w tym samym dniu --------
def test_s2_double_booking_is_rejected(client, repository, notifier):
    payload = {"room_id": 2, "guest": "Anna", "day": DAY}
    assert client.post("/bookings", json=payload).status_code == 201

    second = client.post("/bookings", json={**payload, "guest": "Piotr"})
    assert second.status_code == 409
    assert repository.size() == 1          # druga rezerwacja NIE trafiła do repozytorium
    assert len(notifier.sent) == 1          # i NIE wysłano drugiego powiadomienia


# --- S3: błąd - niepoprawne dane przekazywane między elementami ---------------
@pytest.mark.parametrize(
    "payload",
    [
        {"room_id": "abc", "guest": "Jan", "day": DAY},          # zły typ
        {"room_id": 1, "guest": "Jan", "day": "2026-13-45"},     # niepoprawna data
        {"room_id": 1, "guest": "", "day": DAY},                 # pusty gość
        {"room_id": 0, "guest": "Jan", "day": DAY},              # room_id musi być > 0
        {"room_id": 1, "guest": "Jan"},                          # brak pola day
    ],
    ids=["room-not-int", "bad-date", "empty-guest", "room-zero", "missing-day"],
)
def test_s3_invalid_data_does_not_reach_repository(client, repository, notifier, payload):
    response = client.post("/bookings", json=payload)
    assert response.status_code == 422
    assert repository.size() == 0
    assert notifier.sent == []


# --- S4: błąd - pokój, który nie istnieje -------------------------------------
def test_s4_unknown_room_returns_404(client, repository):
    response = client.post("/bookings", json={"room_id": 99, "guest": "Jan", "day": DAY})
    assert response.status_code == 404
    assert repository.size() == 0


# --- S5: ten sam pokój w różne dni oraz różne pokoje w ten sam dzień ----------
def test_s5_independent_bookings_are_allowed(client, repository):
    assert client.post("/bookings", json={"room_id": 3, "guest": "A", "day": "2026-12-24"}).status_code == 201
    assert client.post("/bookings", json={"room_id": 3, "guest": "B", "day": "2026-12-25"}).status_code == 201
    assert client.post("/bookings", json={"room_id": 1, "guest": "C", "day": "2026-12-24"}).status_code == 201
    assert repository.size() == 3


# --- S6: anulowanie nieistniejącej rezerwacji ---------------------------------
def test_s6_cancel_nonexistent_booking_returns_404(client):
    assert client.delete("/bookings/123").status_code == 404


# --- izolacja: każdy test zaczyna od czystego stanu ---------------------------
def test_each_test_starts_with_empty_repository(client, repository):
    assert repository.size() == 0
    assert availability(client, room_id=2) is True
