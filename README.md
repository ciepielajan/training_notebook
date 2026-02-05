Serwer run
```
uvicorn app.main:app --reload
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
http://192.168.31.29:8000/index_form
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

TODO:
### glowna strona to http://127.0.0.1:8000/index_form
#### co działa:
- każdy przycisk:
- - select z options z configu
- - przyciski elementów
- - przyciski detail
- demo dane
- wczytywanie i zapisywanie wszystkich elementów poza gym
- config zczytywnay z yaml  a nie z klasy python (żeby można było dodawać wartości własne etykiety i później je wczytywać)
- przycisk obok kazdego card (przyciskin nowych card, usunięcie)

#### todo:
- dane demo powinny mieć strukture taka jak w json. 
- przycisk obok kazdego card (kopiowanie i wklejanie całego card)
- możliwosć własnej etykiety w detail ( czyli poprostu możliwość napisania własnego label - to tak naprawde też jednostka np metry , sekundy itd)
- PWA
- lista treningów
- kopiowanie treningów
- przyciski typu number , time (na mobile super to działa)
- przycisk custom label (custom_detail.html)  [INPROGRESS]
- - style do poprawy (brak pogrubienia i obramowanie)
- - zapisaywanie do pliku i wczytywanie
- przycisk dodający nowe sekcje np tętno , laps (chyba tez jako zdefiniowane i jeden custom)


#### błedy:
- 

