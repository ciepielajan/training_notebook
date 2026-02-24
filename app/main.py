from fastapi import UploadFile, File
from fastapi.responses import RedirectResponse, Response
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import secrets
import datetime
import json
from pathlib import Path
import yaml
import os
import shutil


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
DATA_DIR = Path(SETTINGS.get("data_dir"))

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
# --- SENIOR TRICK: Udostępniamy SETTINGS globalnie dla wszystkich szablonów ---
templates.env.globals["SETTINGS"] = SETTINGS
app.mount("/static", StaticFiles(directory="app/static"), name="static")


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


def get_header_level(size_class: str) -> int:
    """Zwraca poziom nagłówka na podstawie klasy rozmiaru (np. fs-1 -> 1)."""
    if not size_class:
        return 0
    level_map = {"fs-1": 1, "fs-2": 2, "fs-3": 3, "fs-4": 4}
    return next((v for k, v in level_map.items() if k in size_class), 0)


def process_spider_json(spider_data):
    processed_cards = []

    for card in spider_data.get("items", []):
        card_type = card.get("type")

        # 1. SPRYTNE ROZPAKOWANIE DANYCH (Usunięto wadliwy wyjątek dla "list")
        # Rozpakowujemy wiersz, JEŚLI ma wewnętrzną strukturę `items` z danymi
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

        # 2. UJEDNOLICENIE I ZABEZPIECZENIE TYPÓW
        if card_type in ["running", "exercise", "running2", "gym", "gym2"]:
            data_obj["activity"] = {"value": data_obj.get("head", ""), "label": data_obj.get("label", "")}
            if card_type == "running2":
                if not isinstance(data_obj.get("sets"), list):
                    data_obj["sets"] = []
            else:
                if not isinstance(data_obj.get("details"), list):
                    data_obj["details"] = []

        if card_type == "list":
            if "items" not in data_obj:
                data_obj["items"] = []

        # 3. ZARZĄDZANIE WIDOCZNOŚCIĄ (level i collapsed)
        # Pobieramy stan z głównego 'card' (jeśli istnieje) lub jako fallback z 'data_obj'
        if card_type == "text":
            calc_level = get_header_level(data_obj.get("size", ""))
        else:
            calc_level = int(card.get("level", data_obj.get("level", 0)))

        c_val = card.get("collapsed", data_obj.get("collapsed", "false"))
        is_collapsed = "true" if str(c_val).lower() == "true" else "false"

        # Nadpisujemy wartości w data_obj, bo Jinja2 odczytuje to przez {{ data.level }}
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


