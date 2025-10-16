from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

app = FastAPI()
templates = Jinja2Templates(directory="app/templates")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/field-fragment", response_class=HTMLResponse)
async def field_fragment(request: Request):
    # zwraca fragment HTML (jedna linia pól)
    return templates.TemplateResponse("_fields_fragment.html", {"request": request})


@app.get("/single-input", response_class=HTMLResponse)
async def single_input(request: Request):
    return '<input type="text" name="extra_text" placeholder="nowe pole">'


@app.get("/test-ui", response_class=HTMLResponse)
async def test_ui(request: Request):
    return templates.TemplateResponse("test_ui.html", {"request": request})



@app.post("/submit", response_class=HTMLResponse)
async def submit(request: Request):
    form = await request.form()
    main_text = form.get("main_text", "")
    extra_texts = form.getlist("extra_text")
    extra_numbers = form.getlist("extra_number")

    # próba konwersji liczb (jeśli podane)
    numbers = []
    for n in extra_numbers:
        try:
            numbers.append(int(n))
        except Exception:
            try:
                numbers.append(float(n))
            except Exception:
                numbers.append(None)

    pairs = list(zip(extra_texts, numbers))
    return templates.TemplateResponse("result.html", {"request": request, "main_text": main_text, "pairs": pairs})
