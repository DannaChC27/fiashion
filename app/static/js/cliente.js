// Pantalla del cliente: filtros, recomendaciones con IA, 3D, probador y reservas.
const $ = (id) => document.getElementById(id);
let prendasEnPantalla = {};  // id_producto -> prenda (para no volver a pedirla)

function filtros() {
  return { talla: $("talla").value, genero: $("genero").value, categoria: $("categoria").value, estilo: $("estilo").value };
}

// Llena el selector de categorías con las que existen en el catálogo
async function cargarCategorias() {
  try {
    const productos = await api("/productos");
    const categorias = [...new Set(productos.map((p) => p.categoria))].sort();
    $("categoria").innerHTML = categorias.map((c) => `<option>${seguro(c)}</option>`).join("");
    if (categorias.includes("chaquetas")) $("categoria").value = "chaquetas";
  } catch (e) { avisar(e.message, "error"); }
}

function tarjeta(p, recomendada = false) {
  prendasEnPantalla[p.id_producto] = p;
  const agotada = p.libres <= 0;
  return `
    <div class="prenda ${recomendada ? "recomendada" : ""}">
      ${recomendada ? '<span class="etiqueta ia">Recomendada por la IA</span>' : ""}
      <img src="${API}/ra/${p.id_producto}/prenda.png?v=${encodeURIComponent(p.imagen || p.color)}" alt="${seguro(p.nombre)}" loading="lazy">
      <div class="nombre">${seguro(p.nombre)}</div>
      <div class="suave">${seguro(p.categoria)} · ${seguro(p.estilo)} · color ${seguro(p.color)}</div>
      <div><span class="etiqueta">Talla ${seguro(p.talla)}</span> <span class="etiqueta">${agotada ? "Agotada" : p.libres + " disponibles"}</span>
        ${p.imagen ? '<span class="etiqueta">Foto real</span>' : ""} ${p.modelo_3d ? '<span class="etiqueta">Escaneo 3D</span>' : ""}</div>
      <div class="precio">${pesos(p.precio)}</div>
      <div class="acciones">
        <button onclick="ver3D(${p.id_producto})">Ver en 3D / RA</button>
        <button onclick="abrirProbador(${p.id_producto})">Probarme</button>
        <button class="principal" onclick="reservar(${p.id_producto})" ${agotada ? "disabled" : ""}>Reservar</button>
      </div>
    </div>`;
}

function pintar(lista, idsRecomendados = []) {
  // primero las recomendadas por la IA, despues las demas
  const orden = [...lista].sort((a, b) => idsRecomendados.indexOf(b.id_producto) - idsRecomendados.indexOf(a.id_producto));
  $("lista").innerHTML = orden.length
    ? orden.map((p) => tarjeta(p, idsRecomendados.includes(p.id_producto))).join("")
    : '<p class="suave">No hay prendas disponibles con esos filtros. Prueba con otra talla o sin estilo.</p>';
}

async function verCatalogo() {
  const f = filtros();
  const params = new URLSearchParams({ talla: f.talla, genero: f.genero, categoria: f.categoria, solo_disponibles: true });
  if (f.estilo) params.set("estilo", f.estilo);
  try {
    const lista = await api("/productos?" + params);
    $("titulo-lista").textContent = `Catálogo (${lista.length})`;
    pintar(lista);
    return lista;
  } catch (e) { avisar(e.message, "error"); return []; }
}

