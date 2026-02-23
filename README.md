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

TODO:
### glowna strona to http://127.0.0.1:8000/

#### co działa:
##### v4
- [todo] - Przenieść z aplikacji

##### v3
- poniższa całość na tyle działa świetnie że przenosze robienie notatek TODO z readme do notatek aplikacji [[todo] po jakimś etapie przenieść zrobine rzeczy do readmy żeby zachowaly sie w git]
- lista treningów, zapisz, zapisz jako, import, export
- wczytywanie i zaciaganie listy treningów z folderu na dysku
- duplikowanie, zmiana nazwy, usuwanie treningów
- strona startowa, 
- grupowanie ćwiczeń w serie
- nowy block ( list punktowa, lista numerowana, checkboxy) [inprogress]  


##### v2
- rezygnacja z grup indexów na rzecz tabelki. Wyglądem są juz identyczne a zarządznie o wiele prostsze
- grupowanie i rozgrupowywanie serii (uwaga możliwe że logika usuwania wierszy w zgrupowanych może nie działać.)
- menu

#### todo:
- lista treningów

##### v1
- każdy przycisk:
- - select z options z configu
- - przyciski elementów
- - przyciski detail
- demo dane
- wczytywanie i zapisywanie wszystkich elementów poza gym
- config zczytywnay z yaml  a nie z klasy python (żeby można było dodawać wartości własne etykiety i później je wczytywać)
- przycisk obok kazdego card (przyciskin nowych card, usunięcie)
- przycisk custom label (custom_detail.html) ( TODO mozna usunac app/templates/inputs/detail.html bo już jest tylko custom)
- przycisk kolejnej serii (INPROGRESS - działa kopiowanie teraz teraz grzeba pogrupowaać etykiety w jednej linii jak w gym) 

#### todo:
- przycisk dodający nowe sekcje np tętno , laps (chyba tez jako zdefiniowane i jeden custom) [NIEE - to nipotrzebne kombinowanie. juz teraz moga to dodawać sobie jak chcą . ] - trzeba edytować przycisk dodanie serii ze albo w doł albo w prawo . trzeba wtedy zdefiniować nowe szablony i wstrzebić w nie dane . moze być potrzebne nowe pojęcie hx-swap-oob="true". 
- przycisk który przesunie w lewo albo w prawo dany castom_field
przycisk obok kazdego card (kopiowanie i wklejanie całego card)
- lista treningów
- kopiowanie treningów
- przyciski typu number , time (na mobile super to działa)
- PWA


#### błedy:


