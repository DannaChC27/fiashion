import os

# Las pruebas siempre usan SQLite en memoria, aunque el .env apunte a MySQL
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.database import Base, get_db


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Base de datos en memoria, separada de la real
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False},
                           poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    Testing = sessionmaker(bind=engine, autoflush=False)

    def override():
        db = Testing()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    monkeypatch.setattr("app.llm.LOG_PATH", str(tmp_path / "log.csv"))
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def tienda(client, tmp_path, monkeypatch):
    """Cliente de pruebas con 2 probadores y 3 prendas ya creadas."""
    monkeypatch.setattr("app.ra.CARPETA", str(tmp_path / "ra"))
    monkeypatch.setattr("app.routers.ra.CARPETA_SUBIDAS", str(tmp_path / "subidas"))
    prendas = [
        {"nombre": "Chaqueta jean", "precio": 120000, "talla": "M", "genero": "mujer",
         "categoria": "chaquetas", "estilo": "urbano", "color": "denim", "stock": 1},
        {"nombre": "Chaqueta bomber", "precio": 150000, "talla": "M", "genero": "mujer",
         "categoria": "chaquetas", "estilo": "urbano", "color": "negro", "stock": 3},
        {"nombre": "Falda plisada", "precio": 69000, "talla": "M", "genero": "mujer",
         "categoria": "faldas", "estilo": "formal", "color": "negro", "stock": 2},
    ]
    for p in prendas:
        assert client.post("/api/v1/productos", json=p).status_code == 201
    for n in ("Probador 1", "Probador 2"):
        assert client.post("/api/v1/probadores", json={"nombre": n}).status_code == 201
    return client
