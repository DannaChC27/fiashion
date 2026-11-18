from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.disponibilidad import con_libres
from app.errors import ConflictoError
from app.routers.ra import borrar_archivos_reales
from app.models import MovimientoInventario, Producto
from app.schemas import ProductoCreate, ProductoOut, ErrorOut, ValidationErrorOut

router = APIRouter(prefix="/api/v1/productos", tags=["Products"])

NOT_FOUND = {404: {"model": ErrorOut, "description": "Product not found"}}
INVALID = {422: {"model": ValidationErrorOut, "description": "Invalid data"}}


@router.post("", response_model=ProductoOut, status_code=status.HTTP_201_CREATED,
             responses=INVALID,
             summary="Create a product",
             description="Creates a new product in the catalog and returns it with its id.")
def crear(datos: ProductoCreate, db: Session = Depends(get_db)):
    producto = Producto(**datos.model_dump())
    db.add(producto)
    db.commit()
    db.refresh(producto)
    return con_libres(db, producto)


@router.get("", response_model=List[ProductoOut],
            summary="List products (with optional filters)",
            description="Returns the catalog. It can be filtered by size, gender, category and "
                        "style. Gender 'unisex' products always match a gender filter.")
def listar(talla: Optional[str] = None, genero: Optional[str] = None,
           categoria: Optional[str] = None, estilo: Optional[str] = None,
           solo_disponibles: bool = False, db: Session = Depends(get_db)):
    consulta = select(Producto)
    if talla:
        consulta = consulta.where(Producto.talla == talla)
    if genero:
        consulta = consulta.where(Producto.genero.in_([genero, "unisex"]))
    if categoria:
        consulta = consulta.where(Producto.categoria == categoria)
    if estilo:
        consulta = consulta.where(Producto.estilo == estilo)
    if solo_disponibles:
        consulta = consulta.where(Producto.disponible.is_(True))
    productos = [con_libres(db, p) for p in db.scalars(consulta.order_by(Producto.nombre)).all()]
    if solo_disponibles:
        productos = [p for p in productos if p["libres"] > 0]
    return productos


@router.get("/{producto_id}", response_model=ProductoOut,
            responses={**NOT_FOUND, **INVALID},
            summary="Get a product by id",
            description="Returns one product. Responds 404 if the id does not exist.")
def obtener(producto_id: int, db: Session = Depends(get_db)):
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return con_libres(db, producto)


@router.put("/{producto_id}", response_model=ProductoOut,
            responses={**NOT_FOUND, **INVALID},
            summary="Update a product",
            description="Replaces the data of an existing product.")
def actualizar(producto_id: int, datos: ProductoCreate, db: Session = Depends(get_db)):
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    for campo, valor in datos.model_dump().items():
        setattr(producto, campo, valor)
    db.commit()
    db.refresh(producto)
    return con_libres(db, producto)


@router.delete("/{producto_id}", status_code=status.HTTP_204_NO_CONTENT,
               responses={**NOT_FOUND, **INVALID,
                          409: {"model": ErrorOut, "description": "Product has reservations"}},
               summary="Delete a product",
               description="Deletes a product. Responds 204 with no body. A product with "
                           "reservations cannot be deleted (mark it as not available instead).")
def eliminar(producto_id: int, db: Session = Depends(get_db)):
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if producto.reservas:
        raise ConflictoError("El producto tiene reservas; marquelo como no disponible")
    # el historial de inventario de esa prenda se borra con ella
    db.query(MovimientoInventario).filter(MovimientoInventario.id_producto == producto_id).delete()
    borrar_archivos_reales(producto)
    db.delete(producto)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)