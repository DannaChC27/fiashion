# Pruebas de reservas, probadores y notificaciones (lo que se planteo en la fase 1).
import threading


def reservar(client, id_producto, cliente="Laura Gomez"):
    return client.post("/api/v1/reservas", json={"id_producto": id_producto, "nombre_cliente": cliente})


def test_reserva_asigna_probador_y_notifica(tienda):
    r = reservar(tienda, 1)
    assert r.status_code == 201
    assert r.json()["probador"] == "Probador 1"
    assert r.json()["estado"] == "pendiente"
    probadores = tienda.get("/api/v1/probadores").json()
    assert probadores[0]["estado"] == "ocupado"
    aviso = tienda.get("/api/v1/notificaciones?pendientes=true").json()[0]
    assert "Chaqueta jean" in aviso["mensaje"] and "Probador 1" in aviso["mensaje"]


def test_prenda_agotada_da_409_con_parecidas(tienda):
    assert reservar(tienda, 1).status_code == 201          # la chaqueta jean solo tiene 1
    r = reservar(tienda, 1, "Carlos Ruiz")
    assert r.status_code == 409
    assert "ya no esta disponible" in r.json()["message"]
    assert r.json()["details"][0]["nombre"] == "Chaqueta bomber"


def test_no_reserva_dos_veces_la_misma_prenda(tienda):
    assert reservar(tienda, 2).status_code == 201
    r = reservar(tienda, 2)
    assert r.status_code == 409
    assert r.json()["message"] == "Ya tiene esta prenda reservada"


def test_mismo_cliente_mismo_probador(tienda):
    a = reservar(tienda, 2).json()
    b = reservar(tienda, 3).json()
    assert a["probador"] == b["probador"]


def test_sin_probadores_libres_no_guarda_nada(tienda):
    assert reservar(tienda, 2, "Ana").status_code == 201
    assert reservar(tienda, 3, "Beto").status_code == 201
    r = reservar(tienda, 2, "Carla")            # los 2 probadores estan ocupados
    assert r.status_code == 409
    assert "probadores" in r.json()["message"]
    assert len(tienda.get("/api/v1/reservas").json()) == 2   # transaccion: no quedo nada a medias


def test_dos_clientes_al_tiempo_por_la_ultima_unidad(tienda):
    resultados = []

    def intentar(nombre):
        resultados.append(reservar(tienda, 1, nombre).status_code)

    hilos = [threading.Thread(target=intentar, args=(f"Cliente {i}",)) for i in range(4)]
    for h in hilos:
        h.start()
    for h in hilos:
        h.join()
    assert sorted(resultados) == [201, 409, 409, 409]


def test_entregar_y_finalizar_con_venta(tienda):
    reserva = reservar(tienda, 2).json()
    assert tienda.patch(f"/api/v1/reservas/{reserva['id_reserva']}/entregar").json()["estado"] == "activa"
    r = tienda.patch(f"/api/v1/reservas/{reserva['id_reserva']}/finalizar?compro=true")
    assert r.json()["estado"] == "finalizada"
    assert tienda.get("/api/v1/productos/2").json()["stock"] == 2          # tenia 3
    assert tienda.get("/api/v1/inventario/movimientos").json()[0]["tipo"] == "salida"
    assert tienda.get("/api/v1/probadores").json()[0]["estado"] == "disponible"


def test_cancelar_libera_la_prenda(tienda):
    reserva = reservar(tienda, 1).json()
    assert tienda.get("/api/v1/productos/1").json()["libres"] == 0
    tienda.patch(f"/api/v1/reservas/{reserva['id_reserva']}/cancelar")
    assert tienda.get("/api/v1/productos/1").json()["libres"] == 1
    assert tienda.get("/api/v1/probadores").json()[0]["estado"] == "disponible"


def test_reserva_cerrada_no_se_puede_volver_a_cerrar(tienda):
    reserva = reservar(tienda, 2).json()
    tienda.patch(f"/api/v1/reservas/{reserva['id_reserva']}/cancelar")
    assert tienda.patch(f"/api/v1/reservas/{reserva['id_reserva']}/finalizar").status_code == 409


def test_nombre_vacio_da_422(tienda):
    assert reservar(tienda, 1, "   ").status_code == 422


def test_reserva_de_producto_inexistente_da_404(tienda):
    assert reservar(tienda, 999).status_code == 404


def test_maximo_cinco_reservas(tienda):
    for i in range(5):
        tienda.post("/api/v1/productos", json={"nombre": f"Prenda {i}", "precio": 1000, "stock": 2})
    ids = [p["id_producto"] for p in tienda.get("/api/v1/productos").json()][:6]
    codigos = [reservar(tienda, i, "Muchas Compras").status_code for i in ids]
    assert codigos[:5] == [201] * 5 and codigos[5] == 409


def test_probador_duplicado_y_ocupado(tienda):
    assert tienda.post("/api/v1/probadores", json={"nombre": "probador 1"}).status_code == 409
    reservar(tienda, 2)
    assert tienda.delete("/api/v1/probadores/1").status_code == 409


def test_producto_con_reservas_no_se_elimina(tienda):
    reservar(tienda, 2)
    assert tienda.delete("/api/v1/productos/2").status_code == 409
