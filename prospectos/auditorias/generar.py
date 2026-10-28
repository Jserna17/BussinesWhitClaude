"""Genera las hojas de auditoría (PDF) de las clínicas prioritarias.

    python prospectos/auditorias/generar.py

Salida en esta carpeta:
  hojas-para-entregar.pdf   una hoja por clínica, para ENTREGAR al dueño (solo datos verificados)
  guia-del-fundador.pdf     INTERNA: ruta, revisión previa de 8 minutos, guion y reglas. No se entrega.

Lo que no se pudo verificar desde el entorno de Claude (Google Maps, Instagram, biblioteca de anuncios) queda en blanco.
Para completarlo, llena `datos-presencia.json` (ver `datos-presencia.ejemplo.json`) y vuelve a ejecutar: la hoja calcula el puntaje.
Los PDF se crean con `node a-pdf.js` (Playwright + Chromium, ya instalados en el entorno de Claude).
"""

from __future__ import annotations

import html
import json
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
FECHA = "28 de octubre de 2026"

# Hechos de la prueba de WhatsApp del 27-oct (ver prospectos/mystery-shopping-2026-10-27.md). Nada de esto es estimado.
CLINICAS = [
    {
        "id": "pb", "nombre": "PB Odontología", "subtitulo": "Dra. Laura Sánchez · ortodoncia y rehabilitación",
        "direccion": "Megacentro Pinares, Torre 1, piso 12, consultorio 1211 · Pereira", "whatsapp": "318 226 9139", "web": "pbodontologia.com",
        "enviado": "Martes 27 de octubre · 9:52 p. m.", "respuesta": "Miércoles 28 de octubre · 8:15 a. m.", "espera": "≈ 10,4 horas",
        "hechos": ["No hubo respuesta esa noche.", "Por la mañana respondieron con el precio de la valoración ($90.000, abonable al tratamiento).",
                   "No se agendó cita en la conversación: la persona quedó esperando el siguiente paso."],
        "pts_whatsapp": 0, "nota_pts": "Respuesta al día siguiente",
        "acciones": ["Responder en menos de un minuto, también de noche, con el precio de la valoración y los horarios libres reales (horario partido L–V incluido).",
                     "Dejar la valoración de ortodoncia agendada en la misma conversación, sin esperar a la mañana.",
                     "Anuncios \"clic a WhatsApp\" para valoración de ortodoncia en Pereira y Dosquebradas."],
        "guia": {"apertura": "Entran a la clínica de ortodoncia con valoración abonable: cada valoración perdida es un tratamiento de alto valor.",
                 "preguntas": "¿Cuántos mensajes de pacientes nuevos reciben por semana? ¿Quién contesta y en qué horario? ¿En qué llevan la agenda?",
                 "ojo": "Comparte edificio con el consultorio del Dr. Orozco: no mencionar su auditoría."},
    },
    {
        "id": "orozco", "nombre": "Consultorio Dr. Ricardo Orozco", "subtitulo": "Odontología · agendamiento digital en su sitio web",
        "direccion": "Megacentro Pinares, Torre 1, consultorio 904 · Pereira", "whatsapp": "311 841 7498 / 314 661 2227", "web": "odontologoricardoorozco.com",
        "enviado": "Martes 27 de octubre · por la noche (hora exacta por confirmar)", "respuesta": "Miércoles 28 de octubre · 9:02 a. m.", "espera": "al día siguiente",
        "hechos": ["Por la mañana respondió una asistente (\"Laura, asistente del Dr. Ricardo Orozco\").",
                   "Tiene dos números de contacto distintos (311 841 7498 y 314 661 2227).",
                   "Según su sitio web, ya ofrece agendamiento digital; por WhatsApp, en esta prueba, la cita no se pudo agendar."],
        "pts_whatsapp": 0, "nota_pts": "Respuesta al día siguiente",
        "acciones": ["Que el WhatsApp también agende: el mismo calendario del sitio, desde la conversación, a cualquier hora.",
                     "Responder fuera de horario sin depender de una persona (24/7).",
                     "Ordenar los dos números de contacto en un solo WhatsApp con respuestas coherentes."],
        "guia": {"apertura": "Ya entienden el valor de agendar en línea: el ángulo es que el WhatsApp (donde escribe el paciente) no agenda y la web sí.",
                 "preguntas": "¿Qué software o servicio usa su agendamiento web? ¿Cuántas citas llegan por la web y cuántas por WhatsApp?",
                 "ojo": "Confirmar la hora exacta del mensaje a ese número antes de citarla. Validar que el Instagram contactado (@Richo5555) sea suyo."},
    },
    {
        "id": "maxisonrisas", "nombre": "Maxisonrisas", "subtitulo": "Odontología · dos sedes en Dosquebradas",
        "direccion": "Calle 21 #17-78 (Av. La Pradera) · Calle 8 #19-80 (Av. Juan B. Gutiérrez) · Dosquebradas", "whatsapp": "320 792 4477", "web": "maxisonrisas.co",
        "enviado": "Martes 27 de octubre · 10:17 p. m.", "respuesta": "Miércoles 28 de octubre · 9:04 a. m.", "espera": "≈ 10,8 horas",
        "hechos": ["El mensaje de la noche no llegó a entregarse (un solo visto gris): el teléfono no lo recibió hasta la mañana.",
                   "Respondieron con una nota de voz de 1 minuto 41 segundos.",
                   "No se agendó cita en la conversación."],
        "pts_whatsapp": 0, "nota_pts": "Respuesta al día siguiente",
        "acciones": ["Un WhatsApp que reciba siempre, aunque el teléfono de la sede esté apagado o sin batería.",
                     "Responder en texto, con horarios de cada sede, y dejar la cita agendada en la sede que le quede mejor al paciente.",
                     "Anuncios \"clic a WhatsApp\" por sede (Pradera y Av. Juan B. Gutiérrez)."],
        "guia": {"apertura": "Dos sedes = el doble de mensajes por atender y un solo equipo. Una nota de voz de casi dos minutos es difícil de escuchar para un paciente nuevo.",
                 "preguntas": "¿Una sola persona atiende el WhatsApp de las dos sedes? ¿Cuál es la que más pacientes nuevos recibe?",
                 "ojo": "Buen candidato a plan Pro (multi-sede)."},
    },
    {
        "id": "delcastillo", "nombre": "Del Castillo Odontología Especializada", "subtitulo": "Implantes y ortodoncia",
        "direccion": "Calle 25 #8-30 · Pereira", "whatsapp": "314 814 2403", "web": "delcastilloodontologia.com",
        "enviado": "Martes 27 de octubre · 9:39 p. m.", "respuesta": "Miércoles 28 de octubre · 8:52 a. m.", "espera": "≈ 11,2 horas",
        "hechos": ["No hubo respuesta esa noche.", "Por la mañana explicaron el proceso de valoración de ortodoncia en 4 mensajes, escritos a mano.",
                   "No se agendó cita en la conversación."],
        "pts_whatsapp": 0, "nota_pts": "Respuesta al día siguiente",
        "acciones": ["Explicar el proceso de valoración al instante y a cualquier hora, y dejar la cita agendada.",
                     "Calificar al paciente (implante, ortodoncia, estética) para que el especialista reciba conversaciones listas.",
                     "Anuncios \"clic a WhatsApp\" para implantes y ortodoncia, tratamientos de alto valor."],
        "guia": {"apertura": "Tratamientos de ticket alto (implantes, ortodoncia): perder un paciente de noche cuesta mucho más que en una limpieza.",
                 "preguntas": "¿Qué porcentaje de las valoraciones termina en tratamiento? ¿De dónde vienen sus pacientes de implantes hoy?",
                 "ojo": "Sin dato de Google/Instagram todavía: completar antes de la visita."},
    },
    {
        "id": "ortocentro", "nombre": "Ortocentro", "subtitulo": "Ortodoncia y odontología · Pereira, Dosquebradas y La Virginia",
        "direccion": "Cra. 6 #22-48 (Pereira) · C.C. Plaza del Sol, local 207 (Dosquebradas)", "whatsapp": "320 688 9421 (asistente virtual \"Ana\")", "web": "ortocentro.com.co",
        "enviado": "Martes 27 de octubre · 10:00 p. m.", "respuesta": "Inmediata (segundos)", "espera": "segundos",
        "hechos": ["Ya tienen un asistente virtual que responde al instante: van por delante del resto.",
                   "Pero el asistente no puede ver la agenda (\"no tengo acceso a la agenda\", 4 veces) y pide datos personales sensibles, como la cédula.",
                   "Cuando la persona pidió cita para el día siguiente, la respuesta fue \"una asesora te contactará\": la cita no quedó agendada."],
        "pts_whatsapp": 30, "nota_pts": "Responde al instante, pero no agenda",
        "acciones": ["Conectar el asistente a la agenda real: que muestre horarios libres y deje la cita confirmada en la misma conversación.",
                     "Pedir solo lo necesario (nombre y teléfono) y no la cédula en el primer contacto.",
                     "Medir cuántas conversaciones del asistente terminan en cita y cuántas se pierden en \"una asesora te contactará\"."],
        "guia": {"apertura": "Ya pagan por IA: no se vende el concepto, se vende lo que le falta: ver la agenda y cerrar la cita. Reconocer que van por delante.",
                 "preguntas": "¿Qué plataforma usa \"Ana\"? ¿Cuántas conversaciones terminan en cita? ¿Cuánto pagan al mes?",
                 "ojo": "Multisede (Pereira / Dosquebradas / La Virginia): buen candidato a plan Integral. No criticar a su proveedor actual."},
    },
]

