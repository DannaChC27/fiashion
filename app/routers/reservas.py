"""
Reservas de prendas, asignacion automatica de probador y notificaciones al empleado.

Es lo que se describio en la fase 1 (Procesos, Sincronizacion y Transacciones):
- Antes de guardar se revisa si la prenda tiene unidades libres.
- Si no tiene, se avisa y se muestran prendas parecidas.
- Si tiene, se busca un probador "disponible" y en UNA sola transaccion se guarda
  la reserva y el probador pasa a "ocupado". Si algo falla no se guarda nada.
- Las reservas se procesan una por una (candado), asi dos clientes no se quedan
  con la misma prenda.
- Al final se crea la notificacion para el empleado.
"""
import threading
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_db
from app.disponibilidad import ESTADOS_ABIERTOS, unidades_libres
from app.errors import ConflictoError
from app.models import MovimientoInventario, Notificacion, Probador, Producto, Reserva
from app.schemas import (ErrorOut, NotificacionOut, ProbadorCreate, ProbadorOut, ReservaCreate,
                         ReservaOut)

router = APIRouter(prefix="/api/v1", tags=["Reservations"])

MAX_RESERVAS_POR_CLIENTE = 5
_candado = threading.Lock()  # una reserva a la vez

CONFLICTO = {409: {"model": ErrorOut, "description": "Business rule not met"}}
NO_EXISTE = {404: {"model": ErrorOut, "description": "Not found"}}


def _reserva_out(r: Reserva) -> ReservaOut:
    return ReservaOut(id_reserva=r.id_reserva, id_producto=r.id_producto, prenda=r.producto.nombre,
                      talla=r.producto.talla, nombre_cliente=r.nombre_cliente,
                      probador=r.probador.nombre, estado=r.estado, creada_en=r.creada_en)


def _parecidas(db: Session, base: Producto, cantidad: int = 3) -> list[dict]:
    """Prendas de la misma talla y categoria (o estilo) que si tienen unidades libres."""
    candidatas = db.scalars(select(Producto).where(
        Producto.id_producto != base.id_producto, Producto.disponible.is_(True),
        Producto.talla == base.talla, Producto.genero.in_([base.genero, "unisex"]))).all()
    parecidas = []
    for p in candidatas:
        puntos = (2 if p.categoria == base.categoria else 0) + (1 if p.estilo == base.estilo else 0)
        if puntos and unidades_libres(db, p) > 0:
            parecidas.append((puntos, p))
    parecidas.sort(key=lambda x: -x[0])
    return [{"id_producto": p.id_producto, "nombre": p.nombre, "precio": p.precio}
            for _, p in parecidas[:cantidad]]


def _liberar_probador_si_queda_vacio(db: Session, probador: Probador):
    db.flush()
    abiertas = db.scalar(select(func.count(Reserva.id_reserva)).where(
        Reserva.id_probador == probador.id_probador, Reserva.estado.in_(ESTADOS_ABIERTOS)))
    if abiertas == 0:
        probador.estado = "disponible"


# ---------- Reservas ----------

@router.post("/reservas", response_model=ReservaOut, status_code=status.HTTP_201_CREATED,
             responses={**CONFLICTO, **NO_EXISTE},
             summary="Reserve a product and get a fitting room",
             description="Checks availability, assigns a free fitting room and notifies the "
                         "employee, all in one transaction. If the product is no longer "
                         "available it answers 409 with similar products in details.")
