// Probador virtual (Realidad Aumentada) con la cámara o con una foto.
//
// Usa MediaPipe Pose Landmarker (de Google, gratis) que corre en el navegador:
// encuentra los hombros y las caderas de la persona y encima se dibuja la prenda.
// La imagen nunca sale del equipo. Si MediaPipe no carga (por ejemplo sin internet),
// se pasa a modo manual: la prenda se acomoda arrastrándola con el mouse.

const MEDIAPIPE = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14";
const MODELO_POSE = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/1/pose_landmarker_lite.task";

// Cómo se ubica cada forma: parte del cuerpo, altura del "ancla" dentro de la imagen,
// ancho de referencia dentro de la imagen y cuánto se agranda respecto al cuerpo.
const AJUSTE = {
  camiseta: { parte: "hombros", y0: 0.12, ref: 0.60, factor: 1.35 },
  chaqueta: { parte: "hombros", y0: 0.10, ref: 0.64, factor: 1.40 },
  vestido:  { parte: "hombros", y0: 0.07, ref: 0.40, factor: 1.25 },
  pantalon: { parte: "caderas", y0: 0.05, ref: 0.56, factor: 1.60 },
  falda:    { parte: "caderas", y0: 0.10, ref: 0.40, factor: 1.50 },
};

// Para fotos reales (recortadas a la prenda) las proporciones son otras
const AJUSTE_FOTO = {
  camiseta: { parte: "hombros", y0: 0.04, ref: 0.62, factor: 1.20 },
  chaqueta: { parte: "hombros", y0: 0.04, ref: 0.66, factor: 1.20 },
  vestido:  { parte: "hombros", y0: 0.03, ref: 0.55, factor: 1.20 },
  pantalon: { parte: "caderas", y0: 0.02, ref: 0.85, factor: 1.60 },
  falda:    { parte: "caderas", y0: 0.02, ref: 0.75, factor: 1.50 },
};

let probadorActual = null;   // prenda que se está probando
let fotoReal = false;        // true si la prenda tiene una foto real subida
let imagenPrenda = null;     // PNG de la prenda
let formaPrenda = "camiseta";
let detector = null;         // PoseLandmarker de MediaPipe
let modoDetector = null;     // "VIDEO" o "IMAGE"
let flujo = null;            // cámara
let animacion = null;
let fotoCargada = null;
let manual = { activo: false, x: 320, y: 140, escala: 1, arrastrando: false };

const lienzo = () => document.getElementById("lienzo");
const estadoProbador = (t) => (document.getElementById("estado-probador").textContent = t);

async function abrirProbador(id) {
  probadorActual = prendasEnPantalla[id];
  document.getElementById("titulo-probador").textContent = `Probador virtual · ${probadorActual.nombre} (${probadorActual.talla})`;
  document.getElementById("modal-probador").classList.add("abierto");
  const info = await api(`/ra/${id}/info`);
  formaPrenda = info.forma;
  fotoReal = info.foto_real;
  imagenPrenda = new Image();
  imagenPrenda.src = `${API}/ra/${id}/prenda.png?v=${encodeURIComponent(probadorActual.imagen || probadorActual.color)}`;
  await imagenPrenda.decode().catch(() => {});
  if (fotoCargada) procesarFoto(fotoCargada);
  else pintarVacio("Marca la autorización y escoge cámara o foto.");
}

function pintarVacio(texto) {
  const c = lienzo(), ctx = c.getContext("2d");
  ctx.fillStyle = "#222"; ctx.fillRect(0, 0, c.width, c.height);
  ctx.fillStyle = "#ccc"; ctx.font = "16px sans-serif"; ctx.textAlign = "center";
  ctx.fillText(texto, c.width / 2, c.height / 2);
}

