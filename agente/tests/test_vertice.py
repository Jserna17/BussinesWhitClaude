"""Pruebas sin conexión: la API de Claude y WhatsApp se simulan."""

import hashlib
import hmac
import json
from datetime import date, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from vertice.agente import RESPUESTA_FALLA, Asistente, prompt_sistema
from vertice.app import crear_app
from vertice.db import BaseDatos
from vertice.herramientas import DEFINICIONES, Herramientas
from vertice.negocio import cargar_negocios
from vertice.whatsapp import extraer_mensajes, firma_valida

NEGOCIOS = cargar_negocios(Path(__file__).resolve().parent.parent / "negocios")
CLINICA = NEGOCIOS["clinica-demo"]
# Fecha fija: lunes 9 de noviembre de 2026, 9:00 a. m.
AHORA = datetime(2026, 11, 9, 9, 0)


def ahora():
    return AHORA


@pytest.fixture
def db(tmp_path):
    base = BaseDatos(tmp_path / "prueba.db")
    base._ahora = lambda: AHORA.isoformat(timespec="seconds")  # mismo reloj que el resto de la prueba
    return base


# --- Bloques y respuestas simulados con la misma forma que el SDK --------
class Bloque(SimpleNamespace):
    def to_dict(self):
        return dict(vars(self))


def texto(t):
    return Bloque(type="text", text=t)


def herramienta(id_, nombre, entrada):
    return Bloque(type="tool_use", id=id_, name=nombre, input=entrada)


def respuesta(*bloques, parada="end_turn"):
    uso = SimpleNamespace(input_tokens=10, cache_read_input_tokens=0, output_tokens=5)
    return SimpleNamespace(content=list(bloques), stop_reason=parada, usage=uso)


class APIFalsa:
    """Devuelve respuestas guionadas y guarda cada petición."""

    def __init__(self, guion):
        self.guion = list(guion)
        self.peticiones = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._crear))

    def _crear(self, **kwargs):
        self.peticiones.append(json.loads(json.dumps(kwargs, default=str)))
        return self.guion.pop(0)


