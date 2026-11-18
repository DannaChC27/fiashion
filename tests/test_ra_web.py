# Pruebas de la Realidad Aumentada (imagen y modelo 3D) y de las paginas web.
import struct


def test_modelo_3d_es_un_glb_valido(tienda):
    r = tienda.get("/api/v1/ra/1/modelo.glb")
    assert r.status_code == 200
    magia, version, largo = struct.unpack("<4sII", r.content[:12])
    assert magia == b"glTF" and version == 2 and largo == len(r.content)


def test_imagen_de_la_prenda_es_png(tienda):
    r = tienda.get("/api/v1/ra/3/prenda.png")
    assert r.status_code == 200
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_info_ra_segun_categoria(tienda):
    assert tienda.get("/api/v1/ra/3/info").json()["forma"] == "falda"
    assert tienda.get("/api/v1/ra/1/info").json()["zona"] == "torso"


def test_ra_de_producto_inexistente(tienda):
    assert tienda.get("/api/v1/ra/99/modelo.glb").status_code == 404


def test_paginas_web(client):
    assert client.get("/", follow_redirects=False).status_code in (302, 307)
    for pagina in ("index.html", "empleado.html", "admin.html"):
        r = client.get(f"/app/{pagina}")
        assert r.status_code == 200 and "FIAshion" in r.text


def test_filtros_del_catalogo(tienda):
    r = tienda.get("/api/v1/productos?categoria=chaquetas&genero=mujer&talla=M&estilo=urbano")
    assert [p["nombre"] for p in r.json()] == ["Chaqueta bomber", "Chaqueta jean"]