// Carga MediaPipe solo la primera vez que se necesita
async function cargarDetector(modo) {
  if (detector && modoDetector === modo) return detector;
  try {
    if (!detector) {
      estadoProbador("Cargando el detector de postura de Google (MediaPipe)...");
      const vision = await import(MEDIAPIPE);
      const archivos = await vision.FilesetResolver.forVisionTasks(MEDIAPIPE + "/wasm");
      detector = await vision.PoseLandmarker.createFromOptions(archivos, {
        baseOptions: { modelAssetPath: MODELO_POSE, delegate: "GPU" }, runningMode: modo, numPoses: 1 });
    } else {
      await detector.setOptions({ runningMode: modo });
    }
    modoDetector = modo;
    return detector;
  } catch (e) {
    console.warn("MediaPipe no cargó, se usa el modo manual", e);
    activarManual("No se pudo cargar MediaPipe (¿sin internet?). Modo manual activado.");
    return null;
  }
}

function activarManual(texto) {
  manual.activo = true;
  document.getElementById("ajuste-manual").hidden = false;
  document.getElementById("ayuda-ajuste").textContent = "Modo manual: arrastra la prenda con el mouse y ajusta el tamaño.";
  estadoProbador(texto);
}

// Dibuja la prenda según los puntos del cuerpo. "espejo" voltea la imagen (cámara frontal).
function dibujarPrenda(ctx, puntos, ancho, alto, espejo) {
  if (!imagenPrenda?.complete) return;
  const tabla = fotoReal ? AJUSTE_FOTO : AJUSTE;
  const a = tabla[formaPrenda] || tabla.camiseta;
  const anchoImg = imagenPrenda.width, altoImg = imagenPrenda.height;
  let centroX, anclaY, distancia, angulo = 0;

  if (puntos) {
    const p = (i) => ({ x: (espejo ? 1 - puntos[i].x : puntos[i].x) * ancho, y: puntos[i].y * alto });
    const [i1, i2] = a.parte === "hombros" ? [11, 12] : [23, 24];  // hombros o caderas
    const izq = p(i1), der = p(i2);
    centroX = (izq.x + der.x) / 2;
    anclaY = (izq.y + der.y) / 2;
    distancia = Math.hypot(der.x - izq.x, der.y - izq.y) * manual.escala;  // el cliente puede ajustar el tamaño
    angulo = Math.atan2(der.y - izq.y, der.x - izq.x);
    if (Math.abs(angulo) > Math.PI / 2) angulo += angulo > 0 ? -Math.PI : Math.PI;
  } else {  // modo manual
    centroX = manual.x; anclaY = manual.y;
    distancia = ancho * 0.22 * manual.escala;
  }
  const escala = (distancia * a.factor) / (a.ref * anchoImg);
  const w = anchoImg * escala, h = altoImg * escala;
  ctx.save();
  ctx.translate(centroX, anclaY);
  ctx.rotate(angulo);
  ctx.globalAlpha = 0.9;
  ctx.drawImage(imagenPrenda, -w / 2, -a.y0 * h, w, h);
  ctx.restore();
}

// ---------- Cámara ----------
async function iniciarCamara() {
  if (!document.getElementById("consentimiento").checked) { avisar("Primero marca la autorización de uso de la cámara.", "error"); return; }
  detenerProbador();
  fotoCargada = null;
  try {
    flujo = await navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480, facingMode: "user" } });
  } catch (e) { avisar("No se pudo abrir la cámara. Revisa el permiso del navegador o usa una foto.", "error"); return; }
  const video = document.getElementById("video");
  video.srcObject = flujo;
  await video.play();
  const c = lienzo();
  c.width = video.videoWidth || 640; c.height = video.videoHeight || 480;
  const d = manual.activo ? null : await cargarDetector("VIDEO");
  if (d) estadoProbador("Ponte de frente, que se vean tus hombros y tu cadera.");
  document.getElementById("ajuste-manual").hidden = false;
  const ctx = c.getContext("2d");
  const cuadro = () => {
    if (!flujo) return;
    ctx.save(); ctx.scale(-1, 1); ctx.drawImage(video, -c.width, 0, c.width, c.height); ctx.restore();  // efecto espejo
    let puntos = null;
    if (detector && !manual.activo) {
      const r = detector.detectForVideo(video, performance.now());
      puntos = r.landmarks?.[0] || null;
    }
    if (puntos || manual.activo) dibujarPrenda(ctx, puntos, c.width, c.height, true);
    animacion = requestAnimationFrame(cuadro);
  };
  cuadro();
}

