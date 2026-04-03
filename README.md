Serwer run
```
uvicorn app.main:app --reload --reload-include "*.yaml" --reload-include "*.html"

```
tips
```
# run serwer with reload for other file them .py
uvicorn app.main:app --reload --reload-include "*.yaml" --reload-include "*.html"

# after bad cloase server you can restart be:
fg

```

Serwer debug
```
launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: FastAPI",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "app.main:app",  
                "--reload",
                "--port", "8000"
            ],
            "jinja": true,
            "justMyCode": true
        }
    ]
}
```


Serwer on your wifi
```
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

```
hostname -I             # your web adresse
sudo ufw allow 8000/tcp # open port
```

```
http://192.168.31.29:8000/
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


## Mapa Interakcji HTMX

| Wyzwalacz (Lokalizacja) | Akcja / Endpoint | Przesyłane Dane | Cel (hx-target) | Zwracany Fragment |
| :--- | :--- | :--- | :--- | :--- |
| Menu boczne () | `GET /new/{context}` | brak | `#form` | `_workout_content.html` |
| Menu boczne () | `GET /list_view/{context}` | `q`, `tag`, `deleted` | `#form` | `_list_view.html` |
| Menu boczne () | `GET /settings` | brak | `#form` | `settings.html` |
| Opcje wiersza () | `POST /card/transform/{uid}` | `new_type`, `new_size` | `closest .exercise-row` | `_card.html` |
| Opcje wiersza () | `POST /card/to_clipboard/{uid}` | `json_body` | (OOB Swap) | Pusta odpowiedź / `_card.html` |
| Opcje wiersza () | `POST /card/paste/{uid}` | brak | `closest .exercise-row` | `_card.html` |
| Nagłówek karty () | `POST /card/toggle/{uid}` | `collapsed`, `level` | `closest .exercise-row` | `_card.html` |
| Menu tabeli () | `POST /card/table/action/{uid}` | `action`, `num_rows/cols` | `#table-{unique_id}` | `blocks/table.html` |
| Edytor tagów () | `POST /tags/add/{filename}` | `tag_name` | `#document-tags-container` | `_tags_editor.html` |
| Edytor tagów () | `DELETE /tags/remove/...` | brak | `#document-tags-container` | `_tags_editor.html` |
| Lista plików () | `GET /load_file/{filename}` | brak | `#form` | `_workout_content.html` |
