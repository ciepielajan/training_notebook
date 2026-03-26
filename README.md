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

