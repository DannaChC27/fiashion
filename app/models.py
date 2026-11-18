from datetime import datetime
from typing import Optional

from sqlalchemy import String, Float, Boolean, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Producto(Base):
    """Una prenda en una talla. Cada fila es una prenda + talla con su stock."""
    __tablename__ = "productos"

    id_producto: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100))
    descripcion: Mapped[str] = mapped_column(String(300), default="")
    precio: Mapped[float] = mapped_column(Float)
    talla: Mapped[str] = mapped_column(String(10), default="M")
    genero: Mapped[str] = mapped_column(String(20), default="unisex")
    categoria: Mapped[str] = mapped_column(String(50), default="general")
    estilo: Mapped[str] = mapped_column(String(50), default="casual")
    disponible: Mapped[bool] = mapped_column(Boolean, default=True)
    color: Mapped[str] = mapped_column(String(30), default="gris")
    stock: Mapped[int] = mapped_column(Integer, default=1)
    # Archivos reales de la prenda (opcionales). Si no hay, se usa la silueta dibujada.
    imagen: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, default=None)
    modelo_3d: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, default=None)

    reservas: Mapped[list["Reserva"]] = relationship(back_populates="producto")


class Probador(Base):
    __tablename__ = "probadores"

    id_probador: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(30), unique=True)
    estado: Mapped[str] = mapped_column(String(15), default="disponible")  # disponible | ocupado

    reservas: Mapped[list["Reserva"]] = relationship(back_populates="probador")


class Reserva(Base):
    __tablename__ = "reservas"

    id_reserva: Mapped[int] = mapped_column(primary_key=True)
    id_producto: Mapped[int] = mapped_column(ForeignKey("productos.id_producto"))
    id_probador: Mapped[int] = mapped_column(ForeignKey("probadores.id_probador"))
    nombre_cliente: Mapped[str] = mapped_column(String(80))
    # pendiente -> activa -> finalizada | cancelada
    estado: Mapped[str] = mapped_column(String(15), default="pendiente")
    creada_en: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    cerrada_en: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    producto: Mapped[Producto] = relationship(back_populates="reservas")
    probador: Mapped[Probador] = relationship(back_populates="reservas")
    notificaciones: Mapped[list["Notificacion"]] = relationship(back_populates="reserva")


class Notificacion(Base):
    """Aviso para el empleado: que prenda llevar y a que probador."""
    __tablename__ = "notificaciones"

    id_notificacion: Mapped[int] = mapped_column(primary_key=True)
    id_reserva: Mapped[int] = mapped_column(ForeignKey("reservas.id_reserva"))
    mensaje: Mapped[str] = mapped_column(String(300))
    leida: Mapped[bool] = mapped_column(Boolean, default=False)
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

    reserva: Mapped[Reserva] = relationship(back_populates="notificaciones")


class MovimientoInventario(Base):
    __tablename__ = "movimientos_inventario"

    id_movimiento: Mapped[int] = mapped_column(primary_key=True)
    id_producto: Mapped[int] = mapped_column(ForeignKey("productos.id_producto"))
    tipo: Mapped[str] = mapped_column(String(10))  # entrada | salida | ajuste
    cantidad: Mapped[int] = mapped_column(Integer)
    motivo: Mapped[str] = mapped_column(String(200), default="")
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)


class Recomendacion(Base):
    """Cada recomendacion que hizo la IA queda guardada (filtros, tecnica y respuesta)."""
    __tablename__ = "recomendaciones"

    id_recomendacion: Mapped[int] = mapped_column(primary_key=True)
    filtros: Mapped[str] = mapped_column(String(300))
    tecnica: Mapped[str] = mapped_column(String(20))
    respuesta: Mapped[str] = mapped_column(Text)
    productos: Mapped[str] = mapped_column(String(200), default="")  # ids recomendados, ej "3,5"
    fecha: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