LECTURA = [(70, "Buena presencia: el siguiente paso es escalar."), (40, "Tiene base, pero deja pacientes sin atender."), (0, "Está perdiendo muchos pacientes por la forma en que atiende.")]


def puntaje_presencia(p: dict) -> dict:
    """Aplica la tabla de plantillas/auditoria-pacientes-perdidos.md a lo que se haya completado (None = sin dato)."""
    g, ig, ads, web = p.get("google"), p.get("instagram"), p.get("anuncios"), p.get("web")
    out = {}
    if g:
        e, r = g.get("estrellas"), g.get("resenas")
        if e is not None and r is not None:
            out["google"] = 25 if e >= 4.7 and r >= 100 else 15 if e >= 4.5 and r >= 50 else 5
    elif g == 0:
        out["google"] = 0
    if ig is not None and ig != "":
        out["instagram"] = 20 if ig >= 8 else 10 if ig >= 3 else 0
    if ads is not None:
        out["anuncios"] = 15 if ads else 0
    if web in ("completo", "parcial", "nada"):
        out["web"] = {"completo": 10, "parcial": 5, "nada": 0}[web]
    return out


ESTILO = """
@page { size: Letter; margin: 14mm 14mm 12mm; }
* { box-sizing: border-box; }
body { font-family: 'Inter', 'Segoe UI', Arial, sans-serif; color: #0f172a; font-size: 9.8pt; line-height: 1.38; margin: 0; }
.hoja { page-break-after: always; height: 247mm; position: relative; overflow: hidden; padding-bottom: 12mm; }
.hoja:last-child { page-break-after: auto; }
header { display: flex; align-items: center; justify-content: space-between; border-bottom: 2px solid #0d5c4e; padding-bottom: 8px; margin-bottom: 14px; }
.marca { display: flex; align-items: center; gap: 8px; font-weight: 800; letter-spacing: .08em; font-size: 11pt; }
.marca i { width: 22px; height: 22px; background: #0d5c4e; border-radius: 6px; display: inline-block; position: relative; }
.marca i::after { content: ""; position: absolute; left: 5px; top: 5px; border-left: 6px solid transparent; border-right: 6px solid transparent; border-bottom: 11px solid #fff; }
.fecha { color: #64748b; font-size: 9pt; text-align: right; }
h1 { font-size: 18pt; margin: 0 0 2px; letter-spacing: -.01em; }
.sub { color: #475569; margin: 0 0 2px; }
.dir { color: #64748b; font-size: 9pt; margin: 0 0 14px; }
h2 { font-size: 9.6pt; text-transform: uppercase; letter-spacing: .07em; color: #0d5c4e; margin: 13px 0 6px; }
.prueba { display: grid; grid-template-columns: 1fr 1fr 1fr; border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden; }
.prueba div { padding: 8px 10px; border-right: 1px solid #e2e8f0; }
.prueba div:last-child { border-right: 0; background: #eaf4f1; }
.prueba small { display: block; color: #64748b; font-size: 8pt; text-transform: uppercase; letter-spacing: .05em; margin-bottom: 3px; }
.prueba b { font-size: 10.5pt; }
.prueba .grande { font-size: 17pt; color: #0d5c4e; line-height: 1.1; }
ul { margin: 0; padding-left: 18px; } li { margin-bottom: 4px; }
.contexto { background: #f8fafc; border-left: 3px solid #0d5c4e; padding: 9px 12px; border-radius: 4px; }
table.pres { width: 100%; border-collapse: collapse; }
table.pres td { border: 1px solid #e2e8f0; padding: 5px 8px; vertical-align: top; }
table.pres td:first-child { width: 22%; font-weight: 600; background: #f8fafc; }
.linea { display: inline-block; border-bottom: 1px solid #94a3b8; min-width: 120px; height: 13px; }
.dato { font-weight: 600; }
.pend { color: #94a3b8; font-size: 8.5pt; }
.puntaje { display: flex; gap: 14px; align-items: center; margin-top: 12px; }
.puntaje .n { font-size: 20pt; font-weight: 800; color: #0d5c4e; }
.acc { counter-reset: a; list-style: none; padding: 0; }
.acc li { counter-increment: a; padding-left: 30px; position: relative; margin-bottom: 5px; }
.acc li::before { content: counter(a); position: absolute; left: 0; top: 0; width: 20px; height: 20px; border-radius: 50%; background: #0d5c4e; color: #fff; font-weight: 700; font-size: 9pt; text-align: center; line-height: 20px; }
footer { position: absolute; bottom: 0; left: 0; right: 0; border-top: 1px solid #e2e8f0; padding-top: 6px; font-size: 8pt; color: #64748b; display: flex; justify-content: space-between; }
.cuadro { border: 1px solid #e2e8f0; border-radius: 8px; padding: 7px 11px; margin-bottom: 6px; page-break-inside: avoid; }
.cuadro h3 { margin: 0 0 4px; font-size: 10.5pt; }
.chk { display: inline-block; width: 11px; height: 11px; border: 1.2px solid #64748b; border-radius: 2px; margin-right: 6px; vertical-align: -1px; }
.aviso { background: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px; padding: 9px 12px; }
"""


