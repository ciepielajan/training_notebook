import yaml
import secrets
from pathlib import Path


def load_settings(path: str = "config.yaml") -> dict:
    """Wczytuje opcje z pliku YAML. Jeśli błąd, zwraca domyślne."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"⚠️ Plik {path} nie istnieje.")
        return {}
    except Exception as e:
        print(f"⚠️ Błąd wczytywania konfiguracji: {e}")
        return {}


# Globalna inicjalizacja konfiguracji
SETTINGS = load_settings()
DATA_DIR = Path(SETTINGS.get("data_dir", "outputs"))

# NOWOŚĆ: Ścieżka bazowa i folder z naszymi szablonami bloków
BASE_DIR = Path(__file__).resolve().parent
EXERCISES_DIR = BASE_DIR / "templates" / "exercises"


def get_recent_workouts() -> list:
    """Pobiera pliki JSON z folderu i sortuje je od najnowszego."""
    import os

    if not DATA_DIR.exists() or not DATA_DIR.is_dir():
        print(f"BŁĄD: Folder z danymi nie istnieje: {DATA_DIR}")
        return []

    files = sorted(DATA_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
    return [{"filename": f.name, "name": f.stem} for f in files]


def get_header_level(size_class: str) -> int:
    """Zwraca poziom nagłówka na podstawie klasy rozmiaru (np. fs-1 -> 1)."""
    if not size_class:
        return 0
    level_map = {"fs-1": 1, "fs-2": 2, "fs-3": 3, "fs-4": 4}
    return next((v for k, v in level_map.items() if k in size_class), 0)


def process_spider_json(spider_data: dict) -> list:
    """Przetwarza surowy JSON na strukturę gotową do wyrenderowania w szablonach."""
    processed_cards = []

    for card in spider_data.get("items", []):
        card_type = card.get("type")

        # Rozpakowujemy wiersz, JEŚLI ma wewnętrzną strukturę `items`
        if (
            card.get("items")
            and isinstance(card["items"], list)
            and len(card["items"]) > 0
            and isinstance(card["items"][0], dict)
        ):
            data_obj = card["items"][0]
        else:
            data_obj = card

        if not card_type:
            card_type = data_obj.get("type")

        # ==========================================
        # DYNAMICZNA WERYFIKACJA SZABLONU
        # ==========================================
        # Sprawdzamy czy fizycznie mamy plik, np. app/templates/exercises/running.html
        if not card_type or not (EXERCISES_DIR / f"{card_type}.html").is_file():
            data_obj["original_type"] = card_type or "brak"
            card_type = "deprecated"

        # Logika tylko dla aktualnie wspieranych, nietypowych bloków
        if card_type == "list":
            if "items" not in data_obj:
                data_obj["items"] = []

        # ZARZĄDZANIE WIDOCZNOŚCIĄ (level i collapsed)
        if card_type == "text":
            calc_level = get_header_level(data_obj.get("size", ""))
        else:
            calc_level = int(card.get("level", data_obj.get("level", 0)))

        c_val = card.get("collapsed", data_obj.get("collapsed", "false"))
        is_collapsed = "true" if str(c_val).lower() == "true" else "false"

        data_obj["level"] = calc_level
        data_obj["collapsed"] = is_collapsed

        processed_cards.append(
            {
                "unique_id": card.get("id") or secrets.token_hex(4),
                "type": card_type,
                "data": data_obj,
                "options": SETTINGS.get("activities", {}).get(card_type, []),
            }
        )
    return processed_cards
