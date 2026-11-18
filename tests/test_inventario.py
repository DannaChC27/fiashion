# Pruebas del inventario (entradas, salidas y ajustes).

def mover(client, tipo, cantidad, id_producto=2):
    return client.post("/api/v1/inventario/movimientos",
                       json={"id_producto": id_producto, "tipo": tipo, "cantidad": cantidad, "motivo": "prueba"})


def test_entrada_salida_y_ajuste(tienda):
    assert mover(tienda, "entrada", 5).status_code == 201
    assert tienda.get("/api/v1/productos/2").json()["stock"] == 8
    assert mover(tienda, "salida", 2).status_code == 201
    assert mover(tienda, "ajuste", 10).status_code == 201
    assert tienda.get("/api/v1/productos/2").json()["stock"] == 10
    assert len(tienda.get("/api/v1/inventario/movimientos?id_producto=2").json()) == 3


def test_no_saca_unidades_reservadas(tienda):
    tienda.post("/api/v1/reservas", json={"id_producto": 1, "nombre_cliente": "Laura"})
    r = mover(tienda, "salida", 1, id_producto=1)
    assert r.status_code == 409
    assert "libres" in r.json()["message"]


def test_cantidad_cero_o_tipo_malo(tienda):
    assert mover(tienda, "entrada", 0).status_code == 409
    assert mover(tienda, "regalo", 1).status_code == 422
    assert mover(tienda, "entrada", -3).status_code == 422
