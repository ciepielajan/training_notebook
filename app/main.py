from fastapi import UploadFile, File, status
from fastapi.responses import JSONResponse, Response
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import datetime
import secrets
import json
import shutil
from pathlib import Path
from app.utils import (
    SETTINGS,
    DATA_DIR,
    get_header_level,
    get_recent_files,
    process_spider_json,
    get_all_exercises,
    save_index,
    load_index,
)
import traceback
import yaml
from urllib.parse import quote, unquote


def multiline_presenter(dumper, data):
    if "\n" in data:
        # Użyj stylu blokowego '|' dla stringów z enterami
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


yaml.add_representer(str, multiline_presenter)
# Zabezpieczenie, gdyby użyto SafeDumpera
yaml.representer.SafeRepresenter.add_representer(str, multiline_presenter)

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
templates.env.globals["SETTINGS"] = SETTINGS
templates.env.globals["get_all_exercises"] = get_all_exercises
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/card", response_class=HTMLResponse)
async def field_fragment(
    request: Request,
    size: str = "",
    type: str = "",
    value: str = "",
    label: str = "",
    list_type: str = "bullet",
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
                "level": get_header_level(size) if type == "text" else 0,
                "collapsed": "false",
                "list_type": list_type,
            },
            "options": options_list,
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


def create_and_render_file(request: Request, file_data: dict, file_prefix: str):
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    random_id = secrets.token_hex(2)
    new_filename = f"{file_prefix}_{timestamp}_{random_id}.json"
    file_path = DATA_DIR / new_filename

    display_name = "Nowy element" if file_prefix == "item" else "Nowa notatka"

    # Inicjujemy metadane bazy w dokumencie
    file_data.update(
        {
            "file_context": file_prefix,
            "title": display_name,
            "is_deleted": False,
            "is_favorite": False,
            "project_ids": [],
        }
    )

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(file_data, f, ensure_ascii=False, indent=4)

    # Aktualizacja indeksu
    index = load_index()
    index[new_filename] = {"title": display_name, "is_deleted": False, "is_favorite": False, "project_ids": []}
    save_index(index)

    cards_to_render = process_spider_json(file_data)
    context = {
        "request": request,
        "cards_list": cards_to_render,
        "current_filename": new_filename,
        "display_name": display_name,
        "workout_data": file_data,
        "file_context": file_prefix,
    }
    response = templates.TemplateResponse("_workout_content.html", context)
    response.headers["HX-Trigger"] = "updateSidebar"
    return response


@app.get("/new/{context_name}", response_class=HTMLResponse)
async def new_file(request: Request, context_name: str):
    # context_name to "note" lub "item"
    unique_id = secrets.token_hex(4)
    head_text = "Nowy element" if context_name == "item" else "Nowa notatka"
    spider_json = {"items": [{"id": unique_id, "type": "text", "data": "", "head": head_text, "size": "fs-6"}]}
    return create_and_render_file(request, spider_json, context_name)


