# Pruebas extra del endpoint de IA. Usan un "falso" Gemini: no gastan cuota ni necesitan clave.
import httpx


def _crear(client, **extra):
    base = {"nombre": "Chaqueta jean", "precio": 120000, "talla": "M",
            "genero": "mujer", "categoria": "chaquetas", "estilo": "urbano"}
    base.update(extra)
    assert client.post("/api/v1/productos", json=base).status_code == 201


FILTROS = {"talla": "M", "genero": "mujer", "categoria": "chaquetas", "estilo": "urbano"}


def test_sin_prendas_no_llama_al_modelo(client):
    r = client.post("/api/v1/ai/recommend", json=FILTROS)
    assert r.status_code == 200
    assert r.json()["products_considered"] == 0


def test_recomendacion_ok(client, monkeypatch):
    _crear(client)
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("GEMINI_MODEL", "modelo-falso")

    def falso(*a, **k):
        return httpx.Response(200, json={
            "candidates": [{"content": {"parts": [{"text": "id 1 - Chaqueta jean"}]}}],
            "usageMetadata": {"promptTokenCount": 100, "candidatesTokenCount": 20}})
    monkeypatch.setattr("app.llm.httpx.post", falso)

    r = client.post("/api/v1/ai/recommend", json={**FILTROS, "technique": "few_shot"})
    assert r.status_code == 200
    assert r.json()["input_tokens"] == 100
    assert r.json()["product_ids"] == [1]   # se leyo el "id 1" de la respuesta


def test_ids_inventados_por_la_ia_se_ignoran(client, monkeypatch):
    _crear(client)
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("GEMINI_MODEL", "modelo-falso")
    monkeypatch.setattr("app.llm.httpx.post", lambda *a, **k: httpx.Response(200, json={
        "candidates": [{"content": {"parts": [{"text": "id 1 y tambien id 77"}]}}]}))
    r = client.post("/api/v1/ai/recommend", json=FILTROS)
    assert r.json()["product_ids"] == [1]


def test_sin_clave_da_503(client, monkeypatch):
    _crear(client)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert client.post("/api/v1/ai/recommend", json=FILTROS).status_code == 503


def test_timeout_da_504(client, monkeypatch):
    _crear(client)
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("GEMINI_MODEL", "modelo-falso")

    def lento(*a, **k):
        raise httpx.TimeoutException("lento")
    monkeypatch.setattr("app.llm.httpx.post", lento)
    assert client.post("/api/v1/ai/recommend", json=FILTROS).status_code == 504


def test_rate_limit_da_429(client, monkeypatch):
    _crear(client)
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    monkeypatch.setenv("GEMINI_MODEL", "modelo-falso")
    monkeypatch.setattr("app.llm.httpx.post", lambda *a, **k: httpx.Response(429))
    assert client.post("/api/v1/ai/recommend", json=FILTROS).status_code == 429
