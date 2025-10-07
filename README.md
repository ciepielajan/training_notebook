poetry env activate

source /Users/...

Serwer run

```
uvicorn app.main:app --reload
```

```
training_notebook/
│── app/
│   ├── main.py              # punkt wejścia FastAPI
│   ├── api/                 # backendowe endpointy (np. import/export JSON)
│   │   └── routes.py
│   ├── models/              # przyszłe modele bazy danych
│   ├── services/            # logika biznesowa
│   ├── static/              # pliki statyczne (JS, CSS, obrazki)
│   │   ├── js/
│   │   │   └── editor.js    # wyciągnięty JS z index.html
│   │   └── css/
│   └── templates/           # pliki HTML
│       └── index.html
│
├── venv/                    # środowisko wirtualne (gitignore)
├── requirements.txt          # zależności (FastAPI, Jinja2, Uvicorn)
└── README.md
```