def esc(x) -> str:
    return html.escape(str(x))


def hoja(c: dict, presencia: dict) -> str:
    pts = puntaje_presencia(presencia)
    completo = {"google", "instagram", "anuncios", "web"} <= pts.keys()
    parcial = c["pts_whatsapp"] + sum(pts.values())

    def fila(nombre, valor, ayuda):
        celda = f'<span class="dato">{esc(valor)}</span>' if valor else f'<span class="linea"></span> <span class="pend">{esc(ayuda)}</span>'
        return f"<tr><td>{nombre}</td><td>{celda}</td></tr>"
    g = presencia.get("google") or {}
    google = f'{g["estrellas"]} estrellas · {g["resenas"]} reseñas' + (f' · {"responde" if g.get("responde") else "no responde"} reseñas' if "responde" in g else "") if g else ""
    ig = presencia.get("instagram")
    instagram = f"{ig} publicaciones en el último mes" if ig not in (None, "") else ""
    ads = presencia.get("anuncios")
    anuncios = "" if ads is None else ("Tiene anuncios activos" if ads else "Sin anuncios activos")
    web = {"completo": "Completo (servicios, precios y botón de WhatsApp)", "parcial": "Parcial", "nada": "Sin sitio o sin enlace a WhatsApp"}.get(presencia.get("web", ""), "")
    if completo:
        total = parcial
        lectura = next(t for m, t in LECTURA if total >= m)
        marcador = f'<div class="n">{total}/100</div><div><b>{esc(lectura)}</b><br><span class="pend">Respuesta WhatsApp {c["pts_whatsapp"]}/30 · Google {pts["google"]}/25 · Instagram {pts["instagram"]}/20 · Anuncios {pts["anuncios"]}/15 · Web {pts["web"]}/10</span></div>'
    else:
        marcador = (f'<div class="n">{parcial}</div><div><b>puntos de {30 + sum({"google": 25, "instagram": 20, "anuncios": 15, "web": 10}[k] for k in pts)} revisados hasta ahora</b><br>'
                    f'<span class="pend">WhatsApp: {c["pts_whatsapp"]}/30 ({esc(c["nota_pts"])}). El puntaje final sobre 100 se completa con la revisión de presencia digital de abajo.</span></div>')
    return f"""
<section class="hoja">
  <header><div class="marca"><i></i>VÉRTICE</div><div class="fecha">Auditoría de pacientes<br>{FECHA}</div></header>
  <h1>{esc(c['nombre'])}</h1>
  <p class="sub">{esc(c['subtitulo'])}</p>
  <p class="dir">{esc(c['direccion'])}</p>

  <h2>1 · Lo que probamos: escribirles como un paciente nuevo</h2>
  <div class="prueba">
    <div><small>Escribimos</small><b>{esc(c['enviado'])}</b><br><span class="pend">WhatsApp {esc(c['whatsapp'])}</span></div>
    <div><small>Respondieron</small><b>{esc(c['respuesta'])}</b></div>
    <div><small>Tiempo de espera</small><span class="grande">{esc(c['espera'])}</span></div>
  </div>
  <ul style="margin-top:10px">{''.join(f'<li>{esc(h)}</li>' for h in c['hechos'])}</ul>

  <h2>2 · Cómo se compara</h2>
  <div class="contexto">Esa misma noche escribimos a unas 20 clínicas de Pereira y Dosquebradas pidiendo cita. <b>Ninguna dejó una cita agendada esa noche</b> y la espera típica fue de
  unas 11 horas. Quien pide cita de noche suele escribir a varias clínicas a la vez: la primera que responde y le da la cita tiene ventaja.</div>

  <h2>3 · Presencia digital <span class="pend" style="text-transform:none;letter-spacing:0">(se completa con la clínica)</span></h2>
  <table class="pres">
    {fila('Ficha de Google', google, 'estrellas · reseñas · ¿responde reseñas?')}
    {fila('Instagram', instagram, 'publicaciones en el último mes · ¿enlace a WhatsApp?')}
    {fila('Anuncios (Meta)', anuncios, 'biblioteca de anuncios de Meta')}
    {fila('Sitio web', web or '', esc(c['web']) + ' · ¿botón de WhatsApp?')}
  </table>
  <div class="puntaje">{marcador}</div>

  <h2>4 · Tres acciones que recomendamos</h2>
  <ol class="acc">{''.join(f'<li>{esc(a)}</li>' for a in c['acciones'])}</ol>

  <footer><span>Vértice · Automatización con IA · Pereira, Colombia</span><span>Preparado por Juan José Serna · WhatsApp: ____________________</span></footer>
</section>"""


