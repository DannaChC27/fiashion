# FIAshion - Asesoría de moda con IA y Realidad Aumentada

FIAshion automatiza la asesoría y la atención al cliente en pymes de venta de ropa. El cliente filtra lo que busca (prenda, género/edad, talla, categoría y estilo), la Inteligencia Artificial le recomienda prendas, se las prueba con Realidad Aumentada y, si le gustan, las reserva. El sistema le asigna un probador y le avisa al empleado qué prenda llevar y a qué probador.

El proyecto es una API REST en FastAPI con una página web sencilla (HTML, CSS y JavaScript con `fetch`) que la misma API sirve.

## Tecnologías (todas gratuitas)

| Capa | Tecnología |
|---|---|
| Lenguaje | Python 3.12 |
| Backend / API | FastAPI + Uvicorn |
| Base de datos | MySQL 8 con SQLAlchemy (ORM) y PyMySQL (SQLite para las pruebas) |
| Validación | Pydantic |
| Inteligencia Artificial | Google Gemini (API gratis de AI Studio) con Zero-Shot, Few-Shot y Chain-of-Thought + RAG básico |
| Realidad Aumentada 3D | `<model-viewer>` de Google (3D en el navegador y RA en el celular) |
| Probador con cámara | MediaPipe Pose Landmarker de Google (corre en el navegador) |
| Imágenes | Pillow |
| Ropa real | rembg (quitar el fondo de las fotos) y KIRI Engine (escanear en 3D con el celular) |
| Frontend | HTML, CSS y JavaScript (`fetch`) |
| Pruebas | Pytest + TestClient |
| CI | GitHub Actions |

## Cómo abrirlo en Visual Studio Code

