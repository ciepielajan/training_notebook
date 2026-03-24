import json
import os
from urllib.parse import unquote
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
PATHS = SETTINGS.get("paths", {})
DATA_DIR = Path(PATHS.get("data_dir")).resolve()
BLOCKS_DIR = Path(PATHS.get("blocks_dir")).resolve()
INDEX_FILE = DATA_DIR / "index.json"


def load_index() -> dict:
    """Ładuje indeks plików (mapa: nazwa_pliku -> ładny_tytuł)."""
    if INDEX_FILE.exists():
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return {}
    return {}


def save_index(index_data: dict):
    """Zapisuje zaktualizowany indeks na dysk."""
    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        json.dump(index_data, f, ensure_ascii=False, indent=4)


def get_recent_files(file_prefix: str, include_deleted: bool = False) -> list:
    """Zwraca listę z indeksu, obsługując miękkie usuwanie i przypinanie."""
    index = load_index()
    filtered = []

    for k, v in index.items():
        if not k.startswith(file_prefix):
            continue

        # Zabezpieczenie (w locie transformuje stare wpisy ze stringów na słowniki)
        if isinstance(v, str):
            v = {"title": v, "is_deleted": False, "is_favorite": False, "project_ids": []}

        # Filtrowanie Kosza
        is_deleted = v.get("is_deleted", False)
        if is_deleted and not include_deleted:
            continue
        if not is_deleted and include_deleted:
            continue

        filtered.append(
            {
                "filename": k,
                "name": v.get("title", "Bez nazwy"),
                "is_favorite": v.get("is_favorite", False),
                "project_ids": v.get("project_ids", []),
            }
        )

    # Sortowanie: 1. Ulubione na górze, 2. Data modyfikacji dyskowej
    filtered.sort(
        key=lambda x: (
            x["is_favorite"],
            os.path.getmtime(DATA_DIR / x["filename"]) if (DATA_DIR / x["filename"]).exists() else 0,
        ),
        reverse=True,
    )

    return filtered


def get_header_level(size_class: str) -> int:
    """Zwraca poziom nagłówka na podstawie klasy rozmiaru (np. fs-1 -> 1)."""
    if not size_class:
        return 0
    level_map = {"fs-1": 1, "fs-2": 2, "fs-3": 3, "fs-4": 4}
    return next((v for k, v in level_map.items() if k in size_class), 0)


def process_spider_json(spider_data: dict) -> list:
    """Przetwarza surowy JSON na strukturę gotową do wyrenderowania w szablonach."""
    processed_cards = []

    # Kuloodporność: Zabezpieczenie przed brakiem 'items' lub innym typem danych
    items = spider_data.get("items", [])
    if not isinstance(items, list):
        items = []

    for card in items:
        # Kuloodporność: Ignorujemy np. stringi wbite w listę
        if not isinstance(card, dict):
            continue

        card_type = card.get("type")

        # Rozpakowujemy wiersz, JEŚLI ma wewnętrzną strukturę `items`
        if (
            "items" in card
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
        # KULOODPORNA WALIDACJA TYPU
        # ==========================================
        # Jeśli obiekt w tablicy w ogóle nie ma atrybutu "type", oznacza to, że to śmieci
        # lub metadane (np. zagnieżdżeni zawodnicy), a nie faktyczny blok treningowy.
        if not card_type or not isinstance(card_type, str) or not card_type.strip():
            continue

        # Sprawdzamy czy fizycznie mamy plik, np. app/templates/blocks/running.html
        if not (BLOCKS_DIR / f"{card_type}.html").is_file():
            # Skoro wpis miał type (np. "gym"), a szablonu nie ma - wtedy jest "deprecated"
            data_obj["original_type"] = card_type
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


def get_all_exercises() -> list:
    """
    Pobiera i parsuje ćwiczenia systemowe oraz użytkownika.
    Zwraca zunifikowaną listę słowników gotową do użycia w całej aplikacji.
    """
    sys_raw = SETTINGS.get("database", {}).get("system_items", "")
    usr_raw = SETTINGS.get("database", {}).get("user_items", "")

    exercises = []

    for source_label, raw_text in [("Systemowe", sys_raw), ("Własne", usr_raw)]:
        if not raw_text:
            continue

        for line in raw_text.split("\n"):
            if not line.strip():
                continue

            parts = [p.strip() for p in line.split(",")]
            name = parts[0]
            tags = [t for t in parts[1:] if t]  # Wyciągamy tagi i ignorujemy puste

            # Pierwszy tag traktujemy jako główną kategorię (do filtru w UI)
            category = tags[0].lower() if tags else ""

            exercises.append({"name": name, "source": source_label, "tags": tags, "category": category})

    return exercises
