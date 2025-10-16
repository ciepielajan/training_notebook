Serwer run
```
uvicorn app.main:app --reload
```

```
training_notebook/
│── app/
│   ├── main.py              # punkt wejścia FastAPI
│   ├── static/              # pliki statyczne (JS, CSS, obrazki)
│   │   └── style.css
│   └── templates/           # pliki HTML
│       └── index.html
└── README.md
```

Zbuduj CSS (jednorazowo lub z watch)
Podczas pracy (auto-build po każdej zmianie):
```
npx tailwindcss -i ./app/static/input.css -o ./app/static/style.css --watch
```