@app.get("/test", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("test.html", {"request": request})


# @app.get("/field-fragment", response_class=HTMLResponse)
# async def field_fragment(request: Request):
#     # zwraca fragment HTML (jedna linia pól)
#     return templates.TemplateResponse("_fields_fragment.html", {"request": request})


@app.get("/card", response_class=HTMLResponse)
async def field_fragment(request: Request, size: str = "", type: str = "running", value: str = "", label: str = ""):
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
                "level": get_header_level(size) if type == "text" else 0,  # Używamy funkcji
                "collapsed": "false",
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


@app.get("/new_workout", response_class=HTMLResponse)
async def new_workout(request: Request):
    unique_id = secrets.token_hex(4)

    # Tworzymy Twój domyślny szablon startowy
    spider_json = {
        "items": [
            {"id": unique_id, "type": "text", "data": "", "head": "Trening Tempowy", "size": "fs-6"},
        ]
    }

    # Przetwarzamy dane naszą funkcją
    cards_to_render = process_spider_json(spider_json)

    # KLUCZOWE: Ustawiamy current_filename na pusty string ("").
    # Dzięki temu aplikacja wie, że to nowy, niezapisany plik i przy kliknięciu "Zapisz"
    # wygeneruje nową nazwę z datą, zamiast nadpisywać poprzedni trening!
    context = {"request": request, "cards_list": cards_to_render, "current_filename": ""}

    # Zwracamy tylko wyrenderowane karty, żeby HTMX mógł podmienić środek ekranu
    return templates.TemplateResponse("_cards_list.html", context)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    # 1. Pobieramy listę plików
    recent_workouts = get_recent_workouts()
    workouts_count = len(recent_workouts)

    # 2. Tworzymy elegancki Dashboard z dwóch osobnych kart (bez znaków \n)
    spider_json = {
        "items": [
            {
                "id": secrets.token_hex(4),
                "type": "text",
                "data": "",
                "head": "👋 Witaj w Notatniku Treningowym!",
                "size": "fs-5 fw-bold",
            },
            {
                "id": secrets.token_hex(4),
                "type": "text",
                "data": "",
                "head": "Wybierz trening z menu po lewej lub kliknij 'Nowy trening', aby zacząć.",
                "size": "fs-6",
            },
            {
                "id": secrets.token_hex(4),
                "type": "text",
                "data": "",
                "head": " ",
                "size": "fs-6",
            },
            {
                "id": secrets.token_hex(4),
                "type": "text",
                "data": "",
                "head": "📊 Podsumowanie",
                "size": "fs-6 fw-bold",
            },
            {
                "id": secrets.token_hex(4),
                "type": "text",
                "data": "",
                "head": f"Masz aktualnie {workouts_count} zapisanych treningów na dysku.",
                "size": "fs-6",
            },
        ]
    }

    # 3. Przetwarzamy na karty
    cards_to_render = process_spider_json(spider_json)

    # 4. Przekazujemy do kontekstu
    context = {
        "request": request,
        "cards_list": cards_to_render,
        "recent_workouts": recent_workouts,
        "current_filename": "",
    }
    return templates.TemplateResponse("index_form.html", context)


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
    context = {"request": request, "cards_list": cards_to_render, "current_filename": filename}
    return templates.TemplateResponse("_cards_list.html", context)


@app.post("/load", response_class=HTMLResponse)
async def load(request: Request, file: UploadFile = File(...)):
    content = await file.read()
    data = json.loads(content)

    # Korzystamy z tej samej logiki transformacji
    processed_cards = process_spider_json(data)

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

    # Pobieramy informacje o akcji i obecnie otwartym pliku z ukrytych inputów
    save_action = form.get("save_action", "save")  # domyślnie "save"
    current_filename = form.get("current_filename", "").strip()

    if not json_body:
        return HTMLResponse("Błąd: Pusty formularz", status_code=400)

    try:
        data_structure = json.loads(json_body)

        # ==========================================
        # AKCJA 3: EKSPORTUJ (Tylko pobieranie)
        # ==========================================
        if save_action == "export":
            # Tworzymy plik w pamięci i wysyłamy do przeglądarki (omijamy dysk serwera)
            json_str = json.dumps(data_structure, ensure_ascii=False, indent=4)
            dl_filename = current_filename if current_filename else "eksport_treningu.json"
            return Response(
                content=json_str,
                media_type="application/json",
                headers={"Content-Disposition": f"attachment; filename={dl_filename}"},
            )

        # ==========================================
        # AKCJA 1 i 2: ZAPISZ / ZAPISZ JAKO (Na dysk)
        # ==========================================

        # Sprawdzamy czy musimy wygenerować nowy plik
        is_new_file = False
        if save_action == "save_as" or not current_filename:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            target_filename = f"trening_{timestamp}.json"
            is_new_file = True
        else:
            target_filename = current_filename

        target_filename = Path(target_filename).name
        file_path = DATA_DIR / target_filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_structure, f, ensure_ascii=False, indent=4)

        # KLUCZOWA ZMIANA:
        if is_new_file:
            # Jeśli to był "Zapisz jako" lub "Nowy", odświeżamy by pokazać go w menu
            return RedirectResponse(url="/", status_code=303)
        else:
            # Zwykłe nadpisanie "Zapisz" - zwracamy 204 No Content!
            # (Przeglądarka ani drgnie)
            return Response(status_code=204)

    except json.JSONDecodeError:
        return HTMLResponse("Błąd: Nieprawidłowy format JSON", status_code=400)
    except Exception as e:
        return HTMLResponse(f"Wystąpił błąd podczas zapisu: {e}", status_code=500)


