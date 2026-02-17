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


# @app.get("/single-input", response_class=HTMLResponse)
# async def single_input(request: Request):
#     return '<input type="text" name="extra_text" placeholder="nowe pole">'


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

    return templates.TemplateResponse(
        "index_form.html",
        {
            "request": request,
            "cards_list": cards_to_render,
        },
    )


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
        # Szukamy data_obj (podobnie jak w metodzie load)
        if card.get("items") and len(card["items"]) > 0:
            data_obj = card["items"][0]
        else:
            data_obj = card

        card_type = data_obj.get("type") or card.get("type")

        # Ujednolicenie pod szablony
        data_obj["activity"] = {"value": data_obj.get("head", ""), "label": data_obj.get("label", "")}
        if not isinstance(data_obj.get("details"), list):
            data_obj["details"] = []

        processed_cards.append(
            {
                "unique_id": secrets.token_hex(4),  # Generujemy nowe ID przy każdym wejściu
                "type": card_type,
                "data": data_obj,
                "options": SETTINGS.get("activities", {}).get(card_type, []),
            }
        )
    return processed_cards
