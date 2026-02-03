from collections import defaultdict
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

# Lista dostępnych opcji dla selecta, w zależności od typu karty
ACTIVITY_OPTIONS = {
    "running": ["Bieg", "Sprint", "Trucht", "Marszobieg", "Interwały"],
    "exercise": ["Wieloskok", "Pompki", "Przysiady", "Brzuszki", "Burpees"],
    # Domyślna lista, jakby typ nie pasował
    "default": ["Inne"],
}


# --- KONFIGURACJA DOMYŚLNA ---
DEFAULT_CARDS = [
    ("text", {"head": "Trening Tempowy", "size": "fs-4"}),
    (
        "running",
        {
            "activity": {"value": "Bieg", "label": ""},
            "details": [
                {"value": "200", "type": "distance", "label": "Dystans [m]"},
                {"value": "20:43", "type": "duration", "label": "Czas [sec]"},
                {"value": "5:12", "type": "pace", "label": "Tempo [min/km]"},
                {"value": "150", "type": "heart_rate", "label": "Śr. tętno [bpm]"},
            ],
        },
    ),
    (
        "exercise",
        {
            "activity": {"value": "Wieloskok", "label": "Ćwiczenie"},
            "details": [
                {"value": "50", "type": "distance", "label": "Dystans [m]"},
            ],
        },
    ),
    ("running", {"activity": {"value": "Sprint", "label": ""}, "details": []}),
]

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


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    start_id = secrets.token_hex(4)
    return templates.TemplateResponse("index.html", {"request": request, "unique_id": start_id, "type": "exercise"})


@app.get("/card", response_class=HTMLResponse)
async def field_fragment(
    request: Request,
    size: str = "",
    type: str = "running",
    value: str = "",
    label: str = "",
):
    unique_id = secrets.token_hex(4)

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
            "options": ACTIVITY_OPTIONS.get(type, ACTIVITY_OPTIONS["default"]),
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


@app.get("/single-input", response_class=HTMLResponse)
async def single_input(request: Request):
    return '<input type="text" name="extra_text" placeholder="nowe pole">'


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


@app.post("/save")
async def save(request: Request):
    form = await request.form()

    # Kolejność jest kluczowa, multi_items() ją gwarantuje
    form_data = form.multi_items()

    if not form_data:
        return HTMLResponse("<div>⚠️ Brak danych do zapisania</div>", status_code=400)

    result_cards = []

    # Wskaźniki stanu (kontekst)
    current_card = None
    in_details_section = False  # Flaga: czy jesteśmy już w środku listy <details>?

    for key, val in form_data:

        # --- POZIOM 0: NOWA KARTA ---
        if key == "id":
            # Tworzymy nową kartę
            current_card = {
                "id": val,
                # type i data zostaną uzupełnione w kolejnych krokach pętli
            }
            result_cards.append(current_card)

            # Reset flagi sekcji przy nowej karcie
            in_details_section = False

        # --- POZIOM 1: TYP I KONTENER DANYCH ---
        elif key == "type":
            if current_card is not None:
                # Uwaga: w detail.html też jest 'type', więc musimy sprawdzić kontekst
                if in_details_section:
                    # To type wewnątrz szczegółu (np. distance)
                    details_list = current_card["data"]["details"]
                    if details_list:
                        details_list[-1]["type"] = val
                else:
                    # To główny type karty (np. running)
                    current_card["type"] = val

        elif key == "data":
            # Znacznik <input name="data"> inicjalizuje obiekt data
            if current_card is not None:
                current_card["data"] = {}

        # --- POZIOM 2: WNĘTRZE ACTIVITY (head, label przed details) ---
        elif key == "head":
            if current_card and "data" in current_card:
                current_card["data"]["head"] = val

        # --- POZIOM 3: ROZPOCZĘCIE LISTY SZCZEGÓŁÓW ---
        elif key == "details":
            # Znacznik <input name="details"> sygnalizuje start listy
            if current_card and "data" in current_card:
                current_card["data"]["details"] = []
                in_details_section = True  # Przełączamy tryb na listę

        # --- POZIOM 4: NOWY ELEMENT LISTY ---
        elif key == "detail":
            # Znacznik <input name="detail"> dodaje nowy pusty słownik do listy
            if current_card and in_details_section:
                current_card["data"]["details"].append({})

        # --- WARTOŚCI (Context aware) ---
        elif key in ["value", "label"]:
            if current_card:
                if in_details_section:
                    # Jesteśmy w liście -> zapisujemy do ostatniego elementu listy
                    details_list = current_card["data"].get("details", [])
                    if details_list:
                        details_list[-1][key] = val
                else:
                    # Nie jesteśmy w liście -> zapisujemy do głównego obiektu data
                    # (To obsłuży 'label' dla Activity)
                    if "data" in current_card:
                        current_card["data"][key] = val

        elif key == "size":
            if current_card and "data" in current_card:
                current_card["data"]["size"] = val

    # --- Zapis do pliku ---
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
    with open(tmp.name, "w", encoding="utf-8") as f:
        json.dump(result_cards, f, ensure_ascii=False, indent=2)

    return FileResponse(tmp.name, media_type="application/json", filename="training_data.json")


