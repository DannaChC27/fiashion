// Panel del administrador: CRUD de prendas, inventario y probadores.
const $ = (id) => document.getElementById(id);
const CAMPOS = ["nombre", "precio", "talla", "genero", "categoria", "estilo", "color", "stock", "descripcion", "disponible"];
let productos = [];

// ---------- Prendas ----------
async function cargarProductos() {
  try {
    productos = await api("/productos");
    $("productos").innerHTML = productos.map((p) => `
      <tr>
        <td>${p.id_producto}</td><td>${seguro(p.nombre)}${p.imagen ? ' <span class="etiqueta">foto</span>' : ""}${p.modelo_3d ? ' <span class="etiqueta">3D</span>' : ""}</td><td>${seguro(p.talla)}</td><td>${seguro(p.categoria)}</td>
        <td>${pesos(p.precio)}</td><td>${p.stock}</td><td class="${p.libres <= 1 ? "estado-ocupado" : ""}">${p.libres}</td>
        <td>${p.disponible ? "Sí" : "No"}</td>
        <td><button onclick="editar(${p.id_producto})">Editar</button>
            <button class="peligro" onclick="eliminar(${p.id_producto})">Eliminar</button></td>
      </tr>`).join("");
    $("m-producto").innerHTML = productos.map((p) =>
      `<option value="${p.id_producto}">${seguro(p.nombre)} (${seguro(p.talla)}) · stock ${p.stock}</option>`).join("");
  } catch (e) { avisar(e.message, "error"); }
}

