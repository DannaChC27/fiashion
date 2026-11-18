import re

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.disponibilidad import unidades_libres
from app.models import Producto, Recomendacion
from app.schemas import RecommendRequest, RecommendResponse, ErrorOut
from app.prompts import TECNICAS
from app.llm import llamar_gemini

router = APIRouter(prefix="/api/v1/ai", tags=["AI"])


@router.post("/recommend", response_model=RecommendResponse,
             summary="Recommend clothes with an LLM",
             description=("Looks for available products that match the customer filters, "
                          "puts them in the prompt (basic RAG) and asks the LLM to pick "
                          "up to 3. The prompting technique can be zero_shot, few_shot or cot."),
             responses={429: {"model": ErrorOut, "description": "AI rate limit"},
                        502: {"model": ErrorOut, "description": "AI provider error"},
                        503: {"model": ErrorOut, "description": "AI not configured"},
                        504: {"model": ErrorOut, "description": "AI timeout"}})
def recomendar(datos: RecommendRequest, db: Session = Depends(get_db)):
    # 1. RETRIEVAL: solo prendas disponibles que cumplen los filtros
    consulta = select(Producto).where(
        Producto.disponible.is_(True),
        Producto.talla == datos.talla,
        Producto.genero.in_([datos.genero, "unisex"]),
        Producto.categoria == datos.categoria,
    )
    if datos.estilo:
        consulta = consulta.where(Producto.estilo == datos.estilo)
    # solo las que todavia tienen unidades sin reservar
    productos = [p for p in db.scalars(consulta.limit(40)).all() if unidades_libres(db, p) > 0][:20]

    # Si no hay prendas, no gastamos una llamada al modelo.
    if not productos:
        return RecommendResponse(technique=datos.technique,
                                 recommendation="No available products match those filters.",
                                 products_considered=0, latency_ms=0)

    # 2. AUGMENTATION: armamos el prompt con las prendas reales
    prompt = TECNICAS[datos.technique](productos, datos.talla, datos.genero,
                                       datos.categoria, datos.estilo)

    # 3. GENERATION: llamamos al LLM
    res = llamar_gemini(prompt, datos.technique)

    # Buscamos en la respuesta los "id X" para que la pagina muestre esas prendas
    ids_validos = {p.id_producto for p in productos}
    ids = []
    for encontrado in re.findall(r"id\s*:?\s*(\d+)", res["texto"], flags=re.IGNORECASE):
        if int(encontrado) in ids_validos and int(encontrado) not in ids:
            ids.append(int(encontrado))

    # Se guarda la recomendacion (tabla recomendaciones)
    db.add(Recomendacion(filtros=f"talla {datos.talla}, genero {datos.genero}, categoria "
                                 f"{datos.categoria}, estilo {datos.estilo or 'cualquiera'}",
                         tecnica=datos.technique, respuesta=res["texto"],
                         productos=",".join(str(i) for i in ids)))
    db.commit()

    return RecommendResponse(technique=datos.technique, recommendation=res["texto"],
                             products_considered=len(productos), product_ids=ids,
                             input_tokens=res["tok_in"], output_tokens=res["tok_out"],
                             latency_ms=res["ms"])
