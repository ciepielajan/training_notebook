from collections import defaultdict
from pprint import pprint
import tempfile
from fastapi import UploadFile, File
from fastapi.responses import FileResponse
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import secrets
import json
from pathlib import Path
import yaml
import os

# 1. Wczytujemy konfigurację z pliku config.yaml
with open("config.yaml", "r", encoding="utf-8") as f:
    config = yaml.safe_load(f)

DATA_DIR = Path(config.get("data_dir"))


def get_recent_workouts():
    """Funkcja pobiera pliki JSON z folderu i sortuje je od najnowszego."""
    if not DATA_DIR.exists() or not DATA_DIR.is_dir():
        print(f"BŁĄD: Folder z danymi nie istnieje: {DATA_DIR}")
        return []

    # Pobieramy tylko pliki .json i sortujemy po dacie modyfikacji (od najnowszego)
    files = sorted(DATA_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)

    workouts = []
    for f in files:
        workouts.append({"filename": f.name, "name": f.stem})
    return workouts


def load_settings(path):
    """Wczytuje opcje z pliku YAML. Jeśli błąd, zwraca domyślne."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"⚠️ Plik {path} nie istnieje.")
    except:
        print("⚠️ Nieznany błąd")


SETTINGS = load_settings(path="config.yaml")

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/test", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("test.html", {"request": request})


@app.get("/field-fragment", response_class=HTMLResponse)
async def field_fragment(request: Request):
    # zwraca fragment HTML (jedna linia pól)
    return templates.TemplateResponse("_fields_fragment.html", {"request": request})


@app.get("/card", response_class=HTMLResponse)
async def field_fragment(
    request: Request,
    size: str = "",
    type: str = "running",
    value: str = "",
    label: str = "",
):
    unique_id = secrets.token_hex(4)

    activities = SETTINGS.get("activities", {})
    options_list = activities.get(type) or []

    return templates.TemplateResponse(
        "_card.html",
        {
            "request": request,
            "unique_id": unique_id,
            "type": type,
            "data": {
                "activity": {"value": value, "label": label},
                "details": [],
                "size": size,
            },
            "options": options_list,
        },
    )


@app.get("/input", response_class=HTMLResponse)
async def add_input(request: Request, type: str):
    # Mapa etykiet
    labels_map = {
        "distance": "Dystans [m]",
        "time": "Czas [s]",
        "quantity": "Liczba powtórzeń",
        "weight": "Ciężar [kg]",
    }

    return templates.TemplateResponse(
        "inputs/detail.html",
        {
            "request": request,
            "values": {"value": "", "type": type, "label": labels_map.get(type, type)},
        },
    )


@app.get("/card/custom_field", response_class=HTMLResponse)
async def custom_field(request: Request, label: str = ""):
    return templates.TemplateResponse(
        "inputs/custom_detail.html",
        {
            "request": request,
            "values": {"value": "", "label": label},
        },
    )


@app.get("/test_form", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("test_form.html", {"request": request})


@app.post("/add-input/{input_type}", response_class=HTMLResponse)
def add_input(input_type: str):
    if input_type not in {"text", "number"}:
        return ""

    return f"""
    <div class="field">
      <input type="{input_type}" name="value" value="1">
      <input type="hidden" name="type" value="{input_type}">
    </div>
    """


@app.post("/card/repetition/{uid}", response_class=HTMLResponse)
async def duplicate_series(request: Request, uid: str):
    form_data = await request.form()
    json_body = form_data.get("json_body")

    if not json_body:
        return HTMLResponse("Błąd: Brak danych strukturalnych", status_code=400)

    data_tree = json.loads(json_body)
    html_content = ""

    # 1. Znajdźmy naszą kartę w drzewie za pomocą uid (które u Ciebie jest polem 'id')
    target_card = None
    for card in data_tree.get("items", []):
        if card.get("id") == uid:
            target_card = card
            break

    if not target_card:
        return HTMLResponse("Nie znaleziono karty o podanym ID", status_code=404)

    # 2. Wyciągamy detale.
    # Zgodnie z Twoim nowym JSONem: karta -> items[0] (running) -> details
    # Używamy get(..., []) aby uniknąć błędów
    content_node = target_card.get("items", [{}])[0]
    labels_to_duplicate = []

    # Pobieramy etykiety z sekcji 'details'
    # Pamiętaj, że JS nazwał to 'details' dzięki data-children-key
    for detail in content_node.get("details", []):
        lbl = detail.get("label")
        if lbl and lbl not in labels_to_duplicate:
            labels_to_duplicate.append(lbl)

    # 3. Generujemy HTML dla nowych pól (pustych)
    for lbl in labels_to_duplicate:
        html_content += templates.get_template("inputs/custom_detail.html").render(
            {
                "request": request,
                "uid": uid,
                "values": {
                    "value": "",
                    "label": lbl,
                    "type": "custom",
                },
            }
        )

    return HTMLResponse(content=html_content)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # Twoje dotychczasowe kody budujące cards_list...

    file_path = "data/training_data (10).json"

    try:
        # 1. Wczytujemy plik z dysku
        with open(file_path, "r", encoding="utf-8") as f:
            spider_json = json.load(f)

        # 2. Przetwarzamy dane naszą nową funkcją
        cards_to_render = process_spider_json(spider_json)

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"OSTRZEŻENIE: Nie można wczytać domyślnego pliku: {e}")
        cards_to_render = []

    # 1. Pobieramy listę plików z Twojego dysku
    recent_workouts = get_recent_workouts()

    # 2. Dodajemy ją do kontekstu
    context = {"request": request, "cards_list": cards_to_render, "recent_workouts": recent_workouts}
    return templates.TemplateResponse("index_form.html", context)


# Upewnij się, że masz zdefiniowane DATA_DIR gdzieś na górze pliku, np:
# DATA_DIR = Path("/home/janek/Dokumenty/my/training_notebook/data")


@app.get("/load_workout/{filename}", response_class=HTMLResponse)
async def load_workout(request: Request, filename: str):
    # Tworzymy pełną ścieżkę do klikniętego pliku
    file_path = DATA_DIR / filename

    try:
        # 1. Wczytujemy plik z dysku
        with open(file_path, "r", encoding="utf-8") as f:
            spider_json = json.load(f)

        # 2. Przetwarzamy dane funkcją
        cards_to_render = process_spider_json(spider_json)

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"BŁĄD: Nie można wczytać pliku {filename}: {e}")
        cards_to_render = []

    # 3. Zwracamy TYLKO wyrenderowane karty (dzięki temu HTMX płynnie podmieni środek strony)
    context = {"request": request, "cards_list": cards_to_render}
    return templates.TemplateResponse("_cards_list.html", context)


@app.post("/load", response_class=HTMLResponse)
async def load(request: Request, file: UploadFile = File(...)):
    content = await file.read()
    spider_json = json.loads(content)

    # Korzystamy z tej samej logiki transformacji
    processed_cards = process_spider_json(spider_json)

    final_html = ""
    for card in processed_cards:
        final_html += templates.get_template("_card.html").render(
            {"request": request, **card}  # Rozpakowuje unique_id, type, data, options
        )

    return final_html


@app.post("/save")
async def save(request: Request):
    form = await request.form()
    json_body = form.get("json_body")

    if not json_body:
        return HTMLResponse("Błąd: Pusty formularz", status_code=400)

    try:
        # 1. Parsujemy string JSON z formularza na obiekt Pythona
        data_structure = json.loads(json_body)

        # 2. Zapisujemy do pliku z wcięciami (indent=4) i polskimi znakami
        with open("training_data.json", "w", encoding="utf-8") as f:
            json.dump(data_structure, f, ensure_ascii=False, indent=4)

        return FileResponse("training_data.json", media_type="application/json", filename="training_data.json")

    except Exception as e:
        return HTMLResponse(f"Błąd zapisu: {e}", status_code=500)


def process_spider_json(spider_data):
    """Przetwarza surowy JSON z pająka na listę kart gotową do renderowania."""
    processed_cards = []

    for card in spider_data.get("items", []):
        # 1. Wyciągamy kontener danych
        if card.get("items") and len(card["items"]) > 0:
            data_obj = card["items"][0]
        else:
            data_obj = card

        # 2. Ustalamy typ karty
        card_type = data_obj.get("type") or card.get("type")

        # 3. Ujednolicenie DEDYKOWANE dla poszczególnych typów
        if card_type in ["running", "exercise", "running2"]:
            data_obj["activity"] = {"value": data_obj.get("head", ""), "label": data_obj.get("label", "")}
            # Upewniamy się, że struktura jest poprawna dla pętli w Jinja
            if card_type == "running2":
                if not isinstance(data_obj.get("sets"), list):
                    data_obj["sets"] = []
            else:
                if not isinstance(data_obj.get("details"), list):
                    data_obj["details"] = []

        # UWAGA: Dla 'table' i 'text' nie robimy nic!
        # Zostawiamy dane płasko, tak jak zapisał je pająk.

        processed_cards.append(
            {
                "unique_id": secrets.token_hex(4),
                "type": card_type,
                "data": data_obj,
                "options": SETTINGS.get("activities", {}).get(card_type, []),
            }
        )
    return processed_cards


@app.post("/card/table/action/{uid}", response_class=HTMLResponse)
async def table_action(request: Request, uid: str):
    form = await request.form()
    action = form.get("action")

    # 1. Zbieramy aktualne dane z tabeli
    data = {}
    for key, value in form.multi_items():
        data[key] = value

    num_rows = int(data.get("num_rows", 2))
    num_cols = int(data.get("num_cols", 4))

    # 2. DODAJ KOLUMNĘ
    if action == "add_col":
        col_idx = int(form.get("col_index", 1))
        col_name = form.get("col_name", "")
        col_width = form.get("col_width", "")

        # Przesuwamy dane w prawo
        for c in range(num_cols, col_idx, -1):
            data[f"h{c+1}"] = data.get(f"h{c}", "")
            data[f"w{c+1}"] = data.get(f"w{c}", "")
            for r in range(1, num_rows + 1):
                data[f"r{r}c{c+1}"] = data.get(f"r{r}c{c}", "")
                data[f"m_r{r}c{c+1}"] = data.get(f"m_r{r}c{c}", "")  # <--- NOWOŚĆ: Przesuwamy info o złączeniu

        # Wstawiamy nową kolumnę
        data[f"h{col_idx+1}"] = col_name
        data[f"w{col_idx+1}"] = col_width
        for r in range(1, num_rows + 1):
            data[f"r{r}c{col_idx+1}"] = ""
            data.pop(f"m_r{r}c{col_idx+1}", None)  # <--- NOWOŚĆ: Nowa kolumna na pewno nie jest złączona

        data["num_cols"] = num_cols + 1

    # 3. USUŃ KOLUMNĘ
    elif action == "remove_col":
        col_idx = int(form.get("col_index", 1))

        if num_cols > 1:
            # Przesuwamy w lewo
            for c in range(col_idx, num_cols):
                data[f"h{c}"] = data.get(f"h{c+1}", "")
                data[f"w{c}"] = data.get(f"w{c+1}", "")
                for r in range(1, num_rows + 1):
                    data[f"r{r}c{c}"] = data.get(f"r{r}c{c+1}", "")
                    data[f"m_r{r}c{c}"] = data.get(f"m_r{r}c{c+1}", "")  # <--- NOWOŚĆ: Przesuwamy info o złączeniu

            data.pop(f"h{num_cols}", None)
            data.pop(f"w{num_cols}", None)
            for r in range(1, num_rows + 1):
                data.pop(f"r{r}c{num_cols}", None)  # <--- POPRAWKA BŁĘDU: Było r{num_rows}, a powinno być r{r}
                data.pop(f"m_r{r}c{num_cols}", None)  # <--- NOWOŚĆ: Czyścimy info o złączeniu z usuniętej kolumny

            data["num_cols"] = num_cols - 1

    # 4. DODAJ WIERSZ (Na samym dole tabeli)
    elif action == "add_row":
        data["num_rows"] = num_rows + 1

    # 5. DODAJ WIERSZ PONIŻEJ
    elif action == "add_row_below":
        row_idx = int(form.get("row_index", 1))

        # Przesuwamy wszystkie wiersze od dołu do 'row_idx' o jeden w dół
        for r in range(num_rows, row_idx, -1):
            for c in range(1, num_cols + 1):
                data[f"r{r+1}c{c}"] = data.get(f"r{r}c{c}", "")
                data[f"m_r{r+1}c{c}"] = data.get(f"m_r{r}c{c}", "")  # <--- NOWOŚĆ: Złączenia jadą w dół z wierszem

        # Czyścimy nowo powstały wiersz
        for c in range(1, num_cols + 1):
            data[f"r{row_idx+1}c{c}"] = ""
            data.pop(f"m_r{row_idx+1}c{c}", None)  # <--- NOWOŚĆ: Nowy wiersz domyślnie nie jest z niczym złączony

        # Zwiększamy licznik wierszy
        data["num_rows"] = num_rows + 1

    # 6. USUŃ WIERSZ (ĆWICZENIE)
    elif action == "remove_row":
        row_idx = int(form.get("row_index", 1))

        if num_rows > 1:
            # Przesuwamy dane w górę
            for r in range(row_idx, num_rows):
                for c in range(1, num_cols + 1):
                    data[f"r{r}c{c}"] = data.get(f"r{r+1}c{c}", "")
                    data[f"m_r{r}c{c}"] = data.get(f"m_r{r+1}c{c}", "")  # <--- NOWOŚĆ: Złączenia jadą w górę

            # Usuwamy "osierocone" dane z ostatniego wiersza
            for c in range(1, num_cols + 1):
                data.pop(f"r{num_rows}c{c}", None)
                data.pop(f"m_r{num_rows}c{c}", None)  # <--- NOWOŚĆ

            # Zmniejszamy licznik wierszy
            data["num_rows"] = num_rows - 1

    # ==========================================
    # 7. NOWOŚĆ: ZGRUPUJ Z PONIŻSZYM (Super-serie)
    # ==========================================
    elif action == "group_below":
        r = int(form.get("row_index", 1))
        c = int(form.get("col_index", 1))

        # Szukamy pierwszego "wolnego" wiersza poniżej bieżącej grupy
        target_r = r + 1
        while target_r <= num_rows and data.get(f"m_r{target_r}c{c}") == "1":
            target_r += 1

        if target_r <= num_rows:
            data[f"m_r{target_r}c{c}"] = "1"

    # ==========================================
    # 8. NOWOŚĆ: ROZŁĄCZ GRUPĘ
    # ==========================================
    elif action == "ungroup":
        r = int(form.get("row_index", 1))
        c = int(form.get("col_index", 1))

        # Zdejmujemy flagę zgrupowania ("1") ze wszystkich podpiętych wierszy poniżej
        target_r = r + 1
        while target_r <= num_rows and data.get(f"m_r{target_r}c{c}") == "1":
            data.pop(f"m_r{target_r}c{c}", None)
            target_r += 1

    # Renderujemy z powrotem cały szablon tabeli z nowymi danymi
    context = {
        "request": request,
        "unique_id": uid,
        "data": data,
    }
    return templates.TemplateResponse("exercises/table.html", context)
