# Pruebas de la ropa real: subir la foto y el escaneo 3D de una prenda.
import io

from PIL import Image


def png_con_fondo_transparente():
    img = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    img.paste((200, 30, 30, 255), (100, 50, 200, 250))   # la "prenda" ocupa solo el centro
    datos = io.BytesIO()
    img.save(datos, "PNG")
    return datos.getvalue()


def test_subir_foto_real_la_recorta_y_la_usa(tienda):
    r = tienda.post("/api/v1/ra/1/imagen", files={"archivo": ("chaqueta.png", png_con_fondo_transparente(), "image/png")})
    assert r.status_code == 200
    assert tienda.get("/api/v1/ra/1/info").json()["foto_real"] is True
    servida = Image.open(io.BytesIO(tienda.get("/api/v1/ra/1/prenda.png").content))
    assert servida.size == (100, 200)                   # se recorto a la prenda
    assert tienda.get("/api/v1/productos/1").json()["imagen"].startswith("prenda_1_")


def test_subir_escaneo_glb(tienda):
    glb = tienda.get("/api/v1/ra/2/modelo.glb").content   # un .glb valido para la prueba
    r = tienda.post("/api/v1/ra/1/modelo", files={"archivo": ("escaneo.glb", glb, "model/gltf-binary")})
    assert r.status_code == 200
    assert tienda.get("/api/v1/ra/1/info").json()["modelo_real"] is True
    assert tienda.get("/api/v1/ra/1/modelo.glb").content == glb


def test_archivos_invalidos(tienda):
    texto = b"esto no es una imagen"
    assert tienda.post("/api/v1/ra/1/imagen", files={"archivo": ("x.png", texto, "image/png")}).status_code == 400
    assert tienda.post("/api/v1/ra/1/modelo", files={"archivo": ("x.glb", texto, "model/gltf-binary")}).status_code == 400
    assert tienda.post("/api/v1/ra/99/imagen", files={"archivo": ("x.png", png_con_fondo_transparente(), "image/png")}).status_code == 404


def test_quitar_foto_vuelve_a_la_dibujada(tienda):
    tienda.post("/api/v1/ra/1/imagen", files={"archivo": ("c.png", png_con_fondo_transparente(), "image/png")})
    assert tienda.delete("/api/v1/ra/1/imagen").status_code == 204
    assert tienda.get("/api/v1/ra/1/info").json()["foto_real"] is False
    assert tienda.get("/api/v1/ra/1/prenda.png").status_code == 200
