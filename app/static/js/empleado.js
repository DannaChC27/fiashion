// Panel del empleado: notificaciones de reservas y estado de los probadores.
const vistas = new Set();   // notificaciones que ya se mostraron (para sonar solo con las nuevas)
let primeraCarga = true;

// Sonido corto con el navegador (no necesita archivos de audio)
function sonar() {
  try {
    const audio = new (window.AudioContext || window.webkitAudioContext)();
    const tono = audio.createOscillator();
    tono.frequency.value = 880;
    tono.connect(audio.destination);
    tono.start();
    tono.stop(audio.currentTime + 0.2);
  } catch (e) { /* algunos navegadores bloquean el sonido hasta que se hace clic */ }
}

async function cargarNotificaciones() {
  try {
    const pendientes = document.getElementById("solo-pendientes").checked;
    const lista = await api("/notificaciones" + (pendientes ? "?pendientes=true" : ""));
    const nuevas = lista.filter((n) => !n.leida);
    document.getElementById("notificaciones").innerHTML = lista.length ? lista.map((n) => `
      <tr class="${n.leida ? "" : "nuevo"}">
        <td>${hora(n.fecha)}</td>
        <td>${seguro(n.mensaje)}</td>
        <td class="estado-${n.estado_reserva}">${n.estado_reserva}</td>
        <td>${botones(n)}</td>
      </tr>`).join("") : '<tr><td colspan="4" class="suave">No hay notificaciones.</td></tr>';

    const contador = document.getElementById("contador");
    contador.hidden = !nuevas.length;
    contador.textContent = nuevas.length + " pendientes";
    if (!primeraCarga && nuevas.some((n) => !vistas.has(n.id_notificacion))) {
      sonar();
      avisar("Llegó una reserva nueva");
    }
    nuevas.forEach((n) => vistas.add(n.id_notificacion));
    primeraCarga = false;
  } catch (e) { avisar(e.message, "error"); }
}

function botones(n) {
  if (n.estado_reserva === "pendiente") {
    return `<button class="principal" onclick="accion(${n.id_reserva}, 'entregar')">Prenda entregada</button>
            <button onclick="accion(${n.id_reserva}, 'finalizar?compro=false')">Cerrar</button>`;
  }
  if (n.estado_reserva === "activa") {
    return `<button class="principal" onclick="accion(${n.id_reserva}, 'finalizar?compro=true')">Compró</button>
            <button onclick="accion(${n.id_reserva}, 'finalizar?compro=false')">No compró</button>`;
  }
  return "";
}

async function accion(idReserva, que) {
  try {
    await api(`/reservas/${idReserva}/${que}`, { method: "PATCH" });
    avisar(que.startsWith("finalizar?compro=true") ? "Venta registrada: se descontó 1 unidad del inventario" : "Listo", "ok");
    actualizar();
  } catch (e) { avisar(e.message, "error"); }
}

async function cargarProbadores() {
  try {
    const lista = await api("/probadores");
    document.getElementById("probadores").innerHTML = lista.map((p) => `
      <tr><td>${seguro(p.nombre)}</td><td class="estado-${p.estado}">${p.estado}</td>
      <td>${seguro(p.cliente)}</td><td>${seguro(p.prendas.join(", "))}</td></tr>`).join("");
  } catch (e) { /* se intenta otra vez en 3 segundos */ }
}

function actualizar() { cargarNotificaciones(); cargarProbadores(); }
document.getElementById("solo-pendientes").onchange = actualizar;
actualizar();
setInterval(actualizar, 3000);  // sincronizacion sin recargar la pagina
