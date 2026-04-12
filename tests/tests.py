from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_card_html_fragment():
    # Sprawdzamy, czy serwer zwraca poprawny fragment HTML dla nowej notatki
    response = client.get("/card?type=notes")
    assert response.status_code == 200
    # Kluczowe: sprawdzamy czy w HTML jest to, czego oczekuje HTMX
    assert '<input type="hidden" name="type" value="notes">' in response.text
    assert 'placeholder="Zacznij pisać notatki..."' in response.text


def test_get_card_context_data():
    # Pytamy o wygenerowanie nowej karty typu 'notes'
    response = client.get("/card?type=notes")
    assert response.status_code == 200

    # WYCIĄGAMY DANE (KONTEKST) PRZEKAZANE DO SZABLONU!
    template_data = response.context

    # 1. Sprawdzamy czy przekazano w ogóle wymagane klucze
    assert "unique_id" in template_data
    assert "type" in template_data
    assert "data" in template_data

    # 2. Sprawdzamy czy wygenerowano unikalne ID (nie jest puste)
    assert len(template_data["unique_id"]) > 0

    # 3. Sprawdzamy czy typ karty jest prawidłowy
    assert template_data["type"] == "notes"

    # 4. Sprawdzamy czy wbudowany słownik 'data' ma poprawne wartości domyślne
    inner_data = template_data["data"]
    assert inner_data["level"] == 0
    assert inner_data["collapsed"] == "false"
    assert inner_data["list_type"] == "bullet"