def guia() -> str:
    filas = "".join(f"""
<div class="cuadro"><h3>{esc(c['nombre'])} <span class="pend">· {esc(c['direccion'])}</span></h3>
<b>Cómo abrir:</b> {esc(c['guia']['apertura'])}<br><b>Preguntar:</b> {esc(c['guia']['preguntas'])}<br><b>Ojo:</b> {esc(c['guia']['ojo'])}</div>""" for c in CLINICAS)
    return f"""
<section class="hoja">
  <header><div class="marca"><i></i>VÉRTICE</div><div class="fecha">GUÍA INTERNA · no se entrega<br>{FECHA}</div></header>
  <h1>Guía de visitas · 5 clínicas prioritarias</h1>
  <p class="sub">Con 2 horas al día, tres jornadas cortas. Lo que ya tenemos son los datos reales de WhatsApp; lo demás se revisa antes de la visita.</p>

  <h2>Ruta sugerida</h2>
  <table class="pres">
    <tr><td>Jornada 1</td><td><b>Megacentro Pinares</b> (mismo edificio, Cra. 18 #12-75): PB Odontología (Torre 1, piso 12, cons. 1211) y Dr. Orozco (Torre 1, cons. 904).</td></tr>
    <tr><td>Jornada 2</td><td><b>Centro de Pereira:</b> Del Castillo (Calle 25 #8-30) y Ortocentro sede Pereira (Cra. 6 #22-48).</td></tr>
    <tr><td>Jornada 3</td><td><b>Dosquebradas:</b> Maxisonrisas (Av. La Pradera y Av. Juan B. Gutiérrez) y, si queda tiempo, Ortocentro Plaza del Sol (local 207).</td></tr>
  </table>

  <h2>Antes de cada visita (8 minutos por clínica)</h2>
  <p style="margin:0 0 6px">Lo hace el fundador desde el celular. Anotar en <code>prospectos/clinicas-dentales.csv</code> o pasárselo a Claude para regenerar las hojas con el puntaje.</p>
  <div class="cuadro"><span class="chk"></span><b>Google Maps (3 min):</b> estrellas, número de reseñas, ¿responden reseñas?, fotos, horario.<br>
  <span class="chk"></span><b>Instagram (2 min):</b> publicaciones en el último mes, fecha de la última, ¿enlace a WhatsApp en el perfil?<br>
  <span class="chk"></span><b>Anuncios (1 min):</b> facebook.com/ads/library → buscar el nombre de la clínica.<br>
  <span class="chk"></span><b>Sitio web (2 min):</b> ¿existe?, ¿botón de WhatsApp?, ¿servicios y precios claros?</div>

  <h2>Qué llevar</h2>
  <ul><li>La hoja impresa de esa clínica (<b>solo</b> la suya) y una tarjeta.</li>
  <li>El celular con la demo de Sofía abierta (<code>claude.ai/artifact/QNoA7pa8cbFn5WqLEwce34</code>, personalizada con el nombre de la clínica) y el panel (<code>claude.ai/artifact/WaS72eAXnZiXdQcAqS82sR</code>, ya en modo claro).</li></ul>

  <h2>Reglas</h2>
  <ul><li>Preguntar por el dueño o el administrador; si no está, dejar la hoja y escribir ese mismo día.</li>
  <li><b>Nunca</b> mostrar ni mencionar la auditoría de una clínica a otra, ni nombrar a otras clínicas.</li>
  <li>La prueba de WhatsApp fue una consulta normal de paciente. No se dejaron datos falsos ni citas pendientes: <b>pendiente cerrar con amabilidad los chats donde ofrecieron cita</b> (DentalEs, Oral Estética, Odontología AGB, entre otros) antes de visitarlos.</li>
  <li>No presentarlo como "los pillamos": es un estudio del sector; su clínica es una entre 20.</li>
  <li>No prometer nada que no esté aprobado. Pilotos: 2 clínicas sin costo de instalación a cambio de testimonio y caso de estudio.</li></ul>
  <footer><span>Guía interna · Vértice</span><span>Página 1 de 2</span></footer>
</section>

<section class="hoja">
  <header><div class="marca"><i></i>VÉRTICE</div><div class="fecha">GUÍA INTERNA · no se entrega<br>{FECHA}</div></header>
  <h1>Notas por clínica</h1>
  <p class="sub">Con lo que sabemos hoy. Verificar cada dato antes de citarlo.</p>
  {filas}
  <div class="aviso"><b>Preguntas que ayudan a cerrar y a diseñar la instalación</b> (<code>docs/14</code>): ¿Dónde llevan hoy las citas (cuaderno, Excel, software)? · ¿Quién contesta el WhatsApp y hasta qué hora? ·
  ¿Atienden por EPS, prepagadas o pólizas? · ¿Cuántos odontólogos y sillas? · ¿Cuántos mensajes de pacientes nuevos reciben por semana?</div>
  <footer><span>Guía interna · Vértice</span><span>Página 2 de 2</span></footer>
</section>"""


def pagina(cuerpo: str) -> str:
    return f'<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Vértice · auditoría</title><style>{ESTILO}</style></head><body>{cuerpo}</body></html>'


def main() -> None:
    ruta = CARPETA / "datos-presencia.json"
    presencia = json.loads(ruta.read_text(encoding="utf-8")) if ruta.exists() else {}
    docs = {"hojas-para-entregar": pagina("".join(hoja(c, presencia.get(c["id"], {})) for c in CLINICAS)),
            "guia-del-fundador": pagina(guia())}
    for nombre, contenido in docs.items():
        (CARPETA / f"{nombre}.html").write_text(contenido, encoding="utf-8")
    print("HTML generado. Para los PDF:  node prospectos/auditorias/a-pdf.js   (necesita Playwright con Chromium)")


if __name__ == "__main__":
    main()