async function recomendar() {
  const f = filtros();
  const boton = $("btn-ia");
  boton.disabled = true;
  boton.textContent = "Pensando...";
  $("zona-ia").hidden = false;
  $("ia-texto").textContent = "La IA está revisando las prendas disponibles...";
  $("ia-meta").textContent = "";
  try {
    const cuerpo = { talla: f.talla, genero: f.genero, categoria: f.categoria, technique: $("tecnica").value };
    if (f.estilo) cuerpo.estilo = f.estilo;
    const r = await api("/ai/recommend", { method: "POST", body: cuerpo });
    // la IA a veces usa **negrita** de markdown: se muestra como negrita de verdad
    $("ia-texto").innerHTML = seguro(r.recommendation).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>");
    $("ia-meta").textContent = r.products_considered
      ? `· ${r.technique} · ${r.products_considered} prendas revisadas · ${r.latency_ms} ms` : "";
    const lista = await verCatalogo();
    pintar(lista, r.product_ids || []);
    $("titulo-lista").textContent = r.product_ids?.length ? "Prendas recomendadas y demás opciones" : `Catálogo (${lista.length})`;
  } catch (e) {
    // Sin IA (sin clave, sin internet o sin cuota) igual se muestran las prendas que cumplen los filtros
    const motivos = {
      503: "La IA no está configurada: falta GEMINI_API_KEY o GEMINI_MODEL en el archivo .env.",
      429: "Se alcanzó el límite gratis de Gemini. Espera un minuto y vuelve a intentar.",
      504: "Gemini tardó demasiado en responder.",
      502: "No se pudo usar Gemini (revisa la clave o la conexión).",
    };
    $("ia-texto").textContent = (motivos[e.status] || e.message) + "\nMientras tanto, estas son las prendas que cumplen tus filtros.";
    await verCatalogo();
  } finally {
    boton.disabled = false;
    boton.textContent = "Recomendarme con IA";
  }
}

// ---------- 3D ----------
function ver3D(id) {
  const p = prendasEnPantalla[id];
  $("titulo-3d").textContent = `${p.nombre} · talla ${p.talla}`;
  $("visor").src = `${API}/ra/${id}/modelo.glb?v=${encodeURIComponent(p.modelo_3d || p.color)}`;
  $("modal-3d").classList.add("abierto");
}
function cerrarModal(id) { $(id).classList.remove("abierto"); }

// ---------- Reservas ----------
function nombreCliente() {
  const nombre = $("nombre").value.trim();
  if (nombre.length < 2) {
    avisar("Escribe tu nombre arriba para poder reservar.", "error");
    $("nombre").focus();
    return null;
  }
  guardarLocal("fiashion_nombre", nombre);
  return nombre;
}

async function reservar(id) {
  const nombre = nombreCliente();
  if (!nombre) return;
  try {
    const r = await api("/reservas", { method: "POST", body: { id_producto: id, nombre_cliente: nombre } });
    avisar(`¡Reserva lista!\n${r.prenda} talla ${r.talla}\nDirígete al ${r.probador}. Un empleado te llevará la prenda.`, "ok");
    cargarMisReservas();
    verCatalogo();
  } catch (e) {
    let texto = e.message;
    if (e.status === 409 && e.details?.length) {
      texto += "\n\nPrendas parecidas disponibles:\n" + e.details.map((d) => `• ${d.nombre} (${pesos(d.precio)})`).join("\n");
    }
    avisar(texto, "error");
  }
}

async function cancelar(id) {
  try {
    await api(`/reservas/${id}/cancelar`, { method: "PATCH" });
    avisar("Reserva cancelada");
    cargarMisReservas();
  } catch (e) { avisar(e.message, "error"); }
}

async function cargarMisReservas() {
  const nombre = $("nombre").value.trim();
  if (nombre.length < 2) return;
  try {
    const reservas = await api("/reservas?nombre_cliente=" + encodeURIComponent(nombre));
    $("mis-reservas").innerHTML = reservas.length ? reservas.map((r) => `
      <tr>
        <td>${seguro(r.prenda)}</td><td>${seguro(r.talla)}</td><td>${seguro(r.probador)}</td>
        <td class="estado-${r.estado}">${r.estado}</td><td>${hora(r.creada_en)}</td>
        <td>${["pendiente", "activa"].includes(r.estado) ? `<button class="peligro" onclick="cancelar(${r.id_reserva})">Cancelar</button>` : ""}</td>
      </tr>`).join("") : '<tr><td colspan="6" class="suave">Aún no tienes reservas.</td></tr>';
  } catch (e) { /* si falla se intenta en la siguiente vuelta */ }
}

// ---------- Inicio ----------
$("btn-ia").onclick = recomendar;
$("btn-catalogo").onclick = () => { $("zona-ia").hidden = true; verCatalogo(); };
$("nombre").value = leerLocal("fiashion_nombre");
$("nombre").onchange = () => { guardarLocal("fiashion_nombre", $("nombre").value.trim()); cargarMisReservas(); };
$("btn-reservar-probador").onclick = () => { if (probadorActual) reservar(probadorActual.id_producto); };

cargarCategorias().then(verCatalogo);
cargarMisReservas();
setInterval(cargarMisReservas, 5000);  // sincronizacion: el estado se actualiza solo
