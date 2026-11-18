"""Mete prendas y probadores de ejemplo para probar el sistema. Uso: python seed.py"""
from app.database import Base, engine, SessionLocal
from app.models import Producto, Probador

Base.metadata.create_all(bind=engine)

# nombre, precio, talla, genero, categoria, estilo, color, stock
datos = [
    ("Chaqueta de jean oversize", 129900, "M", "mujer", "chaquetas", "urbano", "denim", 3),
    ("Chaqueta de jean oversize", 129900, "S", "mujer", "chaquetas", "urbano", "denim", 2),
    ("Chaqueta bomber negra", 159900, "M", "mujer", "chaquetas", "urbano", "negro", 2),
    ("Chaqueta impermeable", 189900, "M", "unisex", "chaquetas", "deportivo", "amarillo", 2),
    ("Chaqueta de cuero sintetico", 210000, "M", "mujer", "chaquetas", "urbano", "cafe", 1),
    ("Blazer gris", 185000, "L", "hombre", "chaquetas", "formal", "gris", 1),
    ("Camisa de lino", 89900, "S", "mujer", "camisas", "casual", "beige", 3),
    ("Camisa de lino", 89900, "M", "mujer", "camisas", "casual", "beige", 2),
    ("Camisa blanca de vestir", 99900, "L", "hombre", "camisas", "formal", "blanco", 4),
    ("Camiseta basica", 35000, "M", "unisex", "camisetas", "casual", "blanco", 5),
    ("Camiseta oversize negra", 48000, "M", "unisex", "camisetas", "urbano", "negro", 3),
    ("Camiseta deportiva", 45000, "L", "hombre", "camisetas", "deportivo", "azul", 3),
    ("Pantalon cargo", 119900, "L", "hombre", "pantalones", "urbano", "verde oliva", 2),
    ("Jean clasico", 110000, "M", "mujer", "pantalones", "casual", "denim", 4),
    ("Pantalon de tela", 120000, "L", "hombre", "pantalones", "formal", "negro", 2),
    ("Jogger", 75000, "M", "unisex", "pantalones", "deportivo", "gris", 3),
    ("Falda plisada", 69000, "S", "mujer", "faldas", "formal", "negro", 2),
    ("Falda de jean", 72000, "M", "mujer", "faldas", "casual", "denim", 2),
    ("Falda larga", 89000, "M", "mujer", "faldas", "formal", "vinotinto", 1),
    ("Vestido casual", 135000, "M", "mujer", "vestidos", "casual", "azul", 2),
    ("Vestido de fiesta", 195000, "M", "mujer", "vestidos", "formal", "rojo", 1),
    ("Vestido de verano", 118000, "S", "mujer", "vestidos", "urbano", "morado", 2),
]
SINGULAR = {"chaquetas": "Chaqueta", "camisas": "Camisa", "camisetas": "Camiseta",
            "pantalones": "Pantalon", "faldas": "Falda", "vestidos": "Vestido"}

with SessionLocal() as db:
    if not db.query(Producto).count():
        for n, p, t, g, c, e, col, st in datos:
            db.add(Producto(nombre=n, precio=p, talla=t, genero=g, categoria=c, estilo=e,
                            color=col, stock=st, descripcion=f"{SINGULAR[c]} {e} color {col}"))
    if not db.query(Probador).count():
        for i in range(1, 5):
            db.add(Probador(nombre=f"Probador {i}", estado="disponible"))
    db.commit()
print("Listo")