@app.get("/index_form", response_class=HTMLResponse)
async def index(request: Request):

    cards_to_render = []
    for card_type, card_data in DEFAULT_CARDS:
        cards_to_render.append(
            {
                "type": card_type,
                "unique_id": secrets.token_hex(4),
                "data": card_data,
                "options": ACTIVITY_OPTIONS.get(card_type, ACTIVITY_OPTIONS["default"]),
            }
        )

    return templates.TemplateResponse(
        "index_form.html",
        {
            "request": request,
            "cards_list": cards_to_render,
        },
    )


@app.post("/load", response_class=HTMLResponse)
async def load(request: Request, file: UploadFile = File(...)):
    print(f"--- Otrzymano plik: {file.filename} ---")

    # 1. Wczytanie pliku
    content = await file.read()
    print(f"Rozmiar pliku: {len(content)} bajtów")

    if len(content) == 0:
        print("BŁĄD: Plik jest pusty!")
        return HTMLResponse("<div>⚠️ Błąd: Przesłany plik jest pusty</div>", status_code=400)

    try:
        # Dekodowanie
        text_content = content.decode("utf-8")
        # print(f"Treść: {text_content}") # Odkomentuj jeśli chcesz widzieć treść w logach

        cards_list = json.loads(text_content)
        print("JSON poprawnie sparsowany.")

    except json.JSONDecodeError as e:
        print(f"BŁĄD JSON: {e}")
        return HTMLResponse(f"<div>⚠️ Błąd JSON: {e}</div>", status_code=400)
    except Exception as e:
        print(f"BŁĄD NIEOCZEKIWANY: {e}")
        return HTMLResponse(f"<div>⚠️ Błąd krytyczny: {e}</div>", status_code=400)

    final_html = ""
    try:
        card_template = templates.get_template("_card.html")

        for card in cards_list:
            unique_id = card.get("id")
            card_type = card.get("type")
            raw_data = card.get("data", {})

            # TRANSFORMACJA DANYCH
            values_for_template = {
                # 1. Dla kart typu Running/Exercise (zagnieżdżone)
                "activity": {"value": raw_data.get("head", ""), "label": raw_data.get("label", "Aktywność")},
                "details": raw_data.get("details", []),
                # 2. Dla kart typu Text (płaskie)
                # Szablon text.html używa {{ data.head }} i {{ data.size }}
                "head": raw_data.get("head", ""),
                "size": raw_data.get("size", "fs-2"),
            }

            context = {
                "request": request,
                "unique_id": unique_id,
                "type": card_type,
                "data": values_for_template,
                "options": ACTIVITY_OPTIONS.get(card_type, ACTIVITY_OPTIONS["default"]),
            }

            rendered_card = card_template.render(context)
            final_html += rendered_card

    except Exception as e:
        print(f"BŁĄD RENDEROWANIA: {e}")
        # Tu rzucamy 500, bo to błąd serwera (szablonów), a nie pliku
        return HTMLResponse(f"<div>⚠️ Błąd renderowania: {e}</div>", status_code=500)

    print("Zwracanie HTML...")
    return final_html
