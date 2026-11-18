from dotenv import load_dotenv
load_dotenv()

import os

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine
from app.errors import register_error_handlers
from app.routers import productos, ai, reservas, inventario, ra

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FIAshion API",
    version="2.0.0",
    description="REST API for the FIAshion clothing advisory system: product catalog "
                "(CRUD), LLM-based recommendations, augmented reality, reservations with "
                "automatic fitting room assignment, employee notifications and inventory.",
)
register_error_handlers(app)
app.include_router(productos.router)
app.include_router(ai.router)
app.include_router(reservas.router)
app.include_router(inventario.router)
app.include_router(ra.router)

# Paginas web (cliente, empleado y administrador) en /app
CARPETA_WEB = os.path.join(os.path.dirname(__file__), "static")
app.mount("/app", StaticFiles(directory=CARPETA_WEB, html=True), name="web")


@app.get("/", include_in_schema=False)
def inicio():
    return RedirectResponse("/app/")
