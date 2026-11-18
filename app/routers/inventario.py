"""Entradas, salidas y ajustes de stock. Cada cambio queda guardado como movimiento."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.disponibilidad import unidades_libres
from app.errors import ConflictoError
from app.models import MovimientoInventario, Producto
from app.schemas import ErrorOut, MovimientoCreate, MovimientoOut

router = APIRouter(prefix="/api/v1/inventario", tags=["Inventory"])


@router.post("/movimientos", response_model=MovimientoOut, status_code=status.HTTP_201_CREATED,
             responses={404: {"model": ErrorOut, "description": "Product not found"},
                        409: {"model": ErrorOut, "description": "Not enough free units"}},
             summary="Register a stock movement",
             description="entrada adds units, salida removes free units and ajuste sets the "
                         "stock after counting. Reserved units cannot be removed.")
def registrar(datos: MovimientoCreate, db: Session = Depends(get_db)):
    producto = db.get(Producto, datos.id_producto)
    if producto is None:
        raise HTTPException(404, "Producto no encontrado")
    if datos.tipo != "ajuste" and datos.cantidad == 0:
        raise ConflictoError("La cantidad debe ser mayor que 0")

    libres = unidades_libres(db, producto)
    reservadas = producto.stock - libres
    if datos.tipo == "entrada":
        producto.stock += datos.cantidad
    elif datos.tipo == "salida":
        if datos.cantidad > libres:
            raise ConflictoError(f"No hay suficientes unidades libres (libres: {libres})")
        producto.stock -= datos.cantidad
    else:  # ajuste: la cantidad es el nuevo stock
        if datos.cantidad < reservadas:
            raise ConflictoError(f"El stock no puede quedar por debajo de las {reservadas} unidades reservadas")
        producto.stock = datos.cantidad

    movimiento = MovimientoInventario(**datos.model_dump())
    db.add(movimiento)
    db.commit()
    db.refresh(movimiento)
    return movimiento


@router.get("/movimientos", response_model=List[MovimientoOut],
            summary="Stock movement history", description="Newest first. Can be filtered by product.")
def historial(id_producto: Optional[int] = None, db: Session = Depends(get_db)):
    consulta = select(MovimientoInventario).order_by(MovimientoInventario.id_movimiento.desc()).limit(200)
    if id_producto:
        consulta = consulta.where(MovimientoInventario.id_producto == id_producto)
    return db.scalars(consulta).all()