def reservar(datos: ReservaCreate, db: Session = Depends(get_db)):
    with _candado:  # sincronizacion: una reserva a la vez
        try:
            producto = db.get(Producto, datos.id_producto)
            if producto is None or not producto.disponible:
                raise HTTPException(404, "Producto no encontrado")

            abiertas = db.scalars(select(Reserva).where(
                Reserva.nombre_cliente == datos.nombre_cliente,
                Reserva.estado.in_(ESTADOS_ABIERTOS))).all()
            if any(r.id_producto == producto.id_producto for r in abiertas):
                raise ConflictoError("Ya tiene esta prenda reservada")
            if len(abiertas) >= MAX_RESERVAS_POR_CLIENTE:
                raise ConflictoError(f"Solo puede tener {MAX_RESERVAS_POR_CLIENTE} prendas reservadas a la vez")
            if unidades_libres(db, producto) <= 0:
                raise ConflictoError(f"'{producto.nombre}' talla {producto.talla} ya no esta disponible",
                                     details=_parecidas(db, producto))

            # Si el cliente ya tiene probador, la prenda nueva va al mismo
            probador = abiertas[0].probador if abiertas else db.scalar(
                select(Probador).where(Probador.estado == "disponible").order_by(Probador.id_probador))
            if probador is None:
                raise ConflictoError("Todos los probadores estan ocupados. Intente en unos minutos")

            reserva = Reserva(id_producto=producto.id_producto, id_probador=probador.id_probador,
                              nombre_cliente=datos.nombre_cliente, estado="pendiente")
            probador.estado = "ocupado"
            db.add(reserva)
            db.flush()  # para tener el id de la reserva
            db.add(Notificacion(id_reserva=reserva.id_reserva, mensaje=(
                f"Llevar '{producto.nombre}' talla {producto.talla} al {probador.nombre} "
                f"para {datos.nombre_cliente}")))
            db.commit()  # transaccion: todo junto
        except Exception:
            db.rollback()  # si algo falla no queda nada a medias
            raise
        db.refresh(reserva)
        return _reserva_out(reserva)


@router.get("/reservas", response_model=List[ReservaOut],
            summary="List reservations",
            description="Lists reservations, newest first. Can be filtered by customer name or state.")
def listar_reservas(nombre_cliente: Optional[str] = None, estado: Optional[str] = None,
                    db: Session = Depends(get_db)):
    consulta = select(Reserva).order_by(Reserva.id_reserva.desc())
    if nombre_cliente:
        consulta = consulta.where(Reserva.nombre_cliente == nombre_cliente.strip())
    if estado:
        consulta = consulta.where(Reserva.estado == estado)
    return [_reserva_out(r) for r in db.scalars(consulta).all()]


def _buscar(db: Session, reserva_id: int) -> Reserva:
    reserva = db.get(Reserva, reserva_id)
    if reserva is None:
        raise HTTPException(404, "Reserva no encontrada")
    return reserva


@router.patch("/reservas/{reserva_id}/entregar", response_model=ReservaOut,
              responses={**CONFLICTO, **NO_EXISTE},
              summary="Employee delivered the product",
              description="Marks a pending reservation as active (the product is in the fitting room).")
def entregar(reserva_id: int, db: Session = Depends(get_db)):
    with _candado:
        reserva = _buscar(db, reserva_id)
        if reserva.estado != "pendiente":
            raise ConflictoError(f"La reserva esta {reserva.estado}")
        reserva.estado = "activa"
        for n in reserva.notificaciones:
            n.leida = True
        db.commit()
        return _reserva_out(reserva)


@router.patch("/reservas/{reserva_id}/finalizar", response_model=ReservaOut,
              responses={**CONFLICTO, **NO_EXISTE},
              summary="Close a reservation",
              description="Closes the reservation. If compro=true one unit is taken from the stock "
                          "and an inventory movement is saved. The fitting room is freed when empty.")
def finalizar(reserva_id: int, compro: bool = False, db: Session = Depends(get_db)):
    with _candado:
        reserva = _buscar(db, reserva_id)
        if reserva.estado not in ESTADOS_ABIERTOS:
            raise ConflictoError("Esta reserva ya fue cerrada")
        reserva.estado = "finalizada"
        reserva.cerrada_en = datetime.now()
        for n in reserva.notificaciones:
            n.leida = True
        if compro:
            reserva.producto.stock -= 1
            db.add(MovimientoInventario(id_producto=reserva.id_producto, tipo="salida", cantidad=1,
                                        motivo=f"Venta en probador (reserva {reserva.id_reserva})"))
        _liberar_probador_si_queda_vacio(db, reserva.probador)
        db.commit()
        return _reserva_out(reserva)