# --- UNIWERSALNE WCZYTYWANIE ---
@app.get("/load_file/{filename}", response_class=HTMLResponse)
async def load_file(request: Request, filename: str):
    file_path = DATA_DIR / filename
    spider_json = {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            spider_json = json.load(f)
        cards_to_render = process_spider_json(spider_json)
    except (FileNotFoundError, json.JSONDecodeError):
        cards_to_render = []

    file_context = spider_json.get("file_context", filename.split("_")[0])
    tags = spider_json.get("tags", spider_json.get("project_ids", []))

    # Tytuł pobieramy już bezpiecznie prosto z JSON-a
    display_name = spider_json.get("title", "Bez nazwy")

    context = {
        "request": request,
        "cards_list": cards_to_render,
        "current_filename": filename,
        "display_name": display_name,
        "workout_data": spider_json,
        "file_context": file_context,
        "tags": tags,
    }
    return templates.TemplateResponse("_workout_content.html", context)


# --- USUWANIE ---
@app.delete("/delete_file/{filename}")
async def delete_file(filename: str):
    """Miękkie usunięcie - ląduje w Koszu"""
    file_path = DATA_DIR / filename
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["is_deleted"] = True
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    index = load_index()
    if filename in index:
        if isinstance(index[filename], str):
            index[filename] = {"title": index[filename]}
        index[filename]["is_deleted"] = True
        save_index(index)

    response = Response(status_code=200)
    response.headers["HX-Trigger"] = "updateSidebar"
    return response


@app.post("/restore_file/{filename}")
async def restore_file(filename: str):
    """Przywraca plik z Kosza"""
    file_path = DATA_DIR / filename
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["is_deleted"] = False
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    index = load_index()
    if filename in index:
        if isinstance(index[filename], str):
            index[filename] = {"title": index[filename]}
        index[filename]["is_deleted"] = False
        save_index(index)

    response = Response(status_code=200)
    response.headers["HX-Trigger"] = "updateSidebar"
    return response


@app.delete("/hard_delete_file/{filename}")
async def hard_delete_file(filename: str):
    """Fizycznie usuwa plik (Opróżnij z Kosza)"""
    file_path = DATA_DIR / filename
    if file_path.exists():
        file_path.unlink()

    index = load_index()
    if filename in index:
        del index[filename]
        save_index(index)

    response = Response(status_code=200)
    response.headers["HX-Trigger"] = "updateSidebar"
    return response


# --- ULUBIONE (Pin) ---
@app.post("/toggle_favorite/{filename}")
async def toggle_favorite(filename: str):
    file_path = DATA_DIR / filename
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["is_favorite"] = not data.get("is_favorite", False)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

    index = load_index()
    if filename in index:
        if isinstance(index[filename], str):
            index[filename] = {"title": index[filename]}
        index[filename]["is_favorite"] = not index[filename].get("is_favorite", False)
        save_index(index)

    response = Response(status_code=200)
    response.headers["HX-Trigger"] = "updateSidebar"
    return response


# --- ZMIANA NAZWY ---
@app.post("/rename_file/{filename}")
async def rename_file(request: Request, filename: str):
    new_name = request.headers.get("HX-Prompt")

    if not new_name or not new_name.strip():
        return Response(status_code=204)

    safe_name = new_name.strip()
    file_path = DATA_DIR / filename

    if file_path.exists():
        # 1. Zmieniamy tytuł wewnątrz samego pliku notatki
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        data["title"] = safe_name

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        # 2. Zmieniamy tytuł w cache'u (index.json) szanując strukturę metadanych
        index = load_index()
        if filename in index:
            # Zabezpieczenie migracyjne na wypadek starych stringów
            if isinstance(index[filename], str):
                index[filename] = {
                    "title": index[filename],
                    "is_deleted": False,
                    "is_favorite": False,
                    "project_ids": [],
                }

            index[filename]["title"] = safe_name
            save_index(index)

    response = Response(status_code=200)
    response.headers["HX-Trigger"] = "updateSidebar"
    return response


# --- DUPLIKOWANIE ---
@app.post("/duplicate_file/{filename}")
async def duplicate_file(filename: str):
    old_path = DATA_DIR / filename

    if not old_path.exists():
        return Response(status_code=404)

    # 1. Odczytujemy starą notatkę
    with open(old_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 2. Tworzymy nowy tytuł i czyścimy specyficzne flagi
    old_title = data.get("title", "Bez nazwy")
    new_title = f"{old_title} (kopia)"

    data["title"] = new_title
    data["is_favorite"] = False  # Kopia domyślnie nie jest ulubiona
    data["is_deleted"] = False  # Kopia domyślnie nie jest w koszu (gdybyśmy duplikowali z kosza)
    # project_ids zostawiamy bez zmian, niech kopia będzie przypisana do tych samych projektów!

    # 3. Generujemy CAŁKOWICIE NOWE ID dla pliku
    prefix = data.get("file_context", "note")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    random_id = secrets.token_hex(2)
    new_filename = f"{prefix}_{timestamp}_{random_id}.json"
    new_path = DATA_DIR / new_filename

    # 4. Zapisujemy jako nowy plik
    with open(new_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    # 5. Dodajemy nowy plik do indeksu uwzględniając wymaganą strukturę metadanych
    index = load_index()
    index[new_filename] = {
        "title": new_title,
        "is_favorite": False,
        "is_deleted": False,
        "project_ids": data.get("project_ids", []),
    }
    save_index(index)

    response = Response(status_code=200)
    response.headers["HX-Trigger"] = "updateSidebar"
    return response


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    recent_notes = get_recent_files("note")
    recent_items = get_recent_files("item")

    spider_json = {
        "items": [
            {
                "id": secrets.token_hex(4),
                "type": "text",
                "data": "",
                "head": "👋 Witaj w Notatniku!",
                "size": "fs-5 fw-bold",
            },
            {
                "id": secrets.token_hex(4),
                "type": "text",
                "data": "",
                "head": f"Masz zapisanych {len(recent_notes)} notatek i {len(recent_items)} elementów bazy.",
                "size": "fs-6",
            },
        ]
    }
    cards_to_render = process_spider_json(spider_json)

    context = {
        "request": request,
        "cards_list": cards_to_render,
        "recent_notes": recent_notes,
        "recent_items": recent_items,
        "current_filename": "",
        "file_context": "note",
    }
    return templates.TemplateResponse("index.html", context)

    # Tworzymy pełną ścieżkę do klikniętego pliku
    file_path = DATA_DIR / filename
    spider_json = {}

    try:
        # 1. Wczytujemy plik z dysku
        with open(file_path, "r", encoding="utf-8") as f:
            spider_json = json.load(f)

        # 2. Przetwarzamy dane funkcją
        cards_to_render = process_spider_json(spider_json)

    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"BŁĄD: Nie można wczytać pliku {filename}: {e}")
        cards_to_render = []

    # 3. Zwracamy PEŁNĄ paczkę (Nagłówek + Karty + Inputy) i przekazujemy workout_data
    context = {
        "request": request,
        "cards_list": cards_to_render,
        "current_filename": filename,
        "workout_data": spider_json,
    }

    # Zmieniamy zwracany szablon na naszą nową paczkę
    return templates.TemplateResponse("_workout_content.html", context)


# --- AUTO ZAPIS ---
@app.post("/save")
async def save(request: Request):
    form = await request.form()
    json_body = form.get("json_body")
    current_filename = form.get("current_filename", "").strip()
    file_context = form.get("file_context", "note").strip()

    if not json_body or not current_filename:
        return JSONResponse(content={"status": "error", "message": "Brak danych"}, status_code=400)

    try:
        new_data_structure = json.loads(json_body)
        file_path = DATA_DIR / current_filename

        # Bezpiecznie wczytujemy STARE metadane, żeby JS ich nie nadpisał
        if file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
        else:
            existing_data = {"title": "Bez nazwy", "is_deleted": False, "is_favorite": False, "project_ids": []}

        # Aktualizujemy TYLKO drzewo bloków i kontekst
        existing_data["items"] = new_data_structure.get("items", [])
        existing_data["file_context"] = file_context

        # Nadpisujemy dokument
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=4)

        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


# --- ENDPOINT 2: Pobieranie pliku (Eksport - Omija HTMX) ---
@app.post("/export")
async def export(request: Request):
    form = await request.form()
    json_body = form.get("json_body")
    current_filename = form.get("current_filename", "export.json").strip()

    if not json_body:
        return JSONResponse(content={"status": "error", "message": "Brak danych"}, status_code=400)

    try:
        # Formatujemy ładnie JSONa do pobrania
        data_structure = json.loads(json_body)
        json_str = json.dumps(data_structure, ensure_ascii=False, indent=4)

        return Response(
            content=json_str,
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename={current_filename}"},
        )
    except Exception as e:
        return JSONResponse(content={"status": "error", "message": str(e)}, status_code=500)


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
                data[f"m_r{r}c{c+1}"] = data.get(f"m_r{r}c{c}", "")
                data[f"u_r{r}c{c+1}"] = data.get(f"u_r{r}c{c}", "")

        # Wstawiamy nową kolumnę
        data[f"h{col_idx+1}"] = col_name
        data[f"w{col_idx+1}"] = col_width
        for r in range(1, num_rows + 1):
            data[f"r{r}c{col_idx+1}"] = ""
            data.pop(f"m_r{r}c{col_idx+1}", None)
            data.pop(f"u_r{r}c{col_idx+1}", None)

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
                    data[f"u_r{r}c{c}"] = data.get(f"u_r{r}c{c+1}", "")

            data.pop(f"h{num_cols}", None)
            data.pop(f"w{num_cols}", None)
            for r in range(1, num_rows + 1):
                data.pop(f"r{r}c{num_cols}", None)  # <--- POPRAWKA BŁĘDU: Było r{num_rows}, a powinno być r{r}
                data.pop(f"m_r{r}c{num_cols}", None)  # <--- NOWOŚĆ: Czyścimy info o złączeniu z usuniętej kolumny
                data.pop(f"u_r{r}c{num_cols}", None)

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
                data[f"m_r{r+1}c{c}"] = data.get(f"m_r{r}c{c}", "")
                data[f"u_r{r+1}c{c}"] = data.get(f"u_r{r}c{c}", "")

        # Czyścimy nowo powstały wiersz
        for c in range(1, num_cols + 1):
            data[f"r{row_idx+1}c{c}"] = ""
            data.pop(f"m_r{row_idx+1}c{c}", None)
            data.pop(f"u_r{row_idx+1}c{c}", None)

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
                    data[f"m_r{r}c{c}"] = data.get(f"m_r{r+1}c{c}", "")
                    data[f"u_r{r}c{c}"] = data.get(f"u_r{r+1}c{c}", "")

            # Usuwamy "osierocone" dane z ostatniego wiersza
            for c in range(1, num_cols + 1):
                data.pop(f"r{num_rows}c{c}", None)
                data.pop(f"m_r{num_rows}c{c}", None)
                data.pop(f"u_r{num_rows}c{c}", None)

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

    # ==========================================
    # 9. NOWOŚĆ: INTELIGENTNA TRANSPOZYCJA TABELI (Pion <-> Poziom)
    # ==========================================
    elif action == "transpose":
        # Sprawdzamy obecny układ. Rozpoznajemy tryb poziomy po tym,
        # że górny nagłówek h1 jest pusty, bo etykieta "Ćwiczenie"
        # została zrzucona do wiersza w ciele tabeli (r1c1).
        is_horizontal = data.get("h1", "").strip() == ""

        new_data = {}

        if not is_horizontal:
            # --- TRYB: PIONOWY -> POZIOMY ---
            new_data["num_rows"] = num_cols
            new_data["num_cols"] = num_rows + 1

            # W trybie poziomym potrzebujemy węższych kolumn na dane (np. 60px zamiast 100px)
            # Pierwsza kolumna zachowuje swoją dotychczasową szerokość
            new_data["w1"] = data.get("w1", "180px")
            for c in range(2, new_data["num_cols"] + 1):
                new_data[f"w{c}"] = "60px"

            # 1. Górne nagłówki (th) ukrywamy (czyścimy)
            for c in range(1, new_data["num_cols"] + 1):
                new_data[f"h{c}"] = ""

            # 2. Wiersz 1: Etykieta głównego ćwiczenia i jego wartość zrzucone z góry
            new_data["r1c1"] = data.get("h1", "")
            new_data["r1c2"] = data.get("r1c1", "")
            # (Puste komórki od r1c3 w górę wygenerują się w HTML automatycznie jako puste kwadraty)

            # 3. Wiersze 2+: Transponujemy tylko metryki (Powtórzenia, Ciężar, itp.)
            for old_c in range(2, num_cols + 1):
                new_r = old_c
                new_data[f"r{new_r}c1"] = data.get(f"h{old_c}", "")

                for old_r in range(1, num_rows + 1):
                    new_c = old_r + 1
                    new_data[f"r{new_r}c{new_c}"] = data.get(f"r{old_r}c{old_c}", "")
                    new_data[f"u_r{new_r}c{new_c}"] = data.get(f"u_r{old_r}c{old_c}", "")
        else:
            # --- TRYB: POZIOMY -> PIONOWY (Cofnięcie do oryginału) ---
            new_data["num_rows"] = num_cols - 1
            new_data["num_cols"] = num_rows

            # Przywracamy standardowe szerokości kolumn (dla metryk np. 100px)
            new_data["w1"] = data.get("w1", "180px")
            for c in range(2, new_data["num_cols"] + 1):
                new_data[f"w{c}"] = "100px"

            # 1. "Ćwiczenie" i wartość wracają na swoje miejsce (h1 i złączone r1c1)
            new_data["h1"] = data.get("r1c1", "")
            new_data["r1c1"] = data.get("r1c2", "")

            # Odtwarzamy flagi scalenia (rowspan) w dół dla kolumny z nazwą ćwiczenia
            for r in range(2, new_data["num_rows"] + 1):
                new_data[f"m_r{r}c1"] = "1"

            # 2. Reszta wierszy wraca do układu kolumnowego jako nagłówki i wartości
            for old_r in range(2, num_rows + 1):
                new_c = old_r
                new_data[f"h{new_c}"] = data.get(f"r{old_r}c1", "")

                for old_c in range(2, num_cols + 1):
                    new_r = old_c - 1
                    new_data[f"r{new_r}c{new_c}"] = data.get(f"r{old_r}c{old_c}", "")
                    new_data[f"u_r{new_r}c{new_c}"] = data.get(f"u_r{old_r}c{old_c}", "")

        # Nadpisujemy stary stan czystą, nowo zmapowaną macierzą
        data = new_data

    # Renderujemy z powrotem cały szablon tabeli z nowymi danymi
    context = {
        "request": request,
        "unique_id": uid,
        "data": data,
    }
    return templates.TemplateResponse("blocks/table.html", context)


@app.get("/add_list_item/{parent_id}", response_class=HTMLResponse)
async def add_list_item(request: Request, parent_id: str, list_type: str = "bullet"):
    # Przygotowujemy "pusty" obiekt elementu, aby partial wiedział co renderować
    empty_item = {"content": "", "is_checked": False}

    return templates.TemplateResponse(
        "blocks/list_item.html", {"request": request, "item": empty_item, "list_type": list_type}
    )


@app.get("/recent_html/{context_name}")
async def recent_html(request: Request, context_name: str, deleted: bool = False):
    recent_files = get_recent_files(context_name, include_deleted=deleted)
    return templates.TemplateResponse(
        "_recent_list.html", {"request": request, "recent_files": recent_files, "is_trash_view": deleted}
    )


@app.post("/card/transform/{uid}", response_class=HTMLResponse)
async def transform_card(request: Request, uid: str):
    form_data = await request.form()

    # 1. Z hx-vals odbieramy pożądany NOWY typ i konfigurację
    new_type = form_data.get("new_type", "text")
    new_size = form_data.get("new_size", "")
    new_list_type = form_data.get("new_list_type", "bullet")

    # Pobieramy stan zagnieżdżenia
    current_collapsed = form_data.get("collapsed", "false")

    data_obj = {
        "level": get_header_level(new_size) if new_type == "text" else 0,
        "collapsed": current_collapsed,
    }

    # 2. Przetwarzamy dane w zależności od nowego typu
    if new_type in ["text", "notes"]:
        data_obj["head"] = form_data.get("head", "")
        data_obj["size"] = new_size

    elif new_type == "list":
        data_obj["list_type"] = new_list_type

        # Zbieramy wszystkie aktualne punkty listy wysłane przez HTMX
        contents = form_data.getlist("content")

        # Budujemy na nowo listę elementów (domyślnie zdejmujemy zaznaczenie "is_checked" przy transformacji)
        items = [{"content": c, "is_checked": False} for c in contents]

        if not items:
            items = [{"content": "", "is_checked": False}]

        data_obj["items"] = items

    # 3. Zwracamy na nowo wyrenderowaną kartę, zachowując ten sam ID
    return templates.TemplateResponse(
        "_card.html",
        {
            "request": request,
            "unique_id": uid,
            "type": new_type,
            "data": data_obj,
            "options": SETTINGS.get("activities", {}).get(new_type, []),
        },
    )


@app.post("/card/to_clipboard/{uid}", response_class=HTMLResponse)
async def to_clipboard(request: Request, uid: str):
    form_data = await request.form()
    json_body = form_data.get("json_body")
    current_filename = form_data.get("current_filename", "")

    if not json_body:
        return Response(status_code=400)

    data_tree = json.loads(json_body)
    target_card = next((card for card in data_tree.get("items", []) if card.get("id") == uid), None)

    if not target_card:
        return Response(status_code=404)

    target_card.pop("id", None)  # Czyścimy ID pod duplikację

    # SCENARIUSZ A: Jesteśmy wewnątrz schowka (wyzwalamy OOB swap)
    if current_filename == "clipboard.json":
        dummy_spider = {"items": [target_card]}
        processed = process_spider_json(dummy_spider)
        new_card_html = templates.get_template("_card.html").render({"request": request, **processed[0]})
        return HTMLResponse(f'<div id="fields-container" hx-swap-oob="afterbegin">{new_card_html}</div>')

    # SCENARIUSZ B: Jesteśmy w zwykłym treningu (zapisujemy do pliku)
    clipboard_path = DATA_DIR / "clipboard.json"
    clipboard_data = {"items": []}

    if clipboard_path.exists():
        try:
            with open(clipboard_path, "r", encoding="utf-8") as f:
                clipboard_data = json.load(f)
        except json.JSONDecodeError:
            pass

    clipboard_data["items"].insert(0, target_card)
    with open(clipboard_path, "w", encoding="utf-8") as f:
        json.dump(clipboard_data, f, ensure_ascii=False, indent=4)

    response = HTMLResponse("")
    response.headers["HX-Trigger"] = "updateSidebar"
    return response


@app.post("/card/paste/{uid}", response_class=HTMLResponse)
async def paste_card(request: Request, uid: str):
    clipboard_path = DATA_DIR / "clipboard.json"

    # Jeśli użytkownik usunął plik lub schowek jest pusty, nic nie robimy
    if not clipboard_path.exists():
        return HTMLResponse("", status_code=200)

    try:
        with open(clipboard_path, "r", encoding="utf-8") as f:
            clipboard_data = json.load(f)
    except json.JSONDecodeError:
        return HTMLResponse("", status_code=200)

    items = clipboard_data.get("items", [])
    if not items:
        return HTMLResponse("", status_code=200)

    # Bierzemy ZAWSZE pierwszy element z góry
    target_card = items[0]

    # Zabezpieczenie: Przetwarzamy go naszym silnikiem, aby dostał nowe, unikalne ID
    dummy_spider = {"items": [target_card]}
    processed_cards = process_spider_json(dummy_spider)

    if not processed_cards:
        return HTMLResponse("Błąd generowania karty", status_code=500)

    # Zwracamy wyrenderowaną kartę, która zostanie wklejona PONIŻEJ
    return templates.TemplateResponse("_card.html", {"request": request, **processed_cards[0]})


# ==========================================
# USTAWIENIA (CONFIG.YAML)
# ==========================================
@app.get("/settings", response_class=HTMLResponse)
async def get_settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request, "settings": SETTINGS})


