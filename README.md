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