# --- Herramientas --------------------------------------------------------
def test_disponibilidad_respeta_horario_almuerzo_y_citas(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    datos = json.loads(h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-09", "servicio": "Limpieza dental (profilaxis)"})[0])
    # Abre a las 08:00 pero solo ofrece desde una hora después de "ahora" (09:00 -> 10:00).
    assert datos["horarios_libres"][0] == "10:00"
    # Almuerzo 12:00–14:00: una limpieza de 45 min no cabe a las 11:30 ni empieza a las 12:00/13:00.
    assert "11:30" not in datos["horarios_libres"] and "12:00" not in datos["horarios_libres"]
    assert "11:00" in datos["horarios_libres"] and "14:00" in datos["horarios_libres"]

    # Dos odontólogos el martes: la misma hora admite dos pacientes; el tercero ya no cabe.
    for tel, nombre in (("1", "Ana Gómez"), ("2", "Luis Pérez")):
        _, err = Herramientas(db, CLINICA, tel, ahora).ejecutar(
            "agendar_cita", {"nombre": nombre, "servicio": "limpieza", "fecha": "2026-11-10", "hora": "10:00"})
        assert not err
    datos = json.loads(h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-10", "servicio": "limpieza"})[0])
    assert "10:00" not in datos["horarios_libres"] and "10:30" not in datos["horarios_libres"]  # dura 45 min
    _, err = h.ejecutar("agendar_cita", {"nombre": "Eva Ruiz", "servicio": "limpieza", "fecha": "2026-11-10", "hora": "10:00"})
    assert err


def test_no_agenda_domingo_ni_hora_llena(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    domingo = json.loads(h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-15", "servicio": "Valoración odontológica"})[0])
    assert domingo["horarios_libres"] == []
    citas = [Herramientas(db, CLINICA, f"57300000{i}", ahora).ejecutar(
        "agendar_cita", {"nombre": f"Persona Prueba{i}", "servicio": "Valoración odontológica", "fecha": "2026-11-10", "hora": "08:00"})
        for i in range(3)]
    assert [err for _, err in citas] == [False, False, True]
    profes = {json.loads(c)["profesional"] for c, err in citas if not err}
    assert profes == {"Dra. Laura Gómez", "Dr. Andrés Ríos"}


def test_servicio_inexistente_y_fecha_pasada(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    salida, error = h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-10", "servicio": "Cirugía de rodilla"})
    assert error and "Servicios disponibles" in salida
    _, error = h.ejecutar("consultar_disponibilidad", {"fecha": "2026-10-01", "servicio": "limpieza"})
    assert error


def test_cancelar_solo_citas_propias(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    cita = json.loads(h.ejecutar("agendar_cita", {"nombre": "Ana Gómez", "servicio": "limpieza", "fecha": "2026-11-10", "hora": "09:00"})[0])
    _, error = Herramientas(db, CLINICA, "573000000001", ahora).ejecutar("cancelar_cita", {"cita_id": cita["cita_id"]})
    assert error
    _, error = h.ejecutar("cancelar_cita", {"cita_id": cita["cita_id"]})
    assert not error


def test_pasar_a_humano_notifica(db):
    avisos = []
    h = Herramientas(db, CLINICA, "573001112233", ahora, lambda n, t: avisos.append(t))
    h.ejecutar("pasar_a_humano", {"motivo": "Dolor fuerte en muela"})
    assert avisos and "Dolor fuerte" in avisos[0]


def test_definiciones_estrictas():
    for d in DEFINICIONES:
        assert d["strict"] is True
        assert d["input_schema"]["additionalProperties"] is False


# --- Ciclo del asistente --------------------------------------------------
def test_ciclo_con_herramienta_y_historial(db):
    api = APIFalsa([
        respuesta(herramienta("t1", "consultar_disponibilidad", {"fecha": "2026-11-10", "servicio": "limpieza"}), parada="tool_use"),
        respuesta(texto("Mañana tengo *8:00* o *8:30*. ¿Cuál prefieres?")),
        respuesta(texto("¡Listo!")),
    ])
    asistente = Asistente(db, api, ahora)
    r = asistente.responder(CLINICA, "573001112233", "Quiero una limpieza mañana")
    assert "8:00" in r

    primera, segunda = api.peticiones[0], api.peticiones[1]
    assert primera["model"] and primera["fallbacks"] == "default"
    assert primera["cache_control"] == {"type": "ephemeral"}
    assert "[Mensaje recibido el lunes 2026-11-09 a las 09:00]" in primera["messages"][0]["content"]
    resultado = segunda["messages"][-1]["content"][0]
    assert resultado["type"] == "tool_result" and resultado["tool_use_id"] == "t1"

    # El segundo mensaje continúa la misma conversación y el prefijo no cambia (caché).
    asistente.responder(CLINICA, "573001112233", "A las 8")
    tercera = api.peticiones[2]
    assert tercera["messages"][: len(segunda["messages"])] == segunda["messages"][:]
    assert tercera["system"] == primera["system"]


def test_rechazo_o_error_avisa_al_equipo(db):
    avisos = []
    api = APIFalsa([respuesta(parada="refusal")])
    asistente = Asistente(db, api, ahora, lambda n, t: avisos.append(t))
    assert asistente.responder(CLINICA, "573001112233", "hola") == RESPUESTA_FALLA
    assert avisos


def test_prompt_estable_y_limitado_al_negocio():
    p = prompt_sistema(CLINICA)
    assert p == prompt_sistema(CLINICA)  # determinista
    assert "Solo hablas de" in p and "Megacentro Pinares" in p and "Sábado" in p


# --- WhatsApp ---------------------------------------------------------------
def payload(phone_number_id="123", texto_msg="Hola", msg_id="wamid.1"):
    return {"entry": [{"changes": [{"value": {
        "metadata": {"phone_number_id": phone_number_id},
        "contacts": [{"wa_id": "573001112233", "profile": {"name": "Ana"}}],
        "messages": [{"id": msg_id, "from": "573001112233", "type": "text", "text": {"body": texto_msg}}],
    }}]}]}


def test_extraer_mensajes_y_firma():
    m = extraer_mensajes(payload())[0]
    assert (m.de, m.texto, m.nombre_perfil, m.phone_number_id) == ("573001112233", "Hola", "Ana", "123")
    cuerpo = b'{"a":1}'
    firma = "sha256=" + hmac.new(b"secreto", cuerpo, hashlib.sha256).hexdigest()
    assert firma_valida(cuerpo, firma, "secreto")
    assert not firma_valida(cuerpo, "sha256=000", "secreto")


def test_webhook_responde_una_sola_vez(db):
    from dataclasses import replace
    negocio = replace(CLINICA, whatsapp_phone_number_id="123")
    api = APIFalsa([respuesta(texto("¡Hola! Soy Sofía."))])
    enviados = []
    app = crear_app(Asistente(db, api, ahora), {negocio.id: negocio},
                    enviar=lambda pid, para, t: enviados.append((pid, para, t)))
    cliente = TestClient(app)
    assert cliente.post("/webhook", json=payload()).status_code == 200
    assert cliente.post("/webhook", json=payload()).status_code == 200  # reintento de Meta
    assert enviados == [("123", "573001112233", "¡Hola! Soy Sofía.")]
    assert cliente.post("/webhook", json=payload(phone_number_id="999", msg_id="wamid.2")).status_code == 200
    assert len(enviados) == 1  # número no configurado: se ignora


def test_respaldo_se_omite_en_haiku():
    from vertice.motores import respaldo
    assert respaldo("claude-opus-5-5")["fallbacks"] == "default"
    assert respaldo("claude-haiku-5-5") == {}


# --- Motor OpenAI -------------------------------------------------------------
class OpenAIFalsa:
    def __init__(self, guion):
        self.guion = list(guion)
        self.peticiones = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._crear))

    def _crear(self, **kwargs):
        self.peticiones.append(json.loads(json.dumps(kwargs, default=str)))
        return self.guion.pop(0)


def respuesta_openai(contenido=None, llamadas=()):
    tool_calls = [SimpleNamespace(id=i, function=SimpleNamespace(name=n, arguments=json.dumps(a)))
                  for i, n, a in llamadas] or None
    mensaje = SimpleNamespace(content=contenido, tool_calls=tool_calls, refusal=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=mensaje)],
                           usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5))


def test_motor_openai_agenda_con_herramientas(db):
    api = OpenAIFalsa([
        respuesta_openai(llamadas=[("c1", "agendar_cita", {"nombre": "Ana Gómez", "servicio": "limpieza",
                                                           "fecha": "2026-11-10", "hora": "09:00"})]),
        respuesta_openai("¡Listo, Ana! Tu limpieza quedó el martes a las *9:00*."),
    ])
    asistente = Asistente(db, api, ahora, proveedor="openai")
    r = asistente.responder(CLINICA, "573001112233", "Agéndame limpieza mañana 9 am, soy Ana Gómez")
    assert "9:00" in r
    assert db.citas_de_cliente(CLINICA.id, "573001112233")  # la cita quedó guardada

    primera, segunda = api.peticiones
    assert primera["messages"][0]["role"] == "system"
    assert primera["tools"][0]["function"]["strict"] is True
    assert segunda["messages"][-1]["role"] == "tool" and segunda["messages"][-1]["tool_call_id"] == "c1"
    # El historial de OpenAI se guarda aparte del de Claude.
    assert db.historial(f"{CLINICA.id}@openai", "573001112233")
    assert db.historial(CLINICA.id, "573001112233") == []


def test_servicio_con_valoracion_previa_no_se_agenda(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    salida, error = h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-10", "servicio": "Blanqueamiento dental"})
    assert error and "Valoración odontológica" in salida
    _, error = h.ejecutar("agendar_cita", {"nombre": "Ana", "servicio": "Blanqueamiento dental", "fecha": "2026-11-10", "hora": "09:00"})
    assert error


# --- Agenda: cruces, simultaneidad, bloqueos, especialidad --------------------
from vertice.agenda import Agenda, Conflicto  # noqa: E402


def test_pacientes_simultaneos_no_reciben_la_misma_silla(tmp_path):
    """20 pacientes intentan la misma hora a la vez (hilos y conexiones distintas): solo caben 2."""
    import threading
    ruta = tmp_path / "carrera.db"
    BaseDatos(ruta)
    resultados, barrera = [], threading.Barrier(20)

    def intentar(i):
        ag = Agenda(BaseDatos(ruta), CLINICA, ahora)  # conexión propia, como otro proceso
        barrera.wait()
        try:
            resultados.append(ag.reservar(f"cli{i}", f"P{i}", "Valoración odontológica", "2026-11-10", "09:00")["profesional"])
        except Conflicto:
            resultados.append(None)

    hilos = [threading.Thread(target=intentar, args=(i,)) for i in range(20)]
    [t.start() for t in hilos]
    [t.join() for t in hilos]
    ok = [r for r in resultados if r]
    assert sorted(ok) == ["Dr. Andrés Ríos", "Dra. Laura Gómez"]
    filas = BaseDatos(ruta).citas_entre(CLINICA.id, "2026-11-10", "2026-11-11")
    assert len(filas) == 2


def test_cita_larga_no_se_cruza_con_la_siguiente(db):
    ag = Agenda(db, CLINICA, ahora)
    # La Dra. Laura es la única que hace resinas (60 min): 09:00–10:00.
    c = ag.reservar("a", "Ana", "Resina estética", "2026-11-12", "09:00")
    assert c["profesional"] == "Dra. Laura Gómez"
    libres = ag.libres(date(2026, 11, 12), ag.servicio("Resina estética"))
    assert "08:30" not in libres and "09:00" not in libres and "09:30" not in libres and "10:00" in libres
    # Para valoración, el Dr. Andrés sigue libre a las 09:30.
    assert ag.libres(date(2026, 11, 12), ag.servicio("Valoración odontológica"))["09:30"] == ["Dr. Andrés Ríos"]


def test_bloqueos_general_y_por_profesional(db):
    ag = Agenda(db, CLINICA, ahora)
    db.crear_bloqueo(CLINICA.id, "", "2026-11-13T08:00:00", "2026-11-13T10:00:00", "Reunión")
    db.crear_bloqueo(CLINICA.id, "Dr. Andrés Ríos", "2026-11-13T14:00:00", "2026-11-13T18:00:00", "Congreso")
    libres = ag.libres(date(2026, 11, 13), ag.servicio("Valoración odontológica"))
    assert "08:00" not in libres and "09:30" not in libres and "10:00" in libres
    assert libres["15:00"] == ["Dra. Laura Gómez"]
    try:
        ag.reservar("x", "X", "Valoración odontológica", "2026-11-13", "15:00", profesional="Dr. Andrés Ríos")
        assert False, "debió fallar"
    except Conflicto:
        pass


def test_cancelar_libera_el_horario(db):
    ag = Agenda(db, CLINICA, ahora)
    a = ag.reservar("a", "A", "Resina estética", "2026-11-12", "08:00")
    assert "08:00" not in ag.libres(date(2026, 11, 12), ag.servicio("Resina estética"))
    db.cancelar_cita(CLINICA.id, "a", a["cita_id"])
    assert "08:00" in ag.libres(date(2026, 11, 12), ag.servicio("Resina estética"))


# --- Lectura de conversaciones y panel --------------------------------------
from vertice import transcripcion  # noqa: E402


def test_transcripcion_claude_y_openai():
    claude = [
        {"role": "user", "content": "[Mensaje recibido el lunes 2026-11-09 a las 21:40] (Nombre en WhatsApp: Ana) Hola"},
        {"role": "assistant", "content": [{"type": "thinking", "thinking": "", "signature": "x"},
                                          {"type": "text", "text": "¡Hola Ana!"},
                                          {"type": "tool_use", "id": "t", "name": "agendar_cita",
                                           "input": {"servicio": "Limpieza", "fecha": "2026-11-10", "hora": "08:00", "nombre": "Ana"}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t", "content": "{}"}]},
    ]
    r = transcripcion.leer(claude)
    assert r["nombre_perfil"] == "Ana"
    assert [m["rol"] for m in r["mensajes"]] == ["paciente", "asistente", "evento"]
    assert r["mensajes"][0] == {"rol": "paciente", "texto": "Hola", "fecha": "2026-11-09", "hora": "21:40"}
    openai = [
        {"role": "user", "content": "[Mensaje recibido el lunes 2026-11-09 a las 08:00] Quiero cita"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "c", "type": "function", "function": {"name": "pasar_a_humano", "arguments": "{\"motivo\": \"dolor\"}"}}]},
        {"role": "tool", "tool_call_id": "c", "content": "{}"},
        {"role": "assistant", "content": "Ya avisé al equipo."},
    ]
    r = transcripcion.leer(openai)
    assert [m["texto"] for m in r["mensajes"]] == ["Quiero cita", "Pasó el caso al equipo: dolor", "Ya avisé al equipo."]


def test_panel_protegido_y_funcional(db):
    from dataclasses import replace
    asistente = Asistente(db, APIFalsa([]), ahora)
    app = crear_app(asistente, {CLINICA.id: CLINICA}, enviar=lambda *a: None)
    c = TestClient(app)
    assert c.get("/panel").status_code == 200
    assert c.get("/panel/api/resumen").status_code == 401
    assert c.get("/panel/api/resumen", headers={"X-Negocio": CLINICA.id, "X-Clave": "mala"}).status_code == 401
    H = {"X-Negocio": CLINICA.id, "X-Clave": "demo123"}

    # Una conversación real guardada y una cita del asistente
    db.guardar_historial(CLINICA.id, "573001112233", [
        {"role": "user", "content": "[Mensaje recibido el domingo 2026-11-08 a las 22:15] Hola, ¿precio limpieza?"},
        {"role": "assistant", "content": [{"type": "text", "text": "$120.000"}]}], AHORA)
    Agenda(db, CLINICA, ahora).reservar("573001112233", "Ana", "Limpieza dental (profilaxis)", "2026-11-09", "10:00")

    r = c.get("/panel/api/resumen", headers=H).json()
    assert r["mensajes_pacientes"] == 1 and r["fuera_de_horario"] == 1 and r["citas_agendadas_asistente"] == 1
    assert r["citas_hoy"] == 1

    # Recepción agenda por el panel; la misma silla no se puede repetir
    cita = {"nombre": "Luis", "servicio": "Resina estética", "fecha": "2026-11-10", "hora": "08:00"}
    assert c.post("/panel/api/citas", headers=H, json=cita).status_code == 200
    assert c.post("/panel/api/citas", headers=H, json={**cita, "nombre": "Eva"}).status_code == 409
    libres = c.get("/panel/api/disponibilidad", headers=H, params={"fecha": "2026-11-10", "servicio": "Resina estética"}).json()
    assert "08:00" not in libres["libres"]

    # Bloqueo y estados
    assert c.post("/panel/api/bloqueos", headers=H, json={"fecha": "2026-11-10", "desde": "14:00", "hasta": "18:00", "motivo": "Congreso"}).status_code == 200
    ag = c.get("/panel/api/agenda", headers=H, params={"desde": "2026-11-09"}).json()
    assert len(ag["citas"]) == 2 and len(ag["bloqueos"]) == 1
    cid = ag["citas"][0]["id"]
    assert c.post(f"/panel/api/citas/{cid}/estado", headers=H, json={"estado": "asistio"}).status_code == 200

    convs = c.get("/panel/api/conversaciones", headers=H).json()
    assert convs[0]["nombre"] == "Ana" and convs[0]["tiene_cita"] is False  # ya asistió
    hilo = c.get("/panel/api/conversaciones/573001112233", headers=H).json()
    assert [m["texto"] for m in hilo["mensajes"]] == ["Hola, ¿precio limpieza?", "$120.000"]


def test_no_agenda_sin_nombre_real(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    for nombre in ("Cliente", "Ana", "", "Paciente nuevo"):
        salida, err = h.ejecutar("agendar_cita", {"nombre": nombre, "servicio": "limpieza", "fecha": "2026-11-10", "hora": "09:00"})
        assert err and "nombre y apellido" in salida
    assert not db.citas_entre(CLINICA.id, "2026-11-10", "2026-11-11")


def test_transcripcion_marca_intentos_rechazados():
    msgs = [
        {"role": "user", "content": "[Mensaje recibido el lunes 2026-11-09 a las 08:00] Cita mañana"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "agendar_cita", "arguments": "{\"nombre\": \"Cliente\", \"servicio\": \"Limpieza\", \"fecha\": \"2026-11-10\", \"hora\": \"08:00\"}"}}]},
        {"role": "tool", "tool_call_id": "c1", "content": "ERROR: Antes de agendar pide al cliente su nombre y apellido. Todavía no se agendó nada."},
    ]
    ev = transcripcion.leer(msgs)["mensajes"][-1]
    assert ev["rol"] == "evento" and ev["texto"].startswith("Intentó agendar y el sistema no lo permitió") and "Agendó" not in ev["texto"]


def test_lecturas_y_escrituras_en_paralelo_no_fallan(tmp_path):
    # El panel pide resumen, agenda y casos a la vez; FastAPI los atiende en hilos distintos con la misma conexión.
    import threading
    base = BaseDatos(tmp_path / "p.db")
    errores = []

    def trabajo(i):
        try:
            for j in range(40):
                base.registrar_escalacion("n", f"c{i}", f"motivo {j}")
                base.filas("escalaciones", "n")
                base.citas_entre("n", "0000", "9999")
        except Exception as e:  # noqa: BLE001
            errores.append(repr(e))

    hilos = [threading.Thread(target=trabajo, args=(i,)) for i in range(8)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert errores == []
    assert len(base.filas("escalaciones", "n")) == 8 * 40


from vertice.festivos import festivos  # noqa: E402


def test_festivos_de_colombia_2026():
    # Calendario oficial 2026: 18 festivos, con la Ley Emiliani (se corren al lunes).
    assert [d.isoformat()[5:] for d in festivos(2026)] == [
        "01-01", "01-12", "03-23", "04-02", "04-03", "05-01", "05-18", "06-08", "06-15",
        "06-29", "07-20", "08-07", "08-17", "10-12", "11-02", "11-16", "12-08", "12-25"]


def test_no_agenda_en_festivo(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    datos = json.loads(h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-16", "servicio": "Valoración odontológica"})[0])
    assert datos["horarios_libres"] == [] and "Independencia de Cartagena" in datos["nota"]
    _, err = h.ejecutar("agendar_cita", {"nombre": "Ana Gómez", "servicio": "Valoración odontológica", "fecha": "2026-11-16", "hora": "09:00"})
    assert err


def test_horario_propio_de_cada_profesional(db):
    ag = Agenda(db, CLINICA, ahora)
    valoracion = ag.servicio("Valoración odontológica")
    # Miércoles: el Dr. Andrés no atiende, solo la Dra. Laura.
    assert {p for ps in ag.libres(date(2026, 11, 11), valoracion).values() for p in ps} == {"Dra. Laura Gómez"}
    # Viernes en la mañana solo la Dra. Laura; en la tarde los dos.
    viernes = ag.libres(date(2026, 11, 13), valoracion)
    assert viernes["09:00"] == ["Dra. Laura Gómez"]
    assert viernes["15:00"] == ["Dra. Laura Gómez", "Dr. Andrés Ríos"]
    with pytest.raises(Conflicto):
        ag.reservar("x", "Ana Gómez", "Valoración odontológica", "2026-11-11", "09:00", profesional="Dr. Andrés Ríos")


def test_prompt_muestra_horario_partido_y_profesionales():
    texto = prompt_sistema(CLINICA)
    assert "- Lunes: 08:00 a 12:00 y 14:00 a 18:00" in texto
    assert "Festivos de Colombia: cerrado" in texto
    assert "Dr. Andrés Ríos: martes" in texto


def test_vacaciones_de_varios_dias_y_citas_afectadas(db):
    c = TestClient(crear_app(Asistente(db, APIFalsa([]), ahora), {CLINICA.id: CLINICA}, enviar=lambda *a: None))
    H = {"X-Negocio": CLINICA.id, "X-Clave": "demo123"}
    Agenda(db, CLINICA, ahora).reservar("573001112233", "Ana Gómez", "Valoración odontológica", "2026-11-12", "09:00",
                                        profesional="Dr. Andrés Ríos")
    r = c.post("/panel/api/bloqueos", headers=H, json={"fecha": "2026-11-10", "fecha_fin": "2026-11-13", "desde": "00:00",
                                                       "hasta": "23:59", "profesional": "Dr. Andrés Ríos", "motivo": "Vacaciones"}).json()
    assert [x["nombre"] for x in r["citas_afectadas"]] == ["Ana Gómez"]
    ag = Agenda(db, CLINICA, ahora)
    for dia in (10, 12, 13):  # sus días de trabajo dentro de las vacaciones: nadie lo puede agendar
        assert all("Dr. Andrés Ríos" not in ps for ps in ag.libres(date(2026, 11, dia), ag.servicio("Valoración odontológica")).values())
    sesion = c.get("/panel/api/sesion", headers=H).json()
    assert sesion["festivos"]["2026-11-16"] == "Independencia de Cartagena"
    assert sesion["horario_profesionales"]["Dr. Andrés Ríos"]["lunes"] == []
