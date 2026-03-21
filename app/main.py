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
from app.utils import SETTINGS, DATA_DIR, get_header_level, get_recent_workouts, process_spider_json, get_all_exercises
import traceback
import yaml


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


def create_and_render_workout(request: Request, workout_data: dict, file_prefix: str):
    """
    Wspólna logika dla tworzenia i ładowania treningów.
    Zapisuje JSON na dysku, przetwarza karty i zwraca szablon dla HTMX.
    """
    # 1. GENERUJEMY NAZWĘ I ZAPISUJEMY PLIK
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    new_filename = f"{file_prefix}_{timestamp}.json"
    file_path = DATA_DIR / new_filename

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(workout_data, f, ensure_ascii=False, indent=4)

    # 2. PRZETWARZAMY DANE
    cards_to_render = process_spider_json(workout_data)
    context = {
        "request": request,
        "cards_list": cards_to_render,
        "current_filename": new_filename,
        "workout_data": workout_data,
    }

    # ZMIANA: Zwracamy _workout_content.html zamiast _cards_list.html
    response = templates.TemplateResponse("_workout_content.html", context)
    response.headers["HX-Trigger"] = "updateSidebar"
    return response


@app.get("/new_workout", response_class=HTMLResponse)
async def new_workout(request: Request):
    unique_id = secrets.token_hex(4)

    # Tworzymy domyślny szablon startowy
    spider_json = {
        "items": [
            {"id": unique_id, "type": "text", "data": "", "head": "Trening Tempowy", "size": "fs-6"},
        ]
    }

    # Przekazujemy dane i przedrostek do wspólnej funkcji
    return create_and_render_workout(request, spider_json, "nowy")


@app.post("/load", response_class=HTMLResponse)
async def load(request: Request, file: UploadFile = File(...)):
    content = await file.read()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        return HTMLResponse("Błąd: Wgrany plik nie jest poprawnym formatem JSON", status_code=400)

    # Przekazujemy wczytane dane i przedrostek "import"
    return create_and_render_workout(request, data, "import")


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
    return templates.TemplateResponse("index.html", context)


@app.get("/load_workout/{filename}", response_class=HTMLResponse)
async def load_workout(request: Request, filename: str):
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


# --- ENDPOINT 1: Cichy Auto-Zapis (Dla HTMX) ---
@app.post("/save")
async def save(request: Request):
    form = await request.form()
    json_body = form.get("json_body")
    current_filename = form.get("current_filename", "").strip()

    if not json_body or not current_filename:
        return JSONResponse(content={"status": "error", "message": "Brak danych"}, status_code=400)

    try:
        data_structure = json.loads(json_body)
        target_filename = Path(current_filename).name
        file_path = DATA_DIR / target_filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data_structure, f, ensure_ascii=False, indent=4)

        # Zwracamy pustą odpowiedź (HTMX i tak to ignoruje dzięki hx-swap="none")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except Exception as e:
        print("\n--- BŁĄD ZAPISU AUTO-SAVE ---")
        traceback.print_exc()
        print("-----------------------------\n")
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

    response = Response(status_code=200)
    response.headers["HX-Trigger"] = "updateSidebar"
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

    response = Response(status_code=200)
    response.headers["HX-Trigger"] = "updateSidebar"
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
    response.headers["HX-Trigger"] = "updateSidebar"
    return response


@app.get("/add_list_item/{parent_id}", response_class=HTMLResponse)
async def add_list_item(request: Request, parent_id: str, list_type: str = "bullet"):
    # Przygotowujemy "pusty" obiekt elementu, aby partial wiedział co renderować
    empty_item = {"content": "", "is_checked": False}

    return templates.TemplateResponse(
        "blocks/list_item.html", {"request": request, "item": empty_item, "list_type": list_type}
    )


@app.get("/recent_workouts_html")
async def recent_workouts_html(request: Request):
    recent_workouts = get_recent_workouts()
    return templates.TemplateResponse("_recent_list.html", {"request": request, "recent_workouts": recent_workouts})


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