@app.post("/settings", response_class=HTMLResponse)
async def save_settings(request: Request):
    form_data = await request.form()

    new_settings = {}
    for key, value in form_data.items():

        if isinstance(value, str):
            value = value.replace("\r\n", "\n").strip()

        # Proste typowanie
        parsed_value = value
        if value.isdigit():
            parsed_value = int(value)
        else:
            try:
                parsed_value = float(value)
            except ValueError:
                pass

        # Obsługa nieskończonego zagnieżdżenia (podział po kropkach)
        parts = key.split(".")
        current_level = new_settings

        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # Ostatni element (klucz docelowy) - przypisujemy wartość
                current_level[part] = parsed_value
            else:
                # Głębsze zagnieżdżenie - tworzymy słownik, jeśli nie istnieje
                if part not in current_level:
                    current_level[part] = {}
                # Przesuwamy wskaźnik głębiej
                current_level = current_level[part]

    # Zapis do fizycznego pliku config.yaml
    with open("config.yaml", "w", encoding="utf-8") as f:
        yaml.dump(new_settings, f, allow_unicode=True, sort_keys=False)

    # Aktualizacja globalnego obiektu w pamięci RAM
    SETTINGS.clear()
    SETTINGS.update(new_settings)

    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "settings": new_settings, "success_message": "Zapisano zmiany w pliku konfiguracyjnym."},
    )


