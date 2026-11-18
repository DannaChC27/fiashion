"""Calcula cuantas unidades de una prenda siguen libres para reservar."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Producto, Reserva

ESTADOS_ABIERTOS = ("pendiente", "activa")  # reservas que "apartan" una unidad


def unidades_libres(db: Session, producto: Producto) -> int:
    reservadas = db.scalar(select(func.count(Reserva.id_reserva)).where(
        Reserva.id_producto == producto.id_producto,
        Reserva.estado.in_(ESTADOS_ABIERTOS)))
    return max(producto.stock - reservadas, 0)


def con_libres(db: Session, producto: Producto) -> dict:
    """Producto como diccionario + el campo 'libres' (para ProductoOut)."""
    datos = {c.name: getattr(producto, c.name) for c in Producto.__table__.columns}
    datos["libres"] = unidades_libres(db, producto) if producto.disponible else 0
    return datos
