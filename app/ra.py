"""
Realidad Aumentada: genera la imagen y el modelo 3D de cada prenda.

- prenda.png: dibujo de la prenda con fondo transparente. Se usa en el catalogo y
  en el probador con camara (se pone encima del cuerpo del cliente).
- modelo.glb: modelo 3D para <model-viewer> (de Google). En celulares permite verlo
  en RA con la camara.

Las prendas se dibujan a partir de una silueta (lista de puntos) segun su categoria,
con el color que tenga guardado. Asi no hace falta tener fotos ni modelos 3D hechos a mano.
"""
import json
import os
import struct

from PIL import Image, ImageDraw

CARPETA = os.getenv("RA_CACHE", os.path.join(os.path.dirname(__file__), "static", "generado"))

# Silueta de cada forma, coordenadas de 0 a 1 (x a la derecha, y hacia abajo)
SILUETAS = {
    "camiseta": [(0.38, 0.08), (0.20, 0.12), (0.02, 0.32), (0.14, 0.42), (0.24, 0.32), (0.24, 0.95),
                 (0.76, 0.95), (0.76, 0.32), (0.86, 0.42), (0.98, 0.32), (0.80, 0.12), (0.62, 0.08),
                 (0.56, 0.15), (0.50, 0.17), (0.44, 0.15)],
    "chaqueta": [(0.38, 0.06), (0.18, 0.10), (0.04, 0.86), (0.16, 0.89), (0.25, 0.36), (0.25, 0.95),
                 (0.75, 0.95), (0.75, 0.36), (0.84, 0.89), (0.96, 0.86), (0.82, 0.10), (0.62, 0.06),
                 (0.50, 0.22)],
    "pantalon": [(0.22, 0.04), (0.78, 0.04), (0.85, 0.96), (0.58, 0.96), (0.50, 0.32), (0.42, 0.96),
                 (0.15, 0.96)],
    "falda": [(0.30, 0.10), (0.70, 0.10), (0.90, 0.84), (0.10, 0.84)],
    "vestido": [(0.36, 0.04), (0.30, 0.08), (0.32, 0.38), (0.12, 0.96), (0.88, 0.96), (0.68, 0.38),
                (0.70, 0.08), (0.64, 0.04), (0.57, 0.12), (0.50, 0.14), (0.43, 0.12)],
}

# Que forma usa cada categoria (si no esta, se usa camiseta)
FORMA_POR_CATEGORIA = {
    "camisetas": "camiseta", "camisas": "camiseta", "blusas": "camiseta",
    "chaquetas": "chaqueta", "buzos": "chaqueta", "abrigos": "chaqueta",
    "pantalones": "pantalon", "jeans": "pantalon",
    "faldas": "falda", "vestidos": "vestido",
}

# Zona del cuerpo donde va la prenda en el probador (para la camara)
ZONA = {"camiseta": "torso", "chaqueta": "torso", "vestido": "torso_largo",
        "pantalon": "piernas", "falda": "cadera"}

COLORES = {
    "blanco": (240, 238, 232), "negro": (40, 40, 44), "azul": (52, 92, 170), "azul oscuro": (32, 46, 90),
    "rojo": (196, 52, 58), "verde": (62, 128, 86), "gris": (140, 140, 146), "beige": (214, 192, 156),
    "rosado": (232, 150, 170), "amarillo": (232, 196, 70), "cafe": (120, 82, 54), "café": (120, 82, 54),
    "morado": (118, 74, 150), "verde oliva": (112, 116, 64), "vinotinto": (110, 30, 46),
    "denim": (70, 102, 146), "naranja": (230, 126, 34),
}


def forma_de(categoria: str) -> str:
    return FORMA_POR_CATEGORIA.get((categoria or "").lower().strip(), "camiseta")


def color_rgb(color: str) -> tuple:
    return COLORES.get((color or "").lower().strip(), COLORES["gris"])


def _ruta(nombre: str) -> str:
    os.makedirs(CARPETA, exist_ok=True)
    return os.path.join(CARPETA, nombre)


