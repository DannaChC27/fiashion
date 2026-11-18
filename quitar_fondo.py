"""
Le quita el fondo a las fotos de la ropa para usarlas en el probador virtual.

Uso:
    pip install "rembg[cpu]"          (solo la primera vez)
    (la primera vez que se usa descarga el modelo u2net, de unos 170 MB)
    python quitar_fondo.py fotos_ropa

Toma todas las fotos (.jpg, .jpeg, .png, .webp) de la carpeta, les quita el fondo,
las recorta justo a la prenda y las guarda como PNG en la carpeta "fotos_sin_fondo".
Luego se suben desde el panel del administrador (boton "Subir foto").

Consejos para la foto: prenda de frente, estirada o en un gancho, sobre una pared o
sabana de un color distinto al de la prenda y con buena luz.
"""
import os
import sys

from PIL import Image

try:
    from rembg import new_session, remove
except ImportError:
    sys.exit('Falta rembg. Instalelo con:  pip install "rembg[cpu]"')

EXTENSIONES = (".jpg", ".jpeg", ".png", ".webp")


def procesar(carpeta: str, salida: str = "fotos_sin_fondo"):
    if not os.path.isdir(carpeta):
        sys.exit(f"No existe la carpeta '{carpeta}'")
    os.makedirs(salida, exist_ok=True)
    fotos = [f for f in sorted(os.listdir(carpeta)) if f.lower().endswith(EXTENSIONES)]
    if not fotos:
        sys.exit("La carpeta no tiene fotos JPG, PNG o WEBP")
    sesion = new_session("u2net")  # modelo libre y liviano para separar el objeto del fondo
    for nombre in fotos:
        with Image.open(os.path.join(carpeta, nombre)) as foto:
            sin_fondo = remove(foto.convert("RGB"), session=sesion)  # devuelve una imagen RGBA
        caja = sin_fondo.getchannel("A").point(lambda v: 255 if v > 128 else 0).getbbox()  # recorta a la prenda
        if caja:
            sin_fondo = sin_fondo.crop(caja)
        destino = os.path.join(salida, os.path.splitext(nombre)[0] + ".png")
        sin_fondo.save(destino)
        print(f"Listo: {destino}")
    print(f"\n{len(fotos)} fotos procesadas. Ahora subalas desde el panel del administrador.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("Uso: python quitar_fondo.py carpeta_con_fotos")
    procesar(sys.argv[1])
