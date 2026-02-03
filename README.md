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

TODO:
### glowna strona to http://127.0.0.1:8000/index_form
#### co działa:
- każdy przycisk:
- - select z options z configu
- - przyciski elementów
- - przyciski detail
- demo dane
- wczytywanie i zapisywanie wszystkich elementów poza gym

#### todo:
- dane demo powinny mieć strukture taka jak w json. 
- przycisk obok kazdego card (przyciskin nowych card, usunięcie, zmiana obecnego, kopiowanie i wklejanie całego card)
- config zczytywnay z yaml  a nie z klasy python (żeby można było dodawać wartości własne etykiety i później je wczytywać)
- możliwosć własnej etykiety w detail ( czyli poprostu możliwość napisania własnego label - to tak naprawde też jednostka np metry , sekundy itd)
- inputy w details nie jako text a jako konkretne typy lub tekst ale z validacja wg formatu (nic pilnego)