def imagen_prenda(forma: str, color: str, tamano: int = 512) -> str:
    """Dibuja la prenda (PNG transparente) y devuelve la ruta. Se guarda para no repetir."""
    ruta = _ruta(f"{forma}_{color.replace(' ', '_')}.png")
    if os.path.exists(ruta):
        return ruta
    rgb = color_rgb(color)
    oscuro = tuple(max(c - 50, 0) for c in rgb)
    puntos = [(x * tamano, y * tamano) for x, y in SILUETAS[forma]]
    img = Image.new("RGBA", (tamano, tamano), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.polygon(puntos, fill=rgb + (255,), outline=oscuro + (255,), width=4)
    t, grosor = tamano, 3
    # detalles simples para que se reconozca la prenda
    if forma in ("camiseta", "chaqueta"):
        d.line([(0.25 * t, 0.88 * t), (0.75 * t, 0.88 * t)], fill=oscuro, width=grosor)
    if forma == "chaqueta":
        d.line([(0.50 * t, 0.22 * t), (0.50 * t, 0.95 * t)], fill=oscuro, width=grosor)
        for i in range(4):
            y = (0.34 + i * 0.15) * t
            d.ellipse([0.47 * t, y, 0.53 * t, y + 0.03 * t], fill=oscuro)
    if forma == "pantalon":
        d.line([(0.22 * t, 0.10 * t), (0.78 * t, 0.10 * t)], fill=oscuro, width=grosor)
    if forma in ("falda", "vestido"):
        y = 0.16 * t if forma == "falda" else 0.40 * t
        d.line([(0.32 * t, y), (0.68 * t, y)], fill=oscuro, width=grosor)
    img.save(ruta)
    return ruta


def _triangular(puntos: list) -> list:
    """Divide la silueta en triangulos con el metodo de "recorte de orejas" (ear clipping)."""
    def area(pts):
        return sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1])) / 2

    def dentro(p, a, b, c):
        def lado(p1, p2, p3):
            return (p1[0] - p3[0]) * (p2[1] - p3[1]) - (p2[0] - p3[0]) * (p1[1] - p3[1])
        d1, d2, d3 = lado(p, a, b), lado(p, b, c), lado(p, c, a)
        return not ((d1 < 0 or d2 < 0 or d3 < 0) and (d1 > 0 or d2 > 0 or d3 > 0))

    pts = list(puntos)
    if area(pts) < 0:
        pts.reverse()  # se trabaja en sentido antihorario
    triangulos = []
    while len(pts) > 3:
        for i in range(len(pts)):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % len(pts)]
            convexo = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]) > 0
            if convexo and not any(dentro(p, a, b, c) for p in pts if p not in (a, b, c)):
                triangulos.append((a, b, c))
                pts.pop(i)
                break
        else:
            break  # no deberia pasar con siluetas simples
    triangulos.append(tuple(pts[:3]))
    return triangulos


def _normal(a, b, c):
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    n = [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]
    largo = sum(x * x for x in n) ** 0.5 or 1
    return [x / largo for x in n]


def modelo_3d(forma: str, color: str) -> str:
    """Arma un modelo 3D (.glb) dandole grosor a la silueta. Mide unos 60 cm de alto.

    Un .glb es un archivo glTF binario: un JSON que describe la malla y despues los
    numeros (posiciones y normales de los vertices).
    """
    ruta = _ruta(f"{forma}_{color.replace(' ', '_')}.glb")
    if os.path.exists(ruta):
        return ruta
    alto, grosor = 0.6, 0.04
    # en 3D el eje y va hacia arriba, por eso se invierte la y de la silueta
    plano = [((x - 0.5) * alto, (1 - y) * alto) for x, y in SILUETAS[forma]]

    caras = []
    for a, b, c in _triangular(plano):  # frente y espalda
        caras.append([(a[0], a[1], grosor), (b[0], b[1], grosor), (c[0], c[1], grosor)])
        caras.append([(a[0], a[1], -grosor), (c[0], c[1], -grosor), (b[0], b[1], -grosor)])
    for (x1, y1), (x2, y2) in zip(plano, plano[1:] + plano[:1]):  # bordes
        caras.append([(x1, y1, grosor), (x1, y1, -grosor), (x2, y2, -grosor)])
        caras.append([(x1, y1, grosor), (x2, y2, -grosor), (x2, y2, grosor)])

    posiciones, normales = [], []
    for cara in caras:
        n = _normal(*cara)
        for v in cara:
            posiciones.extend(v)
            normales.extend(n)
    binario = struct.pack(f"<{len(posiciones)}f", *posiciones) + struct.pack(f"<{len(normales)}f", *normales)
    total = len(posiciones) // 3
    xs, ys, zs = posiciones[0::3], posiciones[1::3], posiciones[2::3]
    r, g, b = color_rgb(color)
    gltf = {
        "asset": {"version": "2.0", "generator": "FIAshion"},
        "scene": 0, "scenes": [{"nodes": [0]}], "nodes": [{"mesh": 0, "name": forma}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0, "NORMAL": 1}, "material": 0}]}],
        "materials": [{"doubleSided": True, "pbrMetallicRoughness": {
            # glTF pide el color en espacio lineal: por eso se eleva a 2.2
            "baseColorFactor": [(r / 255) ** 2.2, (g / 255) ** 2.2, (b / 255) ** 2.2, 1],
            "metallicFactor": 0, "roughnessFactor": 0.85}}],
        "buffers": [{"byteLength": len(binario)}],
        "bufferViews": [{"buffer": 0, "byteOffset": 0, "byteLength": total * 12},
                        {"buffer": 0, "byteOffset": total * 12, "byteLength": total * 12}],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": total, "type": "VEC3",
             "min": [min(xs), min(ys), min(zs)], "max": [max(xs), max(ys), max(zs)]},
            {"bufferView": 1, "componentType": 5126, "count": total, "type": "VEC3"}],
    }
    texto = json.dumps(gltf).encode()
    texto += b" " * (-len(texto) % 4)          # los bloques deben medir multiplos de 4
    binario += b"\0" * (-len(binario) % 4)
    largo_total = 12 + 8 + len(texto) + 8 + len(binario)
    with open(ruta, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, largo_total))
        f.write(struct.pack("<I4s", len(texto), b"JSON") + texto)
        f.write(struct.pack("<I4s", len(binario), b"BIN\0") + binario)
    return ruta