# ==========================================
# MODALE I SZCZEGÓŁY
# ==========================================
@app.get("/exercise_details", response_class=HTMLResponse)
async def exercise_details(request: Request, name: str):

    exercises = get_all_exercises()
    tags = []

    for ex in exercises:
        if ex["name"] == name:
            # Wstrzykujemy źródło na pierwsze miejsce listy tagów
            tags = [ex["source"]] + ex["tags"]
            break

    return templates.TemplateResponse(
        "blocks/exercise_modal.html",
        {"request": request, "name": name, "tags": tags},
    )


# --- WIDOK PEŁNEJ LISTY Z WYSZUKIWARKĄ I TAGAMI ---
# --- WIDOK PEŁNEJ LISTY Z WYSZUKIWARKĄ I TAGAMI ---
@app.get("/list_view/{context_name}", response_class=HTMLResponse)
async def list_view(request: Request, context_name: str, deleted: bool = False, q: str = None, tag: str = None):
    files = get_recent_files(context_name, include_deleted=deleted)

    # 1. Wyciągamy wszystkie unikalne tagi do stworzenia przycisków
    all_tags = set()
    for f in files:
        for t in f.get("tags", []):
            all_tags.add(t)

    sorted_tags = sorted(list(all_tags))

    # 2. Filtrowanie plików po wybranym tagu (jeśli ktoś kliknął przycisk)
    if tag:
        files = [f for f in files if tag in f.get("tags", [])]

    # 3. Dodatkowe filtrowanie po nazwie z pola tekstowego
    if q:
        files = [f for f in files if q.lower() in f["name"].lower()]

    context = {
        "request": request,
        "files": files,
        "context_name": context_name,
        "is_trash_view": deleted,
        "file_context": "dashboard",
        "current_filename": "",
        "search_query": q or "",
        "all_tags": sorted_tags,
        "active_tag": tag,
    }
    return templates.TemplateResponse("_list_view.html", context)