function editar(id) {
  const p = productos.find((x) => x.id_producto === id);
  $("id-producto").value = id;
  CAMPOS.forEach((c) => ($("f-" + c).value = String(p[c])));
  $("modo").textContent = `Editando la prenda ${id}`;
  mostrarArchivos(p);
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function nueva() {
  $("id-producto").value = "";
  CAMPOS.forEach((c) => ($("f-" + c).value = { talla: "M", genero: "mujer", categoria: "camisetas", estilo: "casual", color: "blanco", stock: "1", disponible: "true" }[c] || ""));
  $("modo").textContent = "Creando una prenda nueva";
  $("archivos-reales").hidden = true;
}

async function guardar() {
  const datos = {};
  CAMPOS.forEach((c) => (datos[c] = $("f-" + c).value));
  datos.nombre = datos.nombre.trim();
  if (!datos.nombre) { avisar("El nombre no puede estar vacío", "error"); return; }
  if (!(Number(datos.precio) > 0)) { avisar("El precio debe ser un número mayor que 0", "error"); return; }
  datos.precio = Number(datos.precio);
  datos.stock = Number(datos.stock || 0);
  datos.disponible = datos.disponible === "true";
  const id = $("id-producto").value;
  try {
    await api(id ? `/productos/${id}` : "/productos", { method: id ? "PUT" : "POST", body: datos });
    avisar("Prenda guardada", "ok");
    nueva();
    cargarProductos();
  } catch (e) { avisar(e.message, "error"); }
}

async function eliminar(id) {
  if (!confirm("¿Eliminar esta prenda?")) return;
  try {
    await api(`/productos/${id}`, { method: "DELETE" });
    avisar("Prenda eliminada", "ok");
    cargarProductos();
  } catch (e) { avisar(e.message, "error"); }
}

// ---------- Ropa real: foto y escaneo 3D ----------
function mostrarArchivos(p) {
  $("archivos-reales").hidden = false;
  $("vista-foto").src = `${API}/ra/${p.id_producto}/prenda.png?v=${encodeURIComponent(p.imagen || p.color)}`;
  $("estado-archivos").textContent = `Foto: ${p.imagen ? "real" : "dibujada"} · Modelo 3D: ${p.modelo_3d ? "escaneo real" : "generado"}`;
}

// Los archivos se mandan con FormData (no como JSON)
async function subirArchivo(tipo) {
  const id = $("id-producto").value;
  const archivo = $(tipo === "imagen" ? "archivo-imagen" : "archivo-modelo").files[0];
  if (!archivo) { avisar("Primero elija el archivo", "error"); return; }
  const datos = new FormData();
  datos.append("archivo", archivo);
  try {
    const r = await fetch(`${API}/ra/${id}/${tipo}`, { method: "POST", body: datos });
    const cuerpo = await r.json();
    if (!r.ok) throw new Error(cuerpo.message || "No se pudo subir el archivo");
    avisar(tipo === "imagen" ? "Foto guardada" : "Modelo 3D guardado", "ok");
    $("archivo-imagen").value = ""; $("archivo-modelo").value = "";
    await cargarProductos();
    editar(Number(id));
  } catch (e) { avisar(e.message, "error"); }
}

async function quitarArchivo(tipo) {
  const id = $("id-producto").value;
  try {
    await api(`/ra/${id}/${tipo}`, { method: "DELETE" });
    avisar(tipo === "imagen" ? "Se volvió a la imagen dibujada" : "Se volvió al modelo generado", "ok");
    await cargarProductos();
    editar(Number(id));
  } catch (e) { avisar(e.message, "error"); }
}

// ---------- Inventario ----------
async function cargarMovimientos() {
  try {
    const lista = await api("/inventario/movimientos");
    const nombre = (id) => { const p = productos.find((x) => x.id_producto === id); return p ? `${p.nombre} (${p.talla})` : id; };
    $("movimientos").innerHTML = lista.length ? lista.map((m) => `
      <tr><td>${new Date(m.fecha).toLocaleString("es-CO")}</td><td>${seguro(nombre(m.id_producto))}</td>
      <td>${m.tipo}</td><td>${m.cantidad}</td><td>${seguro(m.motivo)}</td></tr>`).join("")
      : '<tr><td colspan="5" class="suave">Aún no hay movimientos.</td></tr>';
  } catch (e) { avisar(e.message, "error"); }
}

async function registrarMovimiento() {
  const cantidad = $("m-cantidad").value;
  if (cantidad === "") { avisar("Escribe la cantidad", "error"); return; }
  try {
    await api("/inventario/movimientos", { method: "POST", body: {
      id_producto: Number($("m-producto").value), tipo: $("m-tipo").value,
      cantidad: Number(cantidad), motivo: $("m-motivo").value } });
    avisar("Movimiento registrado", "ok");
    $("m-cantidad").value = ""; $("m-motivo").value = "";
    await cargarProductos();
    cargarMovimientos();
  } catch (e) { avisar(e.message, "error"); }
}

// ---------- Probadores ----------
async function cargarProbadores() {
  try {
    const lista = await api("/probadores");
    $("lista-probadores").innerHTML = lista.map((p) => `
      <tr><td>${seguro(p.nombre)}</td><td class="estado-${p.estado}">${p.estado}</td><td>${seguro(p.cliente)}</td>
      <td><button class="peligro" onclick="eliminarProbador(${p.id_probador})">Eliminar</button></td></tr>`).join("");
  } catch (e) { avisar(e.message, "error"); }
}

async function agregarProbador() {
  try {
    await api("/probadores", { method: "POST", body: { nombre: $("p-nombre").value } });
    $("p-nombre").value = "";
    cargarProbadores();
  } catch (e) { avisar(e.message, "error"); }
}

async function eliminarProbador(id) {
  try { await api(`/probadores/${id}`, { method: "DELETE" }); cargarProbadores(); }
  catch (e) { avisar(e.message, "error"); }
}

$("btn-guardar").onclick = guardar;
$("btn-subir-imagen").onclick = () => subirArchivo("imagen");
$("btn-subir-modelo").onclick = () => subirArchivo("modelo");
$("btn-quitar-imagen").onclick = () => quitarArchivo("imagen");
$("btn-quitar-modelo").onclick = () => quitarArchivo("modelo");
$("btn-nueva").onclick = nueva;
$("btn-movimiento").onclick = registrarMovimiento;
$("btn-probador").onclick = agregarProbador;
cargarProductos().then(cargarMovimientos);
cargarProbadores();