// ---------- Foto ----------
function elegirFoto() {
  if (!document.getElementById("consentimiento").checked) { avisar("Primero marca la autorización de uso de la foto.", "error"); return; }
  document.getElementById("archivo-foto").click();
}

document.getElementById("archivo-foto").onchange = (evento) => {
  const archivo = evento.target.files[0];
  if (!archivo) return;
  if (!archivo.type.startsWith("image/")) { avisar("El archivo no es una imagen.", "error"); return; }
  const img = new Image();
  img.onload = () => { fotoCargada = img; procesarFoto(img); };
  img.src = URL.createObjectURL(archivo);  // la foto se queda en el navegador
  evento.target.value = "";
};

async function procesarFoto(img) {
  detenerProbador(false);
  const c = lienzo(), ctx = c.getContext("2d");
  const escala = Math.min(640 / img.width, 640 / img.height, 1);
  c.width = Math.round(img.width * escala); c.height = Math.round(img.height * escala);
  ctx.drawImage(img, 0, 0, c.width, c.height);
  let puntos = null;
  const d = manual.activo ? null : await cargarDetector("IMAGE");
  if (d) {
    puntos = d.detect(img).landmarks?.[0] || null;
    if (!puntos) activarManual("No se encontró una persona en la foto. Acomoda la prenda a mano.");
    else estadoProbador("Listo. Si no te gusta cómo quedó, prueba con una foto de frente y de cuerpo entero.");
  }
  if (!puntos) { manual.x = c.width / 2; manual.y = c.height * 0.25; }
  fotoCargada.puntos = puntos;
  document.getElementById("ajuste-manual").hidden = false;
  redibujarFoto(puntos);
}

function redibujarFoto(puntos) {
  const c = lienzo(), ctx = c.getContext("2d");
  ctx.drawImage(fotoCargada, 0, 0, c.width, c.height);
  dibujarPrenda(ctx, puntos, c.width, c.height, false);
}

function detenerProbador(limpiarFoto = true) {
  if (animacion) cancelAnimationFrame(animacion);
  animacion = null;
  if (flujo) flujo.getTracks().forEach((t) => t.stop());
  flujo = null;
  if (limpiarFoto === true) fotoCargada = null;  // al cerrar se olvida la foto
}

// ---------- Modo manual: arrastrar y cambiar tamaño ----------
const posicion = (e) => {
  const c = lienzo(), r = c.getBoundingClientRect();
  return { x: (e.clientX - r.left) * c.width / r.width, y: (e.clientY - r.top) * c.height / r.height };
};
lienzo().addEventListener("pointerdown", (e) => { if (manual.activo) { manual.arrastrando = true; Object.assign(manual, posicion(e)); refrescarManual(); } });
lienzo().addEventListener("pointermove", (e) => { if (manual.arrastrando) { Object.assign(manual, posicion(e)); refrescarManual(); } });
window.addEventListener("pointerup", () => (manual.arrastrando = false));
document.getElementById("escala").oninput = (e) => { manual.escala = e.target.value / 100; refrescarManual(); };
function refrescarManual() { if (fotoCargada && !flujo) redibujarFoto(manual.activo ? null : fotoCargada.puntos); }

document.getElementById("tab-camara").onclick = () => {
  document.getElementById("tab-camara").classList.add("activo");
  document.getElementById("tab-foto").classList.remove("activo");
  iniciarCamara();
};
document.getElementById("tab-foto").onclick = () => {
  document.getElementById("tab-foto").classList.add("activo");
  document.getElementById("tab-camara").classList.remove("activo");
  elegirFoto();
};