# --- SYSTEM TAGÓW ---
@app.post("/tags/add/{filename}")
async def add_tag(request: Request, filename: str):
    form = await request.form()
    # Pobieramy wpis, wywalamy spacje na końcach, zmieniamy na małe litery i wyrzucamy znak #
    new_tag = form.get("tag_name", "").strip().lower().replace("#", "")

    file_path = DATA_DIR / filename
    if not new_tag or not file_path.exists():
        return Response(status_code=204)

    # 1. Dodajemy do Głównego Źródła (plik)
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Zgodność wsteczna: używamy 'tags' albo 'project_ids'
    tags = data.get("tags", data.get("project_ids", []))

    if new_tag not in tags:
        tags.append(new_tag)
        data["tags"] = tags
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

        # 2. Aktualizujemy Cache (index.json)
        index = load_index()
        if filename in index:
            index[filename]["tags"] = tags
            save_index(index)

    # Zwracamy zaktualizowany komponent HTML
    return templates.TemplateResponse(
        "_tags_editor.html", {"request": request, "current_filename": filename, "tags": tags}
    )


@app.delete("/tags/remove/{filename}/{tag_name}")
async def remove_tag(request: Request, filename: str, tag_name: str):
    file_path = DATA_DIR / filename
    if file_path.exists():
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        tags = data.get("tags", data.get("project_ids", []))
        if tag_name in tags:
            tags.remove(tag_name)
            data["tags"] = tags
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            index = load_index()
            if filename in index:
                index[filename]["tags"] = tags
                save_index(index)

        return templates.TemplateResponse(
            "_tags_editor.html", {"request": request, "current_filename": filename, "tags": tags}
        )
    return Response(status_code=404)
