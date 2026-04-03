from pydantic import BaseModel, Field, field_validator, model_validator, BeforeValidator, ConfigDict, RootModel
from typing import Dict, List, Any, Optional
from typing_extensions import Annotated


class TagGroup(BaseModel):
    order: int = 99
    color: str = "secondary"
    items: List[str]


# 1. Wyciągnięta logika migracji (czysta funkcja Pythona)
def migrate_legacy_tags(value: Any) -> Any:
    """Migruje listę tagów na słownik z grupą 'ogólne'"""
    if isinstance(value, list):
        return {"ogólne": {"items": value}}
    return value


# 2. Stworzenie inteligentnego typu Pydantic
# Mówi to Pydanticowi: "Kiedy widzisz typ MigratedTags, najpierw przepuść dane przez 'migrate_legacy_tags', a potem upewnij się, że to Dict[str, TagGroup]"
MigratedTags = Annotated[Dict[str, TagGroup], BeforeValidator(migrate_legacy_tags)]


class IndexEntry(BaseModel):
    """Schemat pojedynczego wpisu w index.json"""

    title: str = "Bez nazwy"
    is_deleted: bool = False
    is_favorite: bool = False
    project_ids: List[str] = Field(default_factory=list)
    tags: MigratedTags = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_string_format(cls, value: Any) -> Any:
        """
        Migracja w locie: jeśli wpis w JSON jest tylko stringiem,
        Pydantic przed walidacją zamieni go automatycznie na słownik.
        """
        if isinstance(value, str):
            return {"title": value}
        return value


class IndexDB(RootModel):
    """Korzeń pliku index.json mapujący string (nazwa pliku) na IndexEntry"""

    root: Dict[str, IndexEntry]


# --- MODELE DLA TRENINGU ---


class Athlete(BaseModel):
    name: str
    is_checked: bool = False


class WorkoutBlock(BaseModel):
    """
    Model pojedynczego bloku w notatniku (Tekst, Tabela, Lista).
    Używamy extra='allow', aby Pydantic nie odrzucał dynamicznych
    kluczy generowanych przez tabelę (np. r1c1, m_r2c1, w1).
    """

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = None
    type: Optional[str] = None
    level: int = 0
    collapsed: bool = False

    # Pola dla tekstu
    head: Optional[str] = None
    size: Optional[str] = None
    data: Optional[str] = None

    # Pola dla bloków "deprecated"
    original_type: Optional[str] = None
    raw_data: Optional[str] = None

    # Pola zagnieżdżone (np. wiersze w checkliście albo konfiguracja tabeli)
    items: Optional[List[Dict[str, Any]]] = None

    @field_validator("collapsed", mode="before")
    @classmethod
    def parse_boolean_strings(cls, v):
        """Konwertuje JS-owe stringi 'true'/'false' z HTML na prawdziwe wartości bool"""
        if isinstance(v, str):
            return v.lower() == "true"
        return bool(v)

    @field_validator("level", mode="before")
    @classmethod
    def parse_level(cls, v):
        """Konwertuje '4' na 4"""
        if isinstance(v, str) and v.isdigit():
            return int(v)
        return v if isinstance(v, int) else 0


class WorkoutNote(BaseModel):
    """
    Główny model pliku z notatką/treningiem.
    Również ma extra='allow', aby zachować kompatybilność ze starymi polami.
    """

    model_config = ConfigDict(extra="allow")

    current_filename: Optional[str] = None
    title: str = "Bez nazwy"
    date: str = ""
    time: str = ""
    place: str = ""
    weather_temp: str = ""
    weather_icon: str = "bi-sun-fill"
    file_context: str = "note"
    save_action: str = "save"

    is_favorite: bool = False
    is_deleted: bool = False

    athletes: List[Athlete] = Field(default_factory=list)
    items: List[WorkoutBlock] = Field(default_factory=list)

    tags: MigratedTags = Field(default_factory=dict)
