import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker, DeclarativeBase

load_dotenv()  # para que seed.py tambien lea el .env

# Por defecto SQLite (un archivo). Para MySQL se pone en el .env, por ejemplo:
# DATABASE_URL=mysql+pymysql://root:mi_clave@localhost:3306/fiashion
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./fiashion.db")
ES_SQLITE = DATABASE_URL.startswith("sqlite")


def _crear_base_mysql_si_no_existe(url: str):
    """En MySQL la base (schema) tiene que existir antes de crear las tablas."""
    datos = make_url(url)
    # se conecta a "information_schema" (siempre existe) para poder crear la base
    servidor = create_engine(datos.set(database="information_schema"))
    with servidor.connect() as conexion:
        conexion.execute(text(f"CREATE DATABASE IF NOT EXISTS `{datos.database}` "
                              "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
    servidor.dispose()


if DATABASE_URL.startswith("mysql"):
    try:
        _crear_base_mysql_si_no_existe(DATABASE_URL)
    except OperationalError as e:
        # mensaje claro en vez de un error largo: casi siempre es la clave o el servicio apagado
        raise SystemExit(
            "\nNo se pudo conectar a MySQL.\n"
            "Revise en el archivo .env la linea DATABASE_URL (usuario y clave de root)\n"
            "y que el servicio MySQL80 este prendido (en MySQL Workbench debe conectar).\n"
            f"Detalle: {e.orig}\n")

# check_same_thread=False: FastAPI atiende peticiones en varios hilos
# y SQLite por defecto no lo permite. pool_pre_ping revisa que MySQL siga conectado.
engine = create_engine(DATABASE_URL,
                       connect_args={"check_same_thread": False} if ES_SQLITE else {},
                       pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


@event.listens_for(Engine, "connect")
def _activar_llaves_foraneas(conexion, _registro):
    # SQLite no revisa las llaves foraneas si no se le pide (MySQL si las revisa)
    if conexion.__class__.__module__.startswith("sqlite3"):
        cursor = conexion.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


class Base(DeclarativeBase):
    pass


def get_db():
    """Abre una sesion por peticion y la cierra siempre al terminar."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