# ==========================================
# ZWIJANIE / ROZWIJANIE NAGŁÓWKÓW (HTMX)
# ==========================================
@app.post("/card/toggle/{uid}", response_class=HTMLResponse)
async def toggle_card_collapse(request: Request, uid: str):
    form_data = await request.form()

    # Odczyt z formularza przysłanego przez HTMX
    card_type = form_data.get("type", "text")
    current_collapsed = form_data.get("collapsed", "false")

    # Przełączenie flagi
    new_collapsed = "true" if current_collapsed == "false" else "false"

    # Budujemy nowy obiekt danych dla szablonu
    data_obj = {
        "head": form_data.get("head", ""),
        "size": form_data.get("size", "fs-6"),
        "level": int(form_data.get("level", 0)),
        "collapsed": new_collapsed,
    }

    # Odświeżamy i zwracamy wyłącznie zmodyfikowaną kartę
    return templates.TemplateResponse(
        "_card.html",
        {
            "request": request,
            "unique_id": uid,
            "type": card_type,
            "data": data_obj,
            "options": SETTINGS.get("activities", {}).get(card_type, []),
        },
    )


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


# ==========================================
# ZMIANA NAZWY PLIKU
# ==========================================
@app.post("/rename_workout/{filename}")
async def rename_workout(request: Request, filename: str):
    # HTMX wysyła wpisany w okienko tekst w specjalnym nagłówku 'HX-Prompt'
    new_name = request.headers.get("HX-Prompt")

    # Jeśli użytkownik wcisnął "Anuluj" lub nie wpisał niczego
    if not new_name or not new_name.strip():
        return Response(status_code=204)  # 204 oznacza "Nic nie rób"

    safe_name = new_name.strip()

    # Upewniamy się, że nowa nazwa ma rozszerzenie .json
    if not safe_name.endswith(".json"):
        new_filename = f"{safe_name}.json"
    else:
        new_filename = safe_name

    old_path = DATA_DIR / filename
    new_path = DATA_DIR / new_filename

    # Zmieniamy nazwę na dysku
    if old_path.exists() and not new_path.exists():
        old_path.rename(new_path)

    # Mówimy HTMX-owi: "Udało się, odśwież całą stronę"
    response = Response(status_code=200)
    response.headers["HX-Refresh"] = "true"
    return response


# ==========================================
# USUWANIE PLIKU
# ==========================================
@app.delete("/delete_workout/{filename}")
async def delete_workout(filename: str):
    file_path = DATA_DIR / filename

    # Usuwamy plik, jeśli istnieje
    if file_path.exists():
        file_path.unlink()

    # Mówimy HTMX-owi: "Udało się, odśwież całą stronę"
    response = Response(status_code=200)
    response.headers["HX-Refresh"] = "true"
    return response


# ==========================================
# DUPLIKOWANIE PLIKU
# ==========================================
@app.post("/duplicate_workout/{filename}")
async def duplicate_workout(filename: str):
    old_path = DATA_DIR / filename

    if not old_path.exists():
        return Response(status_code=404)

    # 1. Bierzemy bazową nazwę (bez .json) i dodajemy "(kopia)"
    stem = old_path.stem
    new_filename = f"{stem} (kopia).json"
    new_path = DATA_DIR / new_filename

    # 2. Pętla zabezpieczająca: jeśli zrobisz kopię kopii,
    # doklejamy kolejne "(kopia)", aż znajdziemy wolną nazwę.
    while new_path.exists():
        stem = new_path.stem
        new_filename = f"{stem} (kopia).json"
        new_path = DATA_DIR / new_filename

    # 3. Kopiujemy plik
    shutil.copy2(old_path, new_path)

    response = Response(status_code=200)
    response.headers["HX-Refresh"] = "true"
    return response


# @app.get("/add_list_item/{parent_id}", response_class=HTMLResponse)
# async def add_list_item(request: Request, parent_id: str, list_type: str = "bullet"):

#     # Decydujemy, co jest znacznikiem na podstawie przekazanego typu
#     if list_type == "checklist":
#         marker = (
#             '<input class="form-check-input me-2 mt-0 shadow-none border-secondary" type="checkbox" name="is_checked">'
#         )
#     else:
#         marker = '<span class="me-2 text-secondary list-marker"></span>'

#     return f"""
#     <div class="node list-item-row d-flex align-items-center mb-1">
#         {marker}
#         <input type="text" class="form-control form-control-sm border-0 shadow-none bg-transparent p-0"
#                name="content" placeholder="Nowy punkt..." value="">
#     </div>
#     """
