# Pruebas de aceptacion: el proceso completo como lo viviria la tienda.
import httpx


def test_compra_completa(tienda, monkeypatch):
    # 1. La clienta filtra el catalogo
    prendas = tienda.get("/api/v1/productos?talla=M&genero=mujer&categoria=chaquetas&solo_disponibles=true").json()
    assert len(prendas) == 2
    # 2. Pide recomendacion a la IA (Gemini simulado)
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("GEMINI_MODEL", "modelo-falso")
    monkeypatch.setattr("app.llm.httpx.post", lambda *a, **k: httpx.Response(200, json={
        "candidates": [{"content": {"parts": [{"text": "Te recomiendo la Chaqueta bomber (id 2)"}]}}]}))
    r = tienda.post("/api/v1/ai/recommend", json={"talla": "M", "genero": "mujer", "categoria": "chaquetas"})
    elegida = r.json()["product_ids"][0]
    assert elegida == 2
    # 3. La ve en 3D y en el probador
    assert tienda.get(f"/api/v1/ra/{elegida}/modelo.glb").status_code == 200
    assert tienda.get(f"/api/v1/ra/{elegida}/prenda.png").status_code == 200
    # 4. La reserva y le asignan probador
    reserva = tienda.post("/api/v1/reservas", json={"id_producto": elegida, "nombre_cliente": "Sofia"}).json()
    assert reserva["probador"] == "Probador 1"
    # 5. El empleado ve el aviso, lleva la prenda y registra la venta
    aviso = tienda.get("/api/v1/notificaciones?pendientes=true").json()[0]
    assert "Probador 1" in aviso["mensaje"]
    tienda.patch(f"/api/v1/reservas/{reserva['id_reserva']}/entregar")
    tienda.patch(f"/api/v1/reservas/{reserva['id_reserva']}/finalizar?compro=true")
    # 6. Baja el stock, el probador queda libre y no quedan avisos pendientes
    assert tienda.get(f"/api/v1/productos/{elegida}").json()["stock"] == 2
    assert all(p["estado"] == "disponible" for p in tienda.get("/api/v1/probadores").json())
    assert tienda.get("/api/v1/notificaciones?pendientes=true").json() == []


def test_hora_pico(tienda):
    # 2 probadores y 3 clientes: los dos primeros entran, el tercero debe esperar
    codigos = [tienda.post("/api/v1/reservas", json={"id_producto": 2, "nombre_cliente": n}).status_code
               for n in ("Ana", "Beto", "Carla")]
    assert codigos == [201, 201, 409]
    ocupados = {r["probador"] for r in tienda.get("/api/v1/reservas").json()}
    assert ocupados == {"Probador 1", "Probador 2"}
