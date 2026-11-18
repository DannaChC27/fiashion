"""
Endpoints de Realidad Aumentada: imagen y modelo 3D de cada prenda.

Cada prenda puede tener:
- una foto real (PNG con fondo transparente queda mejor en el probador) y
- un escaneo 3D real (.glb, por ejemplo hecho con KIRI Engine en el celular).
Si no los tiene, se usa la silueta dibujada con su forma y color (app/ra.py).
"""
import io
import os
import time

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Producto
from app import ra

router = APIRouter(prefix="/api/v1/ra", tags=["Augmented reality"])

CARPETA_SUBIDAS = os.getenv("SUBIDAS_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                                         "static", "subidas"))
MAX_IMAGEN_MB = 8
MAX_MODELO_MB = 40


def _producto(db: Session, producto_id: int) -> Producto:
    producto = db.get(Producto, producto_id)
    if producto is None:
        raise HTTPException(404, "Producto no encontrado")
    return producto


def _ruta_subida(nombre: str | None) -> str | None:
    """Ruta completa de un archivo subido, solo si todavia existe."""
    if not nombre:
        return None
    ruta = os.path.join(CARPETA_SUBIDAS, os.path.basename(nombre))
    return ruta if os.path.exists(ruta) else None


def _borrar(nombre: str | None):
    ruta = _ruta_subida(nombre)
    if ruta:
        os.remove(ruta)


def borrar_archivos_reales(p: Producto):
    """Se usa al eliminar una prenda: borra su foto y su modelo subidos."""
    _borrar(p.imagen)
    _borrar(p.modelo_3d)


# ---------- Consultar ----------

@router.get("/{producto_id}/prenda.png", summary="Product image",
            description="Real photo if it was uploaded; if not, a drawing of the product with its "
                        "color. Used in the catalog and in the camera fitting room.",
            response_class=FileResponse)
def imagen(producto_id: int, db: Session = Depends(get_db)):
    p = _producto(db, producto_id)
    real = _ruta_subida(p.imagen)
    if real:
        return FileResponse(real, media_type="image/png")
    return FileResponse(ra.imagen_prenda(ra.forma_de(p.categoria), p.color), media_type="image/png")


@router.get("/{producto_id}/modelo.glb", summary="3D model for <model-viewer>",
            description="Real 3D scan if it was uploaded; if not, a model made from the product "
                        "shape. <model-viewer> shows it in 3D and, on phones, in AR.",
            response_class=FileResponse)
def modelo(producto_id: int, db: Session = Depends(get_db)):
    p = _producto(db, producto_id)
    real = _ruta_subida(p.modelo_3d)
    if real:
        return FileResponse(real, media_type="model/gltf-binary")
    return FileResponse(ra.modelo_3d(ra.forma_de(p.categoria), p.color), media_type="model/gltf-binary")


@router.get("/{producto_id}/info", summary="AR info of a product",
            description="Shape and body zone used by the camera fitting room, and whether the "
                        "product has a real photo or 3D scan.")
def info(producto_id: int, db: Session = Depends(get_db)):
    p = _producto(db, producto_id)
    forma = ra.forma_de(p.categoria)
    return {"id_producto": p.id_producto, "forma": forma, "zona": ra.ZONA[forma], "color": p.color,
            "foto_real": bool(_ruta_subida(p.imagen)), "modelo_real": bool(_ruta_subida(p.modelo_3d))}


# ---------- Subir archivos reales ----------

@router.post("/{producto_id}/imagen", summary="Upload a real photo of the product",
             description="Accepts JPG, PNG or WEBP up to 8 MB. If the photo is a PNG with a "
                         "transparent background, it is cropped to the garment so it fits better "
                         "in the fitting room.")
async def subir_imagen(producto_id: int, archivo: UploadFile = File(...), db: Session = Depends(get_db)):
    p = _producto(db, producto_id)
    datos = await archivo.read()
    if len(datos) > MAX_IMAGEN_MB * 1024 * 1024:
        raise HTTPException(400, f"La foto pesa mas de {MAX_IMAGEN_MB} MB")
    try:
        img = Image.open(io.BytesIO(datos))
        img.load()
    except (UnidentifiedImageError, OSError):
        raise HTTPException(400, "El archivo no es una imagen valida (use JPG, PNG o WEBP)")
    if img.format not in ("JPEG", "PNG", "WEBP"):
        raise HTTPException(400, "Formato no permitido. Use JPG, PNG o WEBP")

    img = img.convert("RGBA")
    # si tiene fondo transparente, se recorta a la prenda (se ignoran bordes casi
    # transparentes, como el gancho, para que no queden espacios de mas)
    caja = img.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox()
    if caja:
        img = img.crop(caja)
    img.thumbnail((1024, 1024))

    os.makedirs(CARPETA_SUBIDAS, exist_ok=True)
    nombre = f"prenda_{p.id_producto}_{int(time.time())}.png"  # nombre nuevo para que el navegador no use la vieja
    img.save(os.path.join(CARPETA_SUBIDAS, nombre))
    _borrar(p.imagen)
    p.imagen = nombre
    db.commit()
    return {"id_producto": p.id_producto, "imagen": nombre}


@router.post("/{producto_id}/modelo", summary="Upload a real 3D scan (.glb)",
             description="Accepts a .glb file up to 40 MB (for example exported from KIRI Engine).")
async def subir_modelo(producto_id: int, archivo: UploadFile = File(...), db: Session = Depends(get_db)):
    p = _producto(db, producto_id)
    datos = await archivo.read()
    if len(datos) > MAX_MODELO_MB * 1024 * 1024:
        raise HTTPException(400, f"El modelo pesa mas de {MAX_MODELO_MB} MB")
    if datos[:4] != b"glTF":  # todo archivo .glb empieza asi
        raise HTTPException(400, "El archivo no es un modelo .glb valido (exporte en formato GLB)")
    os.makedirs(CARPETA_SUBIDAS, exist_ok=True)
    nombre = f"modelo_{p.id_producto}_{int(time.time())}.glb"
    with open(os.path.join(CARPETA_SUBIDAS, nombre), "wb") as f:
        f.write(datos)
    _borrar(p.modelo_3d)
    p.modelo_3d = nombre
    db.commit()
    return {"id_producto": p.id_producto, "modelo_3d": nombre}


@router.delete("/{producto_id}/imagen", status_code=204, summary="Remove the real photo",
               description="The product goes back to the drawn image.")
def quitar_imagen(producto_id: int, db: Session = Depends(get_db)):
    p = _producto(db, producto_id)
    _borrar(p.imagen)
    p.imagen = None
    db.commit()


@router.delete("/{producto_id}/modelo", status_code=204, summary="Remove the real 3D scan",
               description="The product goes back to the generated 3D model.")
def quitar_modelo(producto_id: int, db: Session = Depends(get_db)):
    p = _producto(db, producto_id)
    _borrar(p.modelo_3d)
    p.modelo_3d = None
    db.commit()
