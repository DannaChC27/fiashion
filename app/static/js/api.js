// Funciones compartidas: llamar a la API con fetch y mostrar mensajes al usuario.
const API = "/api/v1";

// Hace la peticion y devuelve el JSON. Si la API responde error, lanza un Error
// con el mensaje que manda el servidor ({status, message, details}).
async function api(ruta, opciones = {}) {
  const config = { headers: { "Content-Type": "application/json" }, ...opciones };
  if (config.body && typeof config.body !== "string") config.body = JSON.stringify(config.body);
  let respuesta;
  try {
    respuesta = await fetch(API + ruta, config);
  } catch (e) {
    throw Object.assign(new Error("No hay conexión con el servidor. ¿Está corriendo uvicorn?"), { status: 0 });
  }
  if (respuesta.status === 204) return null;
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    let texto = datos.message || "Ocurrió un error";
    if (respuesta.status === 422 && datos.details) {
      texto = "Datos inválidos:\n" + datos.details.map((d) => `• ${d.field.replace("body.", "")}: ${d.problem}`).join("\n");
    }
    throw Object.assign(new Error(texto), { status: respuesta.status, details: datos.details });
  }
  return datos;
}

// Mensaje flotante abajo a la derecha
function avisar(texto, tipo = "") {
  const caja = document.getElementById("mensaje");
  caja.textContent = texto;
  caja.className = tipo;
  caja.style.display = "block";
  clearTimeout(avisar.temporizador);
  avisar.temporizador = setTimeout(() => (caja.style.display = "none"), tipo === "error" ? 7000 : 4500);
}

const pesos = (n) => "$ " + Math.round(n).toLocaleString("es-CO");
const hora = (f) => new Date(f).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit", second: "2-digit" });

// Evita que un texto del servidor se interprete como HTML
function seguro(texto) {
  const div = document.createElement("div");
  div.textContent = texto ?? "";
  return div.innerHTML;
}

// localStorage puede fallar en algunos navegadores; por eso va en try/catch
function guardarLocal(clave, valor) { try { localStorage.setItem(clave, valor); } catch (e) { /* sin memoria local */ } }
function leerLocal(clave) { try { return localStorage.getItem(clave) || ""; } catch (e) { return ""; } }