1. Abrir la carpeta del proyecto en VS Code (`Archivo > Abrir carpeta`). VS Code sugiere instalar la extensión de Python.
2. Copiar `.env.example` como `.env` y llenar:
   - `GEMINI_API_KEY`: la clave gratis de Gemini (https://aistudio.google.com/apikey). Sin clave todo funciona menos la recomendación con IA.
   - `DATABASE_URL`: la conexión a MySQL. Cambiar `tu_clave` por la clave del usuario `root` (la misma con la que entran a MySQL Workbench):
     `DATABASE_URL=mysql+pymysql://root:tu_clave@localhost:3306/fiashion`
   - El servicio de MySQL tiene que estar prendido (en Workbench se ve como *Local instance MySQL80*). La base `fiashion` y sus tablas se crean solas la primera vez.
   - Si no tienen MySQL, pueden usar SQLite poniendo `DATABASE_URL=sqlite:///./fiashion.db`.
3. En Windows, doble clic a `iniciar.bat`: crea el entorno, instala, carga datos de ejemplo y abre la página.

También se puede hacer a mano desde la terminal de VS Code:

```
python -m venv .venv
.venv\Scripts\activate          (en Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
python seed.py
uvicorn app.main:app --reload
```

O desde la pestaña **Ejecutar y depurar** de VS Code con la configuración *FIAshion: correr la API y la página*.

Luego abrir:

- http://127.0.0.1:8000/app/ → página del **cliente**
- http://127.0.0.1:8000/app/empleado.html → panel del **empleado**
- http://127.0.0.1:8000/app/admin.html → panel del **administrador**
- http://127.0.0.1:8000/docs → documentación de la API (Swagger, OpenAPI 3)

> Si ya tenían una base de la versión anterior (`fiashion.db` o la base `fiashion` en MySQL), bórrenla antes de `python seed.py` porque la tabla de productos tiene columnas nuevas (`color`, `stock`, `imagen` y `modelo_3d`). En Workbench: `DROP DATABASE fiashion;`

## Usar la ropa real de la tienda

Al principio cada prenda se ve con un dibujo que arma el sistema según su categoría y color. Para mostrar la ropa de verdad:

1. **Foto:** tomar la foto de la prenda colgada o extendida, de frente, sobre un fondo liso y con buena luz.
2. **Quitar el fondo** (para que en el probador solo se vea la prenda):
   ```
   pip install "rembg[cpu]"
   python quitar_fondo.py carpeta_con_las_fotos
   ```
   Quedan en `fotos_sin_fondo/` como PNG. La primera vez descarga el modelo u2net (unos 170 MB). También sirve cualquier página gratis para quitar fondos.
3. **Escaneo 3D (opcional):** con la app gratis **KIRI Engine** en el celular se le toman fotos alrededor a la prenda (por ejemplo puesta en un maniquí) y se exporta en formato `.glb`.
4. En el **panel del administrador** se pulsa *Editar* en la prenda y en "Ropa real de esta prenda" se sube la foto y/o el `.glb`. Desde ese momento el catálogo, el 3D y el probador usan esos archivos. Con *Quitar foto* o *Quitar modelo* vuelve al dibujo.

Los archivos quedan en `app/static/subidas/` y en la base de datos solo se guarda el nombre. Fotos de hasta 8 MB (JPG, PNG o WEBP) y modelos de hasta 40 MB.

## Cómo funciona

1. **Filtros:** el cliente elige talla, género, categoría y estilo.
2. **IA (RAG + prompting):** la API busca en la base de datos las prendas que cumplen los filtros y que tienen unidades libres, las pone en el prompt y le pide a Gemini hasta 3 recomendaciones. De la respuesta se leen los `id` para resaltar esas prendas en la página. Cada llamada queda en `llm_calls.csv` (tokens y latencia) y en la tabla `recomendaciones`.
3. **Realidad Aumentada:**
   - *Ver en 3D / RA:* la API arma un modelo `.glb` de la prenda (con su forma y color) y `<model-viewer>` lo muestra. En un celular el botón de RA la pone en el espacio con la cámara.
   - *Probarme:* con la cámara o con una foto, MediaPipe encuentra los hombros y la cadera y se dibuja la prenda encima. La imagen se procesa en el navegador: no se envía al servidor ni se guarda (Ley 1581 de 2012). Si MediaPipe no carga (sin internet) hay un modo manual para acomodar la prenda.
4. **Reserva:** se revisa que la prenda tenga unidades libres, se busca un probador disponible y, en **una sola transacción**, se guarda la reserva, el probador pasa a "ocupado" y se crea la notificación. Las reservas se procesan **una por una** (candado), así dos clientes no se quedan con la última unidad. Si ya no hay unidades, responde 409 con prendas parecidas.
5. **Empleado:** ve las notificaciones (se actualizan cada 3 s y suenan), marca la prenda como entregada y cierra la reserva. Si el cliente compró, se descuenta del inventario.
6. **Administrador:** CRUD de prendas, movimientos de inventario y probadores.

## Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/api/v1/productos` | Crear prenda |
| GET | `/api/v1/productos` | Listar prendas (filtros: talla, genero, categoria, estilo, solo_disponibles) |
| GET | `/api/v1/productos/{id}` | Consultar prenda |
| PUT | `/api/v1/productos/{id}` | Actualizar prenda |
| DELETE | `/api/v1/productos/{id}` | Eliminar prenda |
| POST | `/api/v1/ai/recommend` | Recomendaciones con Gemini (zero_shot, few_shot, cot) |
| GET | `/api/v1/ra/{id}/modelo.glb` | Modelo 3D para `<model-viewer>` |
| GET | `/api/v1/ra/{id}/prenda.png` | Imagen de la prenda (fondo transparente) |
| GET | `/api/v1/ra/{id}/info` | Forma y zona del cuerpo para el probador |
| POST/DELETE | `/api/v1/ra/{id}/imagen` | Subir o quitar la foto real de la prenda |
| POST/DELETE | `/api/v1/ra/{id}/modelo` | Subir o quitar el escaneo 3D (.glb) |
| POST | `/api/v1/reservas` | Reservar prenda y asignar probador |
| GET | `/api/v1/reservas` | Listar reservas (filtro por cliente o estado) |
| PATCH | `/api/v1/reservas/{id}/entregar` | El empleado llevó la prenda |
| PATCH | `/api/v1/reservas/{id}/finalizar?compro=true` | Cerrar reserva (con o sin venta) |
| PATCH | `/api/v1/reservas/{id}/cancelar` | El cliente cancela |
| GET | `/api/v1/notificaciones` | Avisos para el empleado |
| GET/POST/DELETE | `/api/v1/probadores` | Probadores |
| GET/POST | `/api/v1/inventario/movimientos` | Entradas, salidas y ajustes de stock |

En `peticiones.http` hay ejemplos que se pueden ejecutar con la extensión REST Client de VS Code.

## Estructura

```
app/
  main.py            crea la app, registra las rutas y sirve la página web
  database.py        conexión a MySQL (o SQLite); crea la base si no existe
  models.py          tablas: productos, probadores, reservas, notificaciones,
                     movimientos_inventario, recomendaciones
  schemas.py         validaciones con Pydantic
  errors.py          respuestas de error {status, message, timestamp, details}
  disponibilidad.py  unidades libres = stock - reservas abiertas
  llm.py / prompts.py  Gemini y las 3 técnicas de prompting
  ra.py              imagen PNG y modelo 3D .glb de cada prenda (dibujados)
  routers/           productos, ai, reservas, inventario, ra
  static/            página web: index.html (cliente), empleado.html, admin.html
tests/               44 pruebas (no gastan cuota de Gemini)
seed.py              datos de ejemplo
quitar_fondo.py      quita el fondo a las fotos de la ropa real
```

## Pruebas

```
pytest -v
```

Usan una base de datos SQLite en memoria (no tocan MySQL) y un Gemini "falso", así que no necesitan clave ni gastan cuota. Hay pruebas unitarias, de integración, funcionales, de validación y de aceptación. Cubren el CRUD, la IA (incluyendo timeout, límite de peticiones y falta de clave), las reservas (transacción, dos clientes al mismo tiempo, probadores llenos, ventas), el inventario, la RA, la subida de fotos y escaneos reales y las páginas.

## Seguridad y datos personales

- La clave de Gemini va en `.env` (no se sube a GitHub).
- Las fotos y el video de la cámara se procesan solo en el navegador del cliente.
- Las respuestas de error no muestran detalles internos del servidor.