@router.patch("/reservas/{reserva_id}/cancelar", response_model=ReservaOut,
              responses={**CONFLICTO, **NO_EXISTE},
              summary="Cancel a reservation",
              description="The customer cancels. The product and the fitting room are freed.")
def cancelar(reserva_id: int, db: Session = Depends(get_db)):
    with _candado:
        reserva = _buscar(db, reserva_id)
        if reserva.estado not in ESTADOS_ABIERTOS:
            raise ConflictoError("Esta reserva ya fue cerrada")
        reserva.estado = "cancelada"
        reserva.cerrada_en = datetime.now()
        for n in reserva.notificaciones:
            n.leida = True
        _liberar_probador_si_queda_vacio(db, reserva.probador)
        db.commit()
        return _reserva_out(reserva)


# ---------- Notificaciones ----------

@router.get("/notificaciones", response_model=List[NotificacionOut],
            summary="Employee notifications",
            description="What product to take to which fitting room. pendientes=true shows only unread.")
def notificaciones(pendientes: bool = False, db: Session = Depends(get_db)):
    consulta = select(Notificacion).order_by(Notificacion.id_notificacion.desc()).limit(100)
    if pendientes:
        consulta = consulta.where(Notificacion.leida.is_(False))
    return [NotificacionOut(id_notificacion=n.id_notificacion, id_reserva=n.id_reserva,
                            mensaje=n.mensaje, leida=n.leida, fecha=n.fecha,
                            estado_reserva=n.reserva.estado)
            for n in db.scalars(consulta).all()]


# ---------- Probadores ----------

@router.get("/probadores", response_model=List[ProbadorOut], tags=["Fitting rooms"],
            summary="List fitting rooms", description="State of each fitting room and who is using it.")
def listar_probadores(db: Session = Depends(get_db)):
    salida = []
    for p in db.scalars(select(Probador).order_by(Probador.id_probador)).all():
        abiertas = [r for r in p.reservas if r.estado in ESTADOS_ABIERTOS]
        salida.append(ProbadorOut(id_probador=p.id_probador, nombre=p.nombre, estado=p.estado,
                                  cliente=abiertas[0].nombre_cliente if abiertas else "",
                                  prendas=[f"{r.producto.nombre} ({r.producto.talla})" for r in abiertas]))
    return salida


@router.post("/probadores", response_model=ProbadorOut, status_code=status.HTTP_201_CREATED,
             tags=["Fitting rooms"], responses=CONFLICTO,
             summary="Create a fitting room", description="Adds a new free fitting room.")
def crear_probador(datos: ProbadorCreate, db: Session = Depends(get_db)):
    nombre = datos.nombre.strip()
    if db.scalar(select(Probador).where(func.lower(Probador.nombre) == nombre.lower())):
        raise ConflictoError("Ya existe un probador con ese nombre")
    probador = Probador(nombre=nombre, estado="disponible")
    db.add(probador)
    db.commit()
    db.refresh(probador)
    return ProbadorOut(id_probador=probador.id_probador, nombre=probador.nombre, estado=probador.estado)


@router.delete("/probadores/{probador_id}", status_code=status.HTTP_204_NO_CONTENT,
               tags=["Fitting rooms"], responses={**CONFLICTO, **NO_EXISTE},
               summary="Delete a fitting room", description="Only free rooms without history.")
def eliminar_probador(probador_id: int, db: Session = Depends(get_db)):
    probador = db.get(Probador, probador_id)
    if probador is None:
        raise HTTPException(404, "Probador no encontrado")
    if probador.estado == "ocupado" or probador.reservas:
        raise ConflictoError("El probador esta ocupado o tiene historial de reservas")
    db.delete(probador)
    db.commit()

