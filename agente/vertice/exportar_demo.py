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
  const R = (cuerpo, status = 200) => Promise.resolve(new Response(JSON.stringify(cuerpo), { status, headers: { "Content-Type": "application/json" } }));
  const mas = (iso, min) => { const d = new Date(iso + "Z"); d.setUTCMinutes(d.getUTCMinutes() + min); return d.toISOString().slice(0, 19); };
  const cruza = (a1, b1, a2, b2) => a1 < b2 && b1 > a2;
  function libres(fecha, servicio) {
    const base = F.dispo[fecha + "|" + servicio] || {};
    const dur = F.duraciones[servicio] || 30, out = {};
    for (const [hora, profs] of Object.entries(base)) {
      const ini = `${fecha}T${hora}:00`, fin = mas(ini, dur);
      const libresAqui = profs.filter(p =>
        ![...citas.values()].some(c => c.id >= 100000 && c.estado !== "cancelada" && c.profesional === p && cruza(ini, fin, c.inicio, c.fin)) &&
        ![...bloqueos.values()].some(b => b.id >= 100000 && (b.profesional === "" || b.profesional === p) && cruza(ini, fin, b.inicio, b.fin)));
      if (libresAqui.length) out[hora] = libresAqui;
    }
    return out;
  }
  window.fetch = async (url, opts = {}) => {
    const u = new URL(url, "https://demo.local"), ruta = u.pathname.replace("/panel/api", ""), q = u.searchParams;
    const metodo = (opts.method || "GET").toUpperCase(), cuerpo = opts.body ? JSON.parse(opts.body) : {};
    if (metodo === "GET") {
      if (ruta === "/sesion") return R(F["/sesion"]);
      if (ruta === "/resumen") return R(F["/resumen?dias=" + q.get("dias")] || F["/resumen?dias=7"]);
      if (ruta === "/agenda") {
        const desde = q.get("desde"), hasta = new Date(desde + "T00:00:00Z"); hasta.setUTCDate(hasta.getUTCDate() + 7);
        const h = hasta.toISOString().slice(0, 10);
        return R({ desde, dias: 7, citas: [...citas.values()].filter(c => c.inicio >= desde && c.inicio < h).sort((a, b) => a.inicio.localeCompare(b.inicio)),
                   bloqueos: [...bloqueos.values()].filter(b => b.inicio < h && b.fin > desde) });
      }
      if (ruta === "/disponibilidad") return R({ fecha: q.get("fecha"), libres: libres(q.get("fecha"), q.get("servicio")) });
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
      citas.set(c.id, c);
      return R({ cita_id: c.id, fecha: cuerpo.fecha, hora: cuerpo.hora, profesional: prof });
    }
    let m;
    if (metodo === "POST" && (m = ruta.match(/^\/citas\/(\d+)\/estado$/))) { const c = citas.get(+m[1]); if (c) c.estado = cuerpo.estado; return R({ ok: true }); }
    if (metodo === "POST" && ruta === "/bloqueos") {
      if (cuerpo.hasta <= cuerpo.desde) return R({ detail: "La hora final debe ser mayor que la inicial." }, 400);
      const b = { id: sig++, profesional: cuerpo.profesional || "", inicio: `${cuerpo.fecha}T${cuerpo.desde}:00`, fin: `${cuerpo.fecha}T${cuerpo.hasta}:00`, motivo: cuerpo.motivo || "" };
      bloqueos.set(b.id, b); return R({ bloqueo_id: b.id });
    }
    if (metodo === "DELETE" && (m = ruta.match(/^\/bloqueos\/(\d+)$/))) { bloqueos.delete(+m[1]); return R({ ok: true }); }
    if (metodo === "POST" && (m = ruta.match(/^\/casos\/(\d+)\/resolver$/))) { const c = casos.casos.find(x => x.id === +m[1]); if (c) c.estado = "resuelta"; return R({ ok: true }); }
    return R({ detail: "No disponible en la demo." }, 404);
  };
  try { sessionStorage.setItem("vp", JSON.stringify(["clinica-demo", "demo123"])); } catch (_) {}
})();
</script>
"""

AVISO = ('<div style="background:var(--warn-soft);color:var(--fg);padding:8px max(16px, env(safe-area-inset-left, 0px));'
         'font-size:.85rem;border-bottom:1px solid var(--line)"><strong>Demo con datos de ejemplo.</strong> '
         'Las conversaciones son pruebas reales del asistente; puedes agendar, bloquear y marcar citas, '
         'pero los cambios no se guardan (se borran al recargar).</div>')


def exportar(foto: str, salida: str) -> None:
    html = PANEL.read_text(encoding="utf-8")
    cabeza = html[html.index("<title>"):html.index("</head>")]
    cuerpo = html[html.index("<body>") + len("<body>"):html.index("</body>")]
    cabeza = cabeza.replace("<title>Panel de la clínica · Vértice</title>",
                            '<title>Panel Vértice · Demo</title>\n<meta name="claude:viewport-fit-sides" content="cover">')
    simulador = SIMULADOR.replace("__FOTO__", Path(foto).read_text(encoding="utf-8"))
    cuerpo = cuerpo.replace('<section id="login"', AVISO + '\n<section id="login"', 1)
    cuerpo = cuerpo.replace("<script>", simulador + "\n<script>", 1)
    Path(salida).write_text(cabeza + cuerpo, encoding="utf-8")
    print("Generado", salida)


if __name__ == "__main__":
    exportar(sys.argv[1], sys.argv[2])
