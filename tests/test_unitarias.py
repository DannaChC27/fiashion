# Pruebas unitarias: funciones sueltas, sin API ni base de datos.
import struct

from app import ra
from app.models import Producto
from app.prompts import TECNICAS


def _prendas():
    return [Producto(id_producto=4, nombre="Chaqueta jean", categoria="chaquetas", talla="M",
                     estilo="urbano", precio=120000)]


def test_cada_tecnica_arma_su_prompt_con_el_catalogo():
    for nombre, funcion in TECNICAS.items():
        texto = funcion(_prendas(), "M", "mujer", "chaquetas", "urbano")
        assert "id 4: Chaqueta jean" in texto, nombre
        assert "talla M, genero mujer, categoria chaquetas, estilo urbano" in texto


def test_few_shot_trae_ejemplos_y_cot_pide_pasos():
    assert "Ejemplo 1" in TECNICAS["few_shot"](_prendas(), "M", "mujer", "chaquetas", None)
    assert "paso a paso" in TECNICAS["cot"](_prendas(), "M", "mujer", "chaquetas", None)


def test_forma_segun_categoria():
    assert ra.forma_de("Pantalones") == "pantalon"
    assert ra.forma_de("vestidos") == "vestido"
    assert ra.forma_de("algo raro") == "camiseta"   # forma por defecto


def test_color_desconocido_usa_gris():
    assert ra.color_rgb("fucsia neon") == ra.COLORES["gris"]


def test_triangulacion_de_las_siluetas():
    for forma, puntos in ra.SILUETAS.items():
        triangulos = ra._triangular(puntos)
        assert len(triangulos) == len(puntos) - 2, forma   # un poligono de n lados da n-2 triangulos


def test_modelo_3d_tiene_cabecera_glb(tmp_path, monkeypatch):
    monkeypatch.setattr("app.ra.CARPETA", str(tmp_path))
    with open(ra.modelo_3d("falda", "rojo"), "rb") as f:
        datos = f.read()
    assert struct.unpack("<4sII", datos[:12]) == (b"glTF", 2, len(datos))
