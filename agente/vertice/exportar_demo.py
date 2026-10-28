"""Genera una copia del panel que funciona sola en el navegador (sin servidor), con una foto de los datos.

Uso:  python -m vertice.exportar_demo foto.json ../demo/panel-demo.html
La foto se toma de un servidor en marcha (ver demo/README o la bitácora). Los cambios en la copia no se guardan.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

PANEL = Path(__file__).with_name("panel.html")

SIMULADOR = r"""
<script>
// Simulador de la API del panel: responde con la foto de datos y aplica los cambios solo en esta pestaña.
(() => {
  const F = __FOTO__;
  const citas = new Map(), bloqueos = new Map();
  for (const [k, v] of Object.entries(F)) if (k.startsWith("/agenda")) { v.citas.forEach(c => citas.set(c.id, c)); v.bloqueos.forEach(b => bloqueos.set(b.id, b)); }
  let sig = 100000;
  const casos = F["/casos"];
  // Roles de la demo: "Ver como" cambia lo que muestra el panel (el servidor real hace cumplir los mismos permisos).
  const ROLES = {
    dueno: { nombre: "Dr. Juan Pérez", rol: "dueno", rol_texto: "Dueño", profesional: "", p: ["autenticado", "resumen", "agenda_ver", "agenda_editar", "estado_cita", "chats", "casos", "equipo", "historial", "datos_personales"] },
    recepcion: { nombre: "Marta Gil", rol: "recepcion", rol_texto: "Recepción", profesional: "", p: ["autenticado", "resumen", "agenda_ver", "agenda_editar", "estado_cita", "chats", "casos"] },
    odontologo: { nombre: "Dra. Laura Gómez", rol: "odontologo", rol_texto: "Odontólogo", profesional: "Dra. Laura Gómez", p: ["autenticado", "agenda_ver", "estado_cita"] },
  };
  const ROL = ROLES[sessionStorage.getItem("demo_rol")] || ROLES.dueno;
  const usuarios = F["/usuarios"], bitacora = F["/bitacora?dias=30"];
  const hoyIso = () => { const d = new Date(); return F["/sesion"].hoy + "T" + String(d.getHours()).padStart(2, "0") + ":" + String(d.getMinutes()).padStart(2, "0") + ":00"; };
  const anotar = (accion, detalle) => bitacora.unshift({ id: sig++, quien: ROL.nombre, rol: ROL.rol, accion, detalle, creado: hoyIso() });
  const R = (cuerpo, status = 200) => Promise.resolve(new Response(JSON.stringify(cuerpo), { status, headers: { "Content-Type": "application/json" } }));
  const mas = (iso, min) => { const d = new Date(iso + "Z"); d.setUTCMinutes(d.getUTCMinutes() + min); return d.toISOString().slice(0, 19); };
  const cruza = (a1, b1, a2, b2) => a1 < b2 && b1 > a2;
  const PROFS = F["/profesionales"], sesion = F["/sesion"], editados = new Set();   // editados o nuevos: sus horas se calculan en vivo
  const NOMBRE_DIA = ["domingo", "lunes", "martes", "miercoles", "jueves", "viernes", "sabado"];
  const aMin = hhmm => +hhmm.slice(0, 2) * 60 + +hhmm.slice(3, 5), deMin = m => String(Math.floor(m / 60)).padStart(2, "0") + ":" + String(m % 60).padStart(2, "0");
  function generar(fecha, servicio, nombre, dur) {   // horas libres de un odontólogo según su horario, sus servicios, festivos y lo ya ocupado
    const p = PROFS.profesionales.find(x => x.nombre === nombre);
    if (!p || !p.activo || (!p.todos_los_servicios && !p.servicios.includes(servicio))) return [];
    if (sesion.festivos[fecha] && !sesion.abre_festivos) return [];
    const franjas = (sesion.horario_profesionales[nombre] || sesion.horario)[NOMBRE_DIA[new Date(fecha + "T12:00:00").getDay()]] || [];
    const horas = [];
    for (const [a, b] of (franjas.length && typeof franjas[0] === "string" ? [franjas] : franjas)) for (let m = aMin(a); m + dur <= aMin(b); m += 30) horas.push(deMin(m));
    return horas;
  }
  function libres(fecha, servicio, excluir = 0) {
    const base = {}, dur = F.duraciones[servicio] || 30, out = {};
    const nombres = new Set(PROFS.profesionales.filter(x => x.activo).map(x => x.nombre));
    // "Hoy" se calcula con el horario (la foto de datos depende de la hora a la que se tomó y de noche saldría vacía)
    const calculados = fecha === sesion.hoy ? nombres : editados;
    for (const [hora, profs] of Object.entries(F.dispo[fecha + "|" + servicio] || {})) { const ok = profs.filter(p => nombres.has(p) && !calculados.has(p)); if (ok.length) base[hora] = ok; }
    for (const nombre of calculados) for (const hora of generar(fecha, servicio, nombre, dur)) (base[hora] = base[hora] || []).push(nombre);
    for (const [hora, profs] of Object.entries(base)) {
      const ini = `${fecha}T${hora}:00`, fin = mas(ini, dur);
      const libresAqui = profs.filter(p =>
        ![...citas.values()].some(c => (c.id >= 100000 || c.movida || calculados.has(p)) && c.id !== excluir && c.estado !== "cancelada" && c.profesional === p && cruza(ini, fin, c.inicio, c.fin)) &&
        ![...bloqueos.values()].some(b => (b.id >= 100000 || calculados.has(p)) && (b.profesional === "" || b.profesional === p) && cruza(ini, fin, b.inicio, b.fin)));
      if (libresAqui.length) out[hora] = libresAqui;
    }
    return Object.fromEntries(Object.entries(out).sort());
  }
  window.fetch = async (url, opts = {}) => {
    const u = new URL(url, "https://demo.local"), ruta = u.pathname.replace("/panel/api", ""), q = u.searchParams;
    const metodo = (opts.method || "GET").toUpperCase(), cuerpo = opts.body ? JSON.parse(opts.body) : {};
    if (metodo === "GET") {
      if (ruta === "/sesion") return R({ ...F["/sesion"], usuario: { nombre: ROL.nombre, rol: ROL.rol, rol_texto: ROL.rol_texto, profesional: ROL.profesional, soporte: false }, permisos: ROL.p });
      if (ruta === "/usuarios") return R(usuarios);
      if (ruta === "/profesionales") return R({ ...PROFS, profesionales: PROFS.profesionales.map(p => ({ ...p, citas_futuras: [...citas.values()].filter(c => c.profesional === p.nombre && ["confirmada", "por_confirmar"].includes(c.estado)).length })) });
      if (ruta === "/solicitudes") {  // la espera se toma de la foto (la demo no tiene reloj propio)
        const esperas = Object.fromEntries((F["/solicitudes"] || []).map(c => [c.id, c.espera_min]));
        const lista = [...citas.values()].filter(c => c.estado === "por_confirmar" && (ROL.rol !== "odontologo" || c.profesional === ROL.profesional))
          .map(c => ({ ...c, espera_min: esperas[c.id] ?? 0 }));
        return R(lista.sort((a, b) => b.espera_min - a.espera_min));
      }
      if (ruta === "/bitacora") { const dias = +(q.get("dias") || 7), corte = new Date(Date.now() - dias * 86400000).toISOString().slice(0, 10); return R(bitacora.filter(f => f.creado.slice(0, 10) >= (dias >= 30 ? "0000" : F["/sesion"].hoy.slice(0, 8) + String(Math.max(1, +F["/sesion"].hoy.slice(8) - dias)).padStart(2, "0")))); }
      if (ruta === "/resumen") return R(F["/resumen?dias=" + q.get("dias")] || F["/resumen?dias=7"]);
      if (ruta === "/agenda") {
        const desde = q.get("desde"), dias = +(q.get("dias") || 7), hasta = new Date(desde + "T00:00:00Z"); hasta.setUTCDate(hasta.getUTCDate() + dias);
        const h = hasta.toISOString().slice(0, 10);
        const mias = c => ROL.rol !== "odontologo" || c.profesional === ROL.profesional;
        return R({ desde, dias, citas: [...citas.values()].filter(c => c.inicio >= desde && c.inicio < h && mias(c)).sort((a, b) => a.inicio.localeCompare(b.inicio)),
                   bloqueos: [...bloqueos.values()].filter(b => b.inicio < h && b.fin > desde && (ROL.rol !== "odontologo" || !b.profesional || b.profesional === ROL.profesional)) });
      }
      if (ruta === "/disponibilidad") return R({ fecha: q.get("fecha"), libres: libres(q.get("fecha"), q.get("servicio"), +(q.get("excluir") || 0)) });
      if (ruta === "/conversaciones") return R(F["/conversaciones"]);
      if (ruta.startsWith("/conversaciones/")) return R(F.hilos[decodeURIComponent(ruta.split("/")[2])] || {}, F.hilos[decodeURIComponent(ruta.split("/")[2])] ? 200 : 404);
      if (ruta === "/casos") return R(casos);
    }
    if (metodo === "POST" && ruta === "/citas") {
      const disp = libres(cuerpo.fecha, cuerpo.servicio)[cuerpo.hora] || [];
      const prof = cuerpo.profesional ? (disp.includes(cuerpo.profesional) ? cuerpo.profesional : null) : disp[0];
      if (!prof) return R({ detail: `La hora ${cuerpo.hora} no está disponible el ${cuerpo.fecha}.` }, 409);
      const ini = `${cuerpo.fecha}T${cuerpo.hora}:00`;
      const c = { id: sig++, nombre: cuerpo.nombre, servicio: cuerpo.servicio, inicio: ini, fin: mas(ini, F.duraciones[cuerpo.servicio] || 30), estado: "confirmada", profesional: prof, origen: "panel", cliente: cuerpo.telefono || "" };
      citas.set(c.id, c); anotar("cita_creada", `${cuerpo.nombre} · ${cuerpo.servicio} · ${cuerpo.fecha} ${cuerpo.hora}`);
      return R({ cita_id: c.id, fecha: cuerpo.fecha, hora: cuerpo.hora, profesional: prof, servicio: cuerpo.servicio });
    }
    let m;
    if (metodo === "POST" && (m = ruta.match(/^\/conversaciones\/([^/]+)\/(tomar|devolver|enviar)$/))) {
      const cli = decodeURIComponent(m[1]), hilo = F.hilos[cli], item = F["/conversaciones"].find(x => x.cliente === cli);
      if (!hilo) return R({ detail: "Conversación no encontrada." }, 404);
      const hasta = F["/sesion"].hoy + "T23:59:00";
      const marcar = (pausada) => { hilo.pausada = item.pausada = pausada; hilo.pausada_hasta = item.pausada_hasta = pausada ? hasta : ""; hilo.sin_responder = item.sin_responder = false; };
      if (m[2] === "tomar") { marcar(true); return R({ pausada_hasta: hasta }); }
      if (m[2] === "devolver") { marcar(false); return R({ ok: true }); }
      if (!(cuerpo.texto || "").trim()) return R({ detail: "Escribe un mensaje." }, 400);
      const ahora = new Date(), hh = String(ahora.getHours()).padStart(2, "0") + ":" + String(ahora.getMinutes()).padStart(2, "0");
      const msg = { rol: "equipo", texto: cuerpo.texto.trim(), fecha: F["/sesion"].hoy, hora: hh, origen: "panel" };
      hilo.mensajes.push(msg); item.ultimo = msg; marcar(true);
      return R({ ok: true, enviado: false, pausada_hasta: hasta });
    }
    if (metodo === "POST" && (m = ruta.match(/^\/citas\/(\d+)\/reprogramar$/))) {
      const c = citas.get(+m[1]); if (!c || c.estado !== "confirmada") return R({ detail: "No encontré una cita confirmada con ese id." }, 404);
      const disp = libres(cuerpo.fecha, c.servicio, c.id)[cuerpo.hora] || [];
      const prof = cuerpo.profesional ? (disp.includes(cuerpo.profesional) ? cuerpo.profesional : null) : (disp.includes(c.profesional) ? c.profesional : disp[0]);
      if (!prof) return R({ detail: `La hora ${cuerpo.hora} no está disponible el ${cuerpo.fecha}.` }, 409);
      const ini = `${cuerpo.fecha}T${cuerpo.hora}:00`, antes = c.inicio;
      Object.assign(c, { inicio: ini, fin: mas(ini, F.duraciones[c.servicio] || 30), profesional: prof, movida: true }); anotar("cita_reprogramada", `Cita #${c.id} (${c.servicio}) a ${cuerpo.fecha} ${cuerpo.hora}`);
      return R({ cita_id: c.id, estado: "confirmada", servicio: c.servicio, fecha: cuerpo.fecha, hora: cuerpo.hora, profesional: prof, antes });
    }
    if (metodo === "POST" && (m = ruta.match(/^\/citas\/(\d+)\/estado$/))) { const c = citas.get(+m[1]); if (c) { c.estado = cuerpo.estado; anotar("cita_estado", `Cita #${c.id} (${c.nombre}) marcada: ${cuerpo.estado}`); } return R({ ok: true }); }
    if ((m = ruta.match(/^\/pacientes\/([^/]+)\/datos$/))) {
      const cli = decodeURIComponent(m[1]), hilo = F.hilos[cli];
      if (!hilo) return R({ detail: "Paciente no encontrado." }, 404);
      if (metodo === "GET") { anotar("datos_exportados", `Descargó los datos de un paciente (…${cli.slice(-4)})`); return R({ cliente: cli, conversaciones: [{ mensajes: hilo.mensajes }], citas: [...citas.values()].filter(c => c.cliente === cli) }); }
      if (metodo === "DELETE") {
        delete F.hilos[cli]; const i = F["/conversaciones"].findIndex(x => x.cliente === cli); if (i >= 0) F["/conversaciones"].splice(i, 1);
        [...citas.values()].filter(c => c.cliente === cli).forEach(c => { c.nombre = "Paciente eliminado"; c.cliente = "eliminado"; if (c.estado === "confirmada") c.estado = "cancelada"; });
        anotar("datos_eliminados", `Eliminó los datos de un paciente (…${cli.slice(-4)})`); return R({ conversaciones: 1 });
      }
    }
    const sincProfs = () => {   // deja la sesión (carriles del calendario, horarios) al día con la lista
      sesion.profesionales = PROFS.profesionales.filter(p => p.activo).map(p => p.nombre);
      sesion.horario_profesionales = Object.fromEntries(PROFS.profesionales.filter(p => p.activo).map(p => [p.nombre, p.horario || Object.fromEntries(Object.entries(sesion.horario))]));
    };
    const revisarProf = c => {
      if (!/^.{3,60}$/.test((c.nombre || "").trim())) return "El nombre debe tener entre 3 y 60 letras (ej.: Dra. Laura Gómez).";
      for (const [dia, turnos] of Object.entries(c.horario || {})) {
        const t = [...turnos].sort();
        for (const [a, b] of t) { if (!/^([01]\d|2[0-3]):[0-5]\d$/.test(a) || !/^([01]\d|2[0-3]):[0-5]\d$/.test(b)) return `Hora inválida en ${dia}: use el formato HH:MM.`; if (b <= a) return `En ${dia}, la hora final debe ser posterior a la inicial.`; }
        for (let i = 1; i < t.length; i++) if (t[i][0] < t[i - 1][1]) return `En ${dia}, los turnos se cruzan.`;
      }
      if (c.horario && !Object.keys(c.horario).length) return "Marca al menos un día en el que atiende, o elige el horario de la clínica.";
      return "";
    };
    if (metodo === "POST" && ruta === "/profesionales") {
      const err = revisarProf(cuerpo); if (err) return R({ detail: err }, 400);
      const nombre = cuerpo.nombre.trim().replace(/\s+/g, " ");
      if (PROFS.profesionales.some(p => p.nombre.toLowerCase() === nombre.toLowerCase())) return R({ detail: `Ya existe un odontólogo llamado '${nombre}'.` }, 409);
      const p = { id: sig++, nombre, activo: true, servicios: cuerpo.servicios || [], todos_los_servicios: !(cuerpo.servicios || []).length, horario: cuerpo.horario || null, citas_futuras: 0 };
      PROFS.profesionales.push(p); editados.add(nombre); sincProfs(); anotar("profesional_creado", `${nombre} (${p.todos_los_servicios ? "todos los servicios" : p.servicios.join(", ")})`);
      return R({ id: p.id, citas_movidas: 0 });
    }
    if ((m = ruta.match(/^\/profesionales\/(\d+)(?:\/(estado))?$/))) {
      const p = PROFS.profesionales.find(x => x.id === +m[1]); if (!p) return R({ detail: "Odontólogo no encontrado." }, 404);
      if (metodo === "PUT") {
        const err = revisarProf({ ...cuerpo, nombre: p.nombre }); if (err) return R({ detail: err }, 400);
        Object.assign(p, { servicios: cuerpo.servicios || [], todos_los_servicios: !(cuerpo.servicios || []).length, horario: cuerpo.horario || null });
        editados.add(p.nombre); sincProfs(); anotar("profesional_editado", p.nombre); return R({ ok: true, citas_futuras: 0 });
      }
      if (metodo === "POST" && m[2] === "estado") {
        if (!cuerpo.activo && p.activo && PROFS.profesionales.filter(x => x.activo).length <= 1) return R({ detail: "Debe quedar al menos un odontólogo activo." }, 400);
        p.activo = !!cuerpo.activo; sincProfs(); anotar(p.activo ? "profesional_activado" : "profesional_desactivado", p.nombre);
        return R({ ok: true, citas_futuras: [...citas.values()].filter(c => c.profesional === p.nombre && ["confirmada", "por_confirmar"].includes(c.estado)).length });
      }
    }
    if (metodo === "POST" && ruta === "/usuarios") {
      if (!/^[a-z0-9._-]{3,}$/i.test(cuerpo.usuario || "")) return R({ detail: "El usuario debe tener al menos 3 letras o números (sin espacios)." }, 400);
      if (!(cuerpo.nombre || "").trim()) return R({ detail: "Escribe el nombre de la persona." }, 400);
      if ((cuerpo.clave || "").length < 8 || !/[a-z]/i.test(cuerpo.clave) || !/\d/.test(cuerpo.clave)) return R({ detail: "La clave debe tener al menos 8 caracteres, con letras y números." }, 400);
      if (usuarios.some(u => u.usuario === cuerpo.usuario.toLowerCase())) return R({ detail: `Ya existe el usuario '${cuerpo.usuario}'.` }, 409);
      const u = { id: sig++, usuario: cuerpo.usuario.toLowerCase(), nombre: cuerpo.nombre.trim(), rol: cuerpo.rol, profesional: cuerpo.profesional || "", activo: 1, creado: hoyIso() };
      usuarios.push(u); anotar("usuario_creado", `${u.nombre} (${u.usuario}) como ${ROLES[u.rol] ? ROLES[u.rol].rol_texto : u.rol}`); return R({ id: u.id });
    }
    if (metodo === "POST" && (m = ruta.match(/^\/usuarios\/(\d+)\/(estado|clave)$/))) {
      const u = usuarios.find(x => x.id === +m[1]); if (!u) return R({ detail: "Usuario no encontrado." }, 404);
      if (m[2] === "estado") { u.activo = cuerpo.activo ? 1 : 0; anotar(cuerpo.activo ? "usuario_activado" : "usuario_desactivado", `${u.nombre} (${u.usuario})`); }
      else anotar("clave_restablecida", `Nueva clave para ${u.nombre} (${u.usuario})`);
      return R({ ok: true });
    }
    if (metodo === "POST" && ruta === "/bloqueos") {
      if (`${cuerpo.fecha_fin || cuerpo.fecha}T${cuerpo.hasta}` <= `${cuerpo.fecha}T${cuerpo.desde}`) return R({ detail: "El final del bloqueo debe ser posterior al inicio." }, 400);
      const b = { id: sig++, profesional: cuerpo.profesional || "", inicio: `${cuerpo.fecha}T${cuerpo.desde}:00`, fin: `${cuerpo.fecha_fin || cuerpo.fecha}T${cuerpo.hasta}:00`, motivo: cuerpo.motivo || "" };
      bloqueos.set(b.id, b); anotar("bloqueo_creado", `${b.profesional || "Toda la clínica"} · ${b.inicio.slice(0, 16).replace("T", " ")}`);
      const afectadas = [...citas.values()].filter(c => c.estado === "confirmada" && c.inicio < b.fin && c.fin > b.inicio && (!b.profesional || c.profesional === b.profesional));
      return R({ bloqueo_id: b.id, citas_afectadas: afectadas });
    }
    if (metodo === "DELETE" && (m = ruta.match(/^\/bloqueos\/(\d+)$/))) { bloqueos.delete(+m[1]); return R({ ok: true }); }
    if (metodo === "POST" && (m = ruta.match(/^\/casos\/(\d+)\/resolver$/))) { const c = casos.casos.find(x => x.id === +m[1]); if (c) c.estado = "resuelta"; return R({ ok: true }); }
    return R({ detail: "No disponible en la demo." }, 404);
  };
  try { sessionStorage.setItem("vp", JSON.stringify({ n: "clinica-demo", c: "demo123" })); } catch (_) {}
})();
</script>
"""

AVISO = r"""<div style="background:var(--warn-soft);color:var(--fg);padding:8px max(16px, env(safe-area-inset-left, 0px));font-size:.85rem;border-bottom:1px solid var(--line);display:flex;gap:12px;flex-wrap:wrap;align-items:center">
<span><strong>Demo con datos de ejemplo.</strong> Las conversaciones son pruebas reales del asistente; puedes agendar, bloquear y marcar citas, pero los cambios no se guardan (se borran al recargar).</span>
<label style="margin-left:auto;display:flex;gap:6px;align-items:center;font-weight:600">Ver como
<select id="demoRol" onchange="try{sessionStorage.setItem('demo_rol',this.value)}catch(_){}location.reload()" style="border:1px solid var(--line-strong);border-radius:8px;padding:4px 8px;background:var(--surface);color:var(--fg)">
<option value="dueno">Dueño</option><option value="recepcion">Recepción</option><option value="odontologo">Odontólogo (Dra. Laura)</option></select></label>
<script>try{document.getElementById("demoRol").value=sessionStorage.getItem("demo_rol")||"dueno"}catch(_){}</script></div>"""


def exportar(foto: str, salida: str) -> None:
    html = PANEL.read_text(encoding="utf-8")
    cabeza = html[html.index("<title>"):html.index("</head>")]
    cuerpo = html[html.index("<body>") + len("<body>"):html.index("</body>")]
    cabeza = cabeza.replace("<title>Panel de la clínica · Vértice</title>",
                            '<title>Panel Vértice · Demo</title>\n<meta name="claude:viewport-fit-sides" content="cover">')
    simulador = SIMULADOR.replace("__FOTO__", Path(foto).read_text(encoding="utf-8"))
    cuerpo = cuerpo.replace('<div id="login"', AVISO + '\n<div id="login"', 1)
    cuerpo = cuerpo.replace("<script>", simulador + "\n<script>", 1)
    Path(salida).write_text(cabeza + cuerpo, encoding="utf-8")
    print("Generado", salida)


if __name__ == "__main__":
    exportar(sys.argv[1], sys.argv[2])
