"""Pruebas sin conexión: la API de Claude y WhatsApp se simulan."""

import hashlib
import hmac
import json
import shutil
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
from dataclasses import replace as _reemplazar  # noqa: E402

# El aviso de privacidad del primer mensaje tiene sus propias pruebas; en las demás se desactiva para no mezclar.
CLINICA = _reemplazar(NEGOCIOS["clinica-demo"], aviso_privacidad=False)
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
from vertice.agenda import Agenda, CitaNoEncontrada, Conflicto  # noqa: E402


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


def eco(para="573001112233", texto_="Hola, soy Marta de la clínica", msg_id="wamid.eco1", phone_number_id="123"):
    return {"entry": [{"changes": [{"field": "smb_message_echoes", "value": {
        "metadata": {"phone_number_id": phone_number_id},
        "message_echoes": [{"id": msg_id, "to": para, "type": "text", "text": {"body": texto_}}]}}]}]}


def test_el_equipo_escribe_y_el_asistente_se_calla(db):
    from dataclasses import replace
    negocio = replace(CLINICA, whatsapp_phone_number_id="123")
    api = APIFalsa([respuesta(texto("Claro, te ayudo.")), respuesta(texto("Listo, sigo yo."))])
    enviados = []
    app = crear_app(Asistente(db, api, ahora), {negocio.id: negocio},
                    enviar=lambda pid, para, t: enviados.append(t) or f"wamid.sofia{len(enviados)}")
    c = TestClient(app)
    c.post("/webhook", json=eco())                      # la recepcionista escribe desde su celular
    assert db.pausa_vigente(negocio.id, "573001112233")
    c.post("/webhook", json=eco())                      # el mismo aviso repetido no cambia nada
    assert len(db.mensajes_chat(negocio.id, "573001112233")) == 1
    c.post("/webhook", json=payload(msg_id="wamid.p1"))  # el paciente responde: Sofía NO contesta
    assert enviados == [] and api.peticiones == []
    chat = [(m["rol"], m["texto"]) for m in db.mensajes_chat(negocio.id, "573001112233")]
    assert chat[0] == ("equipo", "Hola, soy Marta de la clínica") and chat[1][0] == "paciente"
    # Se devuelve el chat a Sofía: responde y sabe lo que habló el equipo.
    db.reanudar(negocio.id, "573001112233")
    c.post("/webhook", json=payload(msg_id="wamid.p2"))
    assert enviados == ["Claro, te ayudo."]
    pedido = json.dumps(api.peticiones[0]["messages"], ensure_ascii=False)
    assert "Una persona del equipo escribió" in pedido and "Hola, soy Marta" in pedido


def test_pausa_vence_sola(db):
    from datetime import timedelta
    db.pausar(CLINICA.id, "573001112233", 12, "prueba")
    assert db.pausa_vigente(CLINICA.id, "573001112233")
    futuro = (datetime.fromisoformat(db._ahora()) + timedelta(hours=13)).isoformat(timespec="seconds")
    db._ahora = lambda: futuro
    assert db.pausa_vigente(CLINICA.id, "573001112233") is None


def test_panel_tomar_control_responder_y_devolver(db):
    from dataclasses import replace
    negocio = replace(CLINICA, whatsapp_phone_number_id="123")
    enviados = []
    c = TestClient(crear_app(Asistente(db, APIFalsa([]), ahora), {negocio.id: negocio},
                             enviar=lambda pid, para, t: enviados.append((para, t)) or "wamid.x"))
    H = {"X-Negocio": negocio.id, "X-Clave": "demo123"}
    cli = "573001112233"
    # Sin mensaje reciente del paciente no se puede escribir (ventana de 24 h de WhatsApp)
    assert c.post(f"/panel/api/conversaciones/{cli}/enviar", headers=H, json={"texto": "Hola"}).status_code == 409
    db.guardar_mensaje_chat(negocio.id, cli, "paciente", "¿Tienen cita hoy?", "whatsapp")
    assert c.post(f"/panel/api/conversaciones/{cli}/enviar", headers=H, json={"texto": "  "}).status_code == 400
    r = c.post(f"/panel/api/conversaciones/{cli}/enviar", headers=H, json={"texto": "Sí, a las 3 p. m."}).json()
    assert r["enviado"] is True and enviados == [(cli, "Sí, a las 3 p. m.")]
    lista = c.get("/panel/api/conversaciones", headers=H).json()
    assert lista[0]["pausada"] is True and lista[0]["sin_responder"] is False
    hilo = c.get(f"/panel/api/conversaciones/{cli}", headers=H).json()
    assert [m["rol"] for m in hilo["mensajes"]] == ["paciente", "equipo"] and hilo["pausada"]
    # El paciente escribe mientras la atiende una persona: queda "sin responder"
    db.guardar_mensaje_chat(negocio.id, cli, "paciente", "Perfecto, gracias", "whatsapp")
    assert c.get("/panel/api/conversaciones", headers=H).json()[0]["sin_responder"] is True
    assert c.post(f"/panel/api/conversaciones/{cli}/devolver", headers=H).status_code == 200
    assert c.get("/panel/api/conversaciones", headers=H).json()[0]["pausada"] is False


def payload_audio(msg_id="wamid.a1", media="media123"):
    return {"entry": [{"changes": [{"value": {
        "metadata": {"phone_number_id": "123"},
        "contacts": [{"wa_id": "573001112233", "profile": {"name": "Ana"}}],
        "messages": [{"id": msg_id, "from": "573001112233", "type": "audio",
                      "audio": {"id": media, "mime_type": "audio/ogg; codecs=opus", "voice": True}}],
    }}]}]}


def test_nota_de_voz_se_transcribe_y_llega_al_asistente(db):
    from dataclasses import replace
    negocio = replace(CLINICA, whatsapp_phone_number_id="123")
    m = extraer_mensajes(payload_audio())[0]
    assert (m.tipo, m.texto, m.media_id) == ("audio", None, "media123")
    api = APIFalsa([respuesta(texto("Claro, ¿para qué día?"))])
    enviados = []
    c = TestClient(crear_app(Asistente(db, api, ahora), {negocio.id: negocio},
                             enviar=lambda pid, para, t: enviados.append(t) or "wamid.s",
                             descargar=lambda mid: (b"OggS...", "audio/ogg"),
                             transcribir=lambda audio, mime: "quiero una limpieza para mañana"))
    c.post("/webhook", json=payload_audio())
    assert enviados == ["Claro, ¿para qué día?"]
    pedido = json.dumps(api.peticiones[0]["messages"], ensure_ascii=False)
    assert "🎤 quiero una limpieza para mañana" in pedido


def test_nota_de_voz_que_falla_pide_escribir(db):
    from dataclasses import replace
    negocio = replace(CLINICA, whatsapp_phone_number_id="123")
    enviados = []

    def roto(audio, mime):
        raise RuntimeError("sin red")

    c = TestClient(crear_app(Asistente(db, APIFalsa([]), ahora), {negocio.id: negocio},
                             enviar=lambda pid, para, t: enviados.append(t),
                             descargar=lambda mid: (b"x", "audio/ogg"), transcribir=roto))
    c.post("/webhook", json=payload_audio())
    assert len(enviados) == 1 and "escribir" in enviados[0]


def test_nota_de_voz_en_chat_pausado_se_guarda_transcrita(db):
    from dataclasses import replace
    negocio = replace(CLINICA, whatsapp_phone_number_id="123")
    db.pausar(negocio.id, "573001112233", 12, "prueba")
    enviados = []
    c = TestClient(crear_app(Asistente(db, APIFalsa([]), ahora), {negocio.id: negocio},
                             enviar=lambda pid, para, t: enviados.append(t),
                             descargar=lambda mid: (b"x", "audio/ogg"), transcribir=lambda a, m: "¿atienden el sábado?"))
    c.post("/webhook", json=payload_audio())
    assert enviados == []
    assert db.mensajes_chat(negocio.id, "573001112233")[0]["texto"] == "🎤 ¿atienden el sábado?"


def test_transcribir_rechaza_audios_enormes_y_vacios():
    from vertice import voz
    with pytest.raises(voz.ErrorVoz):
        voz.transcribir(b"0" * (voz.MAX_BYTES + 1))
    falso = SimpleNamespace(audio=SimpleNamespace(transcriptions=SimpleNamespace(create=lambda **k: SimpleNamespace(text="  "))))
    with pytest.raises(voz.ErrorVoz):
        voz.transcribir(b"abc", cliente=falso)


def test_reprogramar_mueve_la_cita_y_libera_el_horario_viejo(db):
    ag = Agenda(db, CLINICA, ahora)
    cita = ag.reservar("573001112233", "Ana Gómez", "Resina estética", "2026-11-10", "09:00")
    nueva = ag.reprogramar(cita["cita_id"], "2026-11-12", "10:00", cliente="573001112233")
    assert nueva["cita_id"] == cita["cita_id"] and nueva["antes"] == "2026-11-10T09:00:00"
    assert nueva["profesional"] == cita["profesional"]  # misma doctora
    assert "09:00" in ag.libres(date(2026, 11, 10), ag.servicio("Resina estética"))
    assert "10:00" not in ag.libres(date(2026, 11, 12), ag.servicio("Resina estética"))
    assert len(db.citas_entre(CLINICA.id, "2026-11-01", "2026-12-01")) == 1  # no se duplicó


def test_reprogramar_a_un_horario_que_se_cruza_con_la_propia_cita(db):
    ag = Agenda(db, CLINICA, ahora)
    cita = ag.reservar("573001112233", "Ana Gómez", "Resina estética", "2026-11-10", "09:00")  # 09:00–10:00
    mover = ag.reprogramar(cita["cita_id"], "2026-11-10", "09:30", cliente="573001112233")    # 09:30–10:30
    assert mover["hora"] == "09:30"


def test_reprogramar_horario_ocupado_deja_la_cita_donde_estaba(db):
    ag = Agenda(db, CLINICA, ahora)
    ag.reservar("1", "Luis Pérez", "Resina estética", "2026-11-12", "10:00")
    cita = ag.reservar("573001112233", "Ana Gómez", "Resina estética", "2026-11-10", "09:00")
    with pytest.raises(Conflicto):
        ag.reprogramar(cita["cita_id"], "2026-11-12", "10:00", cliente="573001112233")
    assert db.cita(CLINICA.id, cita["cita_id"])["inicio"] == "2026-11-10T09:00:00"


def test_no_se_reprograma_la_cita_de_otro_paciente_ni_una_cancelada(db):
    ag = Agenda(db, CLINICA, ahora)
    cita = ag.reservar("573001112233", "Ana Gómez", "Resina estética", "2026-11-10", "09:00")
    with pytest.raises(CitaNoEncontrada):
        ag.reprogramar(cita["cita_id"], "2026-11-10", "11:00", cliente="999")
    db.cancelar_cita(CLINICA.id, "573001112233", cita["cita_id"])
    with pytest.raises(CitaNoEncontrada):
        ag.reprogramar(cita["cita_id"], "2026-11-10", "11:00")


def test_herramienta_reprogramar_y_panel(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    cita = json.loads(h.ejecutar("agendar_cita", {"nombre": "Ana Gómez", "servicio": "limpieza", "fecha": "2026-11-10", "hora": "10:00"})[0])
    salida, err = h.ejecutar("reprogramar_cita", {"cita_id": cita["cita_id"], "fecha": "2026-11-10", "hora": "15:00"})
    assert not err and json.loads(salida)["hora"] == "15:00"
    _, err = Herramientas(db, CLINICA, "otro", ahora).ejecutar("reprogramar_cita", {"cita_id": cita["cita_id"], "fecha": "2026-11-10", "hora": "16:00"})
    assert err
    c = TestClient(crear_app(Asistente(db, APIFalsa([]), ahora), {CLINICA.id: CLINICA}, enviar=lambda *a: None))
    H = {"X-Negocio": CLINICA.id, "X-Clave": "demo123"}
    r = c.post(f"/panel/api/citas/{cita['cita_id']}/reprogramar", headers=H, json={"fecha": "2026-11-11", "hora": "08:00"})
    assert r.status_code == 200 and r.json()["fecha"] == "2026-11-11"
    # La hora propia cuenta como libre al elegir nueva hora para la misma cita
    libres = c.get("/panel/api/disponibilidad", headers=H, params={"fecha": "2026-11-11", "servicio": "limpieza", "excluir": cita["cita_id"]}).json()["libres"]
    assert "08:00" in libres
    assert c.post("/panel/api/citas/9999/reprogramar", headers=H, json={"fecha": "2026-11-11", "hora": "08:00"}).status_code == 404


# --- Recordatorios --------------------------------------------------------
from vertice import recordatorios  # noqa: E402


def test_cuando_en_espanol():
    base = datetime(2026, 11, 9, 9, 0)
    assert recordatorios.cuando(datetime(2026, 11, 9, 14, 0), base) == "hoy a las 2:00 p. m."
    assert recordatorios.cuando(datetime(2026, 11, 10, 8, 30), base) == "mañana a las 8:30 a. m."
    assert recordatorios.cuando(datetime(2026, 11, 12, 12, 0), base) == "el jueves 12 de noviembre a las 12:00 p. m."


def _clinica_con_whatsapp():
    from dataclasses import replace
    return replace(CLINICA, whatsapp_phone_number_id="123")


def test_recordatorio_se_envia_una_vez_con_botones(db):
    n = _clinica_con_whatsapp()
    cita = Agenda(db, n, ahora).reservar("573001112233", "Ana Gómez", "Valoración odontológica", "2026-11-10", "15:00")
    enviados = []

    def plantilla(pid, para, nombre, parametros, botones):
        enviados.append((pid, para, nombre, parametros, botones))
        return f"wamid.r{len(enviados)}"

    manana_temprano = datetime(2026, 11, 9, 7, 30)   # de madrugada: no se molesta
    assert recordatorios.ciclo(db, {n.id: n}, plantilla, manana_temprano) == {"enviados": 0, "fallidos": 0}
    dia = datetime(2026, 11, 9, 15, 30)               # ya falta menos de 24 h: toca el aviso del día anterior
    assert recordatorios.ciclo(db, {n.id: n}, plantilla, dia)["enviados"] == 1
    assert recordatorios.ciclo(db, {n.id: n}, plantilla, dia)["enviados"] == 0  # no se repite
    pid, para, nombre, parametros, botones = enviados[0]
    assert (pid, para, nombre) == ("123", "573001112233", "recordatorio_cita")
    assert parametros == ["Ana", n.nombre, "Valoración odontológica", "mañana a las 3:00 p. m."]
    assert botones == [f"confirmar:{cita['cita_id']}", f"cambiar:{cita['cita_id']}"]
    # El aviso corto de 2 h antes también sale, una sola vez
    corto = datetime(2026, 11, 10, 13, 30)
    assert recordatorios.ciclo(db, {n.id: n}, plantilla, corto)["enviados"] == 1
    assert recordatorios.ciclo(db, {n.id: n}, plantilla, corto)["enviados"] == 0
    assert enviados[1][3][3] == "hoy a las 3:00 p. m."


def test_recordatorio_que_falla_se_reintenta_y_casos_que_se_omiten(db):
    n = _clinica_con_whatsapp()
    ag = Agenda(db, n, ahora)
    ag.reservar("573001112233", "Ana Gómez", "Valoración odontológica", "2026-11-10", "15:00")
    ag.reservar("panel-20261109", "Sin Teléfono", "Valoración odontológica", "2026-11-10", "16:00")  # recepción sin número
    llamadas = []

    def meta_caida(*a):
        llamadas.append(a)
        raise RuntimeError("131047 plantilla no aprobada")

    dia = datetime(2026, 11, 9, 15, 30)
    assert recordatorios.ciclo(db, {n.id: n}, meta_caida, dia) == {"enviados": 0, "fallidos": 1}
    assert len(llamadas) == 1                                   # la de sin teléfono ni se intentó
    assert recordatorios.ciclo(db, {n.id: n}, lambda *a: "ok", dia)["enviados"] == 1  # reintento exitoso
    # Clínica sin número de WhatsApp conectado o con recordatorios apagados: nada se envía
    assert recordatorios.ciclo(db, {CLINICA.id: CLINICA}, lambda *a: "x", dia)["enviados"] == 0


def test_cita_recien_agendada_no_recibe_aviso_pegado(db):
    n = _clinica_con_whatsapp()
    Agenda(db, n, ahora).reservar("573001112233", "Ana Gómez", "Valoración odontológica", "2026-11-09", "14:00")  # hoy mismo
    enviados = []
    r = recordatorios.ciclo(db, {n.id: n}, lambda *a: enviados.append(a) or "w", datetime(2026, 11, 9, 12, 5))
    assert r["enviados"] == 0 and enviados == []   # se agendó 5 h antes: ya está fresca


def payload_boton(boton_payload, texto_="Sí, confirmo", msg_id="wamid.b1"):
    return {"entry": [{"changes": [{"value": {
        "metadata": {"phone_number_id": "123"},
        "contacts": [{"wa_id": "573001112233", "profile": {"name": "Ana"}}],
        "messages": [{"id": msg_id, "from": "573001112233", "type": "button",
                      "button": {"payload": boton_payload, "text": texto_}}],
    }}]}]}


def test_boton_confirmo_y_boton_cambiar(db):
    n = _clinica_con_whatsapp()
    cita = Agenda(db, n, ahora).reservar("573001112233", "Ana Gómez", "Valoración odontológica", "2026-11-10", "15:00")
    api = APIFalsa([respuesta(texto("Claro, ¿qué día te queda mejor?"))])
    enviados = []
    c = TestClient(crear_app(Asistente(db, api, ahora), {n.id: n}, enviar=lambda pid, para, t: enviados.append(t) or "w",
                             recordatorios_activos=False))
    c.post("/webhook", json=payload_boton(f"confirmar:{cita['cita_id']}"))
    assert db.cita(n.id, cita["cita_id"])["confirmacion"] == "confirmo"
    assert len(enviados) == 1 and "confirmada tu asistencia" in enviados[0] and api.peticiones == []
    # "Necesito cambiarla": lo atiende Sofía con las herramientas, sin gastar una respuesta fija
    c.post("/webhook", json=payload_boton(f"cambiar:{cita['cita_id']}", "Necesito cambiarla", "wamid.b2"))
    assert db.cita(n.id, cita["cita_id"])["confirmacion"] == "cambiar"
    assert "Necesito cambiar mi cita de Valoración odontológica (mañana a las 3:00 p. m.)" in json.dumps(api.peticiones[0]["messages"], ensure_ascii=False)
    assert enviados[-1] == "Claro, ¿qué día te queda mejor?"
    # Un botón de una cita ajena o cancelada no marca nada
    assert db.marcar_confirmacion(n.id, cita["cita_id"], "otro", "confirmo") is False


def test_reprogramar_reinicia_confirmacion_y_recordatorios(db):
    n = _clinica_con_whatsapp()
    ag = Agenda(db, n, ahora)
    cita = ag.reservar("573001112233", "Ana Gómez", "Valoración odontológica", "2026-11-10", "15:00")
    assert recordatorios.ciclo(db, {n.id: n}, lambda *a: "w", datetime(2026, 11, 9, 15, 30))["enviados"] == 1
    db.marcar_confirmacion(n.id, cita["cita_id"], "573001112233", "confirmo")
    ag.reprogramar(cita["cita_id"], "2026-11-12", "10:00")
    fila = db.cita(n.id, cita["cita_id"])
    assert (fila["recordatorio_1"], fila["confirmacion"]) == ("", "")


def test_herramienta_confirmar_asistencia(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    cita = json.loads(h.ejecutar("agendar_cita", {"nombre": "Ana Gómez", "servicio": "limpieza", "fecha": "2026-11-10", "hora": "10:00"})[0])
    assert not h.ejecutar("confirmar_asistencia", {"cita_id": cita["cita_id"]})[1]
    assert db.cita(CLINICA.id, cita["cita_id"])["confirmacion"] == "confirmo"
    assert Herramientas(db, CLINICA, "otro", ahora).ejecutar("confirmar_asistencia", {"cita_id": cita["cita_id"]})[1]


def test_el_ciclo_de_recordatorios_arranca_con_el_servidor(db, monkeypatch):
    import time
    from vertice import app as modulo_app
    monkeypatch.setattr(modulo_app, "INTERVALO_RECORDATORIOS", 0.05)
    n = _clinica_con_whatsapp()
    Agenda(db, n, ahora).reservar("573001112233", "Ana Gómez", "Valoración odontológica", "2026-11-10", "15:00")
    enviados = []
    reloj = lambda: datetime(2026, 11, 9, 15, 30)  # noqa: E731
    app = crear_app(Asistente(db, APIFalsa([]), reloj), {n.id: n}, enviar=lambda *a: None,
                    enviar_plantilla=lambda *a: enviados.append(a) or "wamid.loop", recordatorios_activos=True)
    with TestClient(app):          # al entrar arranca el ciclo; al salir se detiene
        for _ in range(40):
            if enviados:
                break
            time.sleep(0.05)
    assert len(enviados) == 1


# --- Usuarios, roles e historial ------------------------------------------
from vertice import usuarios as modulo_usuarios  # noqa: E402


@pytest.fixture
def panel(db, monkeypatch):
    monkeypatch.setattr(modulo_usuarios, "ITERACIONES", 1000)  # claves rápidas en las pruebas
    c = TestClient(crear_app(Asistente(db, APIFalsa([]), ahora), {CLINICA.id: CLINICA}, enviar=lambda *a: None))
    for usuario, nombre, rol, prof in [("dueno1", "Dr. Dueño", "dueno", ""), ("marta", "Marta Recepción", "recepcion", ""),
                                       ("laura", "Dra. Laura", "odontologo", "Dra. Laura Gómez"),
                                       ("andres", "Dr. Andrés", "odontologo", "Dr. Andrés Ríos")]:
        db.crear_usuario(CLINICA.id, usuario, nombre, rol, prof, modulo_usuarios.hashear("Clave1234"))
    return c


def entrar(c, usuario, clave="Clave1234"):
    r = c.post("/panel/api/login", json={"negocio": CLINICA.id, "usuario": usuario, "clave": clave})
    assert r.status_code == 200, r.text
    return {"X-Token": r.json()["token"]}


def test_claves_se_guardan_con_hash_y_se_validan():
    h = modulo_usuarios.hashear("Clave1234")
    assert "Clave1234" not in h and modulo_usuarios.verificar("Clave1234", h)
    assert not modulo_usuarios.verificar("clave1234", h) and not modulo_usuarios.verificar("x", "basura")
    assert modulo_usuarios.validar_clave("corta1") and modulo_usuarios.validar_clave("sololetrasaqui")
    assert modulo_usuarios.validar_clave("12345678") and modulo_usuarios.validar_clave("Clave1234") is None


def test_ingreso_sesion_y_clave_equivocada(panel, db):
    assert panel.post("/panel/api/login", json={"negocio": CLINICA.id, "usuario": "marta", "clave": "mala"}).status_code == 401
    assert panel.post("/panel/api/login", json={"negocio": CLINICA.id, "usuario": "nadie", "clave": "Clave1234"}).status_code == 401
    H = entrar(panel, "Marta")  # el usuario no distingue mayúsculas
    s = panel.get("/panel/api/sesion", headers=H).json()
    assert s["usuario"]["rol"] == "recepcion" and "equipo" not in s["permisos"] and "chats" in s["permisos"]
    assert panel.get("/panel/api/sesion", headers={"X-Token": "inventado"}).status_code == 401
    panel.post("/panel/api/salir", headers=H)
    assert panel.get("/panel/api/sesion", headers=H).status_code == 401   # la sesión se cerró
    # El acceso de soporte con la clave de la clínica sigue funcionando
    soporte = panel.get("/panel/api/sesion", headers={"X-Negocio": CLINICA.id, "X-Clave": "demo123"}).json()
    assert soporte["usuario"]["soporte"] is True and "equipo" in soporte["permisos"]


def test_sesion_vence_y_usuario_desactivado_pierde_acceso(panel, db):
    from datetime import timedelta
    H = entrar(panel, "marta")
    uid = db.usuario_por_login(CLINICA.id, "marta")["id"]
    db.activar_usuario(CLINICA.id, uid, False)
    assert panel.get("/panel/api/sesion", headers=H).status_code == 401
    assert panel.post("/panel/api/login", json={"negocio": CLINICA.id, "usuario": "marta", "clave": "Clave1234"}).status_code == 401
    db.activar_usuario(CLINICA.id, uid, True)
    H = entrar(panel, "marta")
    futuro = (datetime.fromisoformat(db._ahora()) + timedelta(hours=13)).isoformat(timespec="seconds")
    db._ahora = lambda: futuro
    assert panel.get("/panel/api/sesion", headers=H).status_code == 401   # pasaron 12 h


def test_demasiados_intentos_bloquean_el_ingreso(panel):
    for _ in range(5):
        assert panel.post("/panel/api/login", json={"negocio": CLINICA.id, "usuario": "marta", "clave": "mala"}).status_code == 401
    assert panel.post("/panel/api/login", json={"negocio": CLINICA.id, "usuario": "marta", "clave": "Clave1234"}).status_code == 429


def test_permisos_por_rol_los_hace_cumplir_el_servidor(panel, db):
    marta, laura, dueno = entrar(panel, "marta"), entrar(panel, "laura"), entrar(panel, "dueno1")
    cita = {"nombre": "Ana Gómez", "servicio": "Valoración odontológica", "fecha": "2026-11-10", "hora": "09:00", "profesional": "Dra. Laura Gómez"}
    assert panel.post("/panel/api/citas", headers=marta, json=cita).status_code == 200      # recepción agenda
    assert panel.post("/panel/api/citas", headers=laura, json=cita).status_code == 403      # odontólogo no
    for ruta in ("/usuarios", "/bitacora"):
        assert panel.get("/panel/api" + ruta, headers=marta).status_code == 403             # solo el dueño
        assert panel.get("/panel/api" + ruta, headers=dueno).status_code == 200
    for ruta in ("/resumen", "/conversaciones", "/casos"):
        assert panel.get("/panel/api" + ruta, headers=laura).status_code == 403             # odontólogo: solo su agenda
        assert panel.get("/panel/api" + ruta, headers=marta).status_code == 200
    assert panel.post("/panel/api/bloqueos", headers=laura, json={"fecha": "2026-11-10", "desde": "09:00", "hasta": "10:00"}).status_code == 403
    assert panel.post("/panel/api/conversaciones/573001112233/tomar", headers=laura).status_code == 403
    assert panel.get("/panel/api/disponibilidad", headers=laura, params={"fecha": "2026-11-10", "servicio": "limpieza"}).status_code == 403
    assert panel.post("/panel/api/usuarios", headers=marta, json={"usuario": "x1", "nombre": "X", "rol": "dueno", "clave": "Clave1234"}).status_code == 403


def test_odontologo_solo_ve_y_marca_su_agenda(panel, db):
    marta, laura, andres = entrar(panel, "marta"), entrar(panel, "laura"), entrar(panel, "andres")
    for prof, nombre in (("Dra. Laura Gómez", "Ana Gómez"), ("Dr. Andrés Ríos", "Luis Pérez")):
        assert panel.post("/panel/api/citas", headers=marta, json={"nombre": nombre, "servicio": "Valoración odontológica",
                                                                    "fecha": "2026-11-10", "hora": "09:00", "profesional": prof}).status_code == 200
    panel.post("/panel/api/bloqueos", headers=marta, json={"fecha": "2026-11-11", "desde": "09:00", "hasta": "10:00", "profesional": "Dr. Andrés Ríos"})
    panel.post("/panel/api/bloqueos", headers=marta, json={"fecha": "2026-11-12", "desde": "09:00", "hasta": "10:00"})
    ag = panel.get("/panel/api/agenda", headers=laura, params={"desde": "2026-11-09"}).json()
    assert [c["nombre"] for c in ag["citas"]] == ["Ana Gómez"]
    assert len(ag["bloqueos"]) == 1 and ag["bloqueos"][0]["profesional"] == ""   # el de Andrés no es suyo
    propia = ag["citas"][0]["id"]
    ajena = next(c["id"] for c in panel.get("/panel/api/agenda", headers=marta, params={"desde": "2026-11-09"}).json()["citas"] if c["nombre"] == "Luis Pérez")
    assert panel.post(f"/panel/api/citas/{propia}/estado", headers=laura, json={"estado": "asistio"}).status_code == 200
    assert panel.post(f"/panel/api/citas/{ajena}/estado", headers=laura, json={"estado": "asistio"}).status_code == 403
    assert panel.post(f"/panel/api/citas/{propia}/estado", headers=laura, json={"estado": "cancelada"}).status_code == 403
    assert panel.post(f"/panel/api/citas/{propia}/reprogramar", headers=laura, json={"fecha": "2026-11-11", "hora": "10:00"}).status_code == 403


def test_administrar_equipo(panel, db):
    dueno = entrar(panel, "dueno1")
    nuevo = {"usuario": "Sofia.R", "nombre": "Sofía Ramírez", "rol": "recepcion", "clave": "OtraClave99"}
    assert panel.post("/panel/api/usuarios", headers=dueno, json={**nuevo, "clave": "corta"}).status_code == 400
    assert panel.post("/panel/api/usuarios", headers=dueno, json={**nuevo, "rol": "jefe"}).status_code == 400
    assert panel.post("/panel/api/usuarios", headers=dueno, json={**nuevo, "rol": "odontologo", "profesional": "Nadie"}).status_code == 400
    uid = panel.post("/panel/api/usuarios", headers=dueno, json=nuevo).json()["id"]
    assert panel.post("/panel/api/usuarios", headers=dueno, json=nuevo).status_code == 409   # ya existe
    entrar(panel, "sofia.r", "OtraClave99")
    lista = panel.get("/panel/api/usuarios", headers=dueno).json()
    assert all("clave" not in u and "clave_hash" not in u for u in lista) and len(lista) == 5
    # No se puede dejar la clínica sin dueño ni desactivarse a sí mismo
    mio = db.usuario_por_login(CLINICA.id, "dueno1")["id"]
    assert panel.post(f"/panel/api/usuarios/{mio}/estado", headers=dueno, json={"activo": False}).status_code == 400
    # Restablecer clave cierra las sesiones de esa persona
    sesion_sofia = entrar(panel, "sofia.r", "OtraClave99")
    assert panel.post(f"/panel/api/usuarios/{uid}/clave", headers=dueno, json={"clave": "Nueva5678x"}).status_code == 200
    assert panel.get("/panel/api/sesion", headers=sesion_sofia).status_code == 401
    entrar(panel, "sofia.r", "Nueva5678x")


def test_cambiar_mi_clave(panel):
    marta = entrar(panel, "marta")
    assert panel.post("/panel/api/mi-clave", headers=marta, json={"actual": "mala", "nueva": "Nueva5678x"}).status_code == 400
    assert panel.post("/panel/api/mi-clave", headers=marta, json={"actual": "Clave1234", "nueva": "floja"}).status_code == 400
    assert panel.post("/panel/api/mi-clave", headers=marta, json={"actual": "Clave1234", "nueva": "Nueva5678x"}).status_code == 200
    assert panel.get("/panel/api/sesion", headers=marta).status_code == 401      # debe volver a entrar
    entrar(panel, "marta", "Nueva5678x")


def test_la_bitacora_registra_personas_y_asistente(panel, db):
    marta, dueno = entrar(panel, "marta"), entrar(panel, "dueno1")
    panel.post("/panel/api/citas", headers=marta, json={"nombre": "Ana Gómez", "servicio": "Valoración odontológica", "fecha": "2026-11-10", "hora": "09:00"})
    Herramientas(db, CLINICA, "573001112233", ahora).ejecutar("agendar_cita", {"nombre": "Luis Pérez", "servicio": "limpieza", "fecha": "2026-11-10", "hora": "10:00"})
    panel.post("/panel/api/login", json={"negocio": CLINICA.id, "usuario": "marta", "clave": "mala"})
    h = panel.get("/panel/api/bitacora", headers=dueno).json()
    acciones = [(f["quien"], f["rol"], f["accion"]) for f in h]
    assert ("Marta Recepción", "recepcion", "cita_creada") in acciones
    assert ("Sofía", "asistente", "cita_creada") in acciones
    assert ("marta", "-", "ingreso_fallido") in acciones and ("Marta Recepción", "recepcion", "ingreso") in acciones
    assert all("Clave1234" not in json.dumps(f) for f in h)


# --- Modo pre-reserva ------------------------------------------------------
def _pre_reserva():
    from dataclasses import replace
    return replace(CLINICA, modo_agenda="pre_reserva", whatsapp_phone_number_id="123")


def test_en_pre_reserva_el_asistente_aparta_y_la_recepcion_confirma(db):
    n = _pre_reserva()
    avisos = []
    h = Herramientas(db, n, "573001112233", ahora, notificar_dueno=lambda neg, t: avisos.append(t))
    salida, err = h.ejecutar("agendar_cita", {"nombre": "Ana Gómez", "servicio": "Valoración odontológica", "fecha": "2026-11-10", "hora": "09:00"})
    cita = json.loads(salida)
    assert not err and cita["estado"] == "por_confirmar" and "NO confirmada" in cita["nota"]
    assert len(avisos) == 1 and "Solicitud de cita por confirmar" in avisos[0]
    # El horario queda apartado: otros pacientes no lo ven y solo queda un cupo (el otro odontólogo)
    libres = Agenda(db, n, ahora).libres(date(2026, 11, 10), Agenda(db, n, ahora).servicio("Valoración odontológica"))
    assert len(libres["09:00"]) == 1
    # La recepción (panel) agenda directo y queda confirmada, sin pasar por solicitud
    directa = Agenda(db, n, ahora).reservar("573009998877", "Luis Pérez", "Valoración odontológica", "2026-11-10", "10:00", origen="panel")
    assert directa["estado"] == "confirmada"
    # El paciente ve el estado, puede moverla y cancelarla
    citas = json.loads(h.ejecutar("ver_mis_citas", {})[0])["citas"]
    assert citas[0]["estado"] == "por_confirmar"
    movida = json.loads(h.ejecutar("reprogramar_cita", {"cita_id": cita["cita_id"], "fecha": "2026-11-10", "hora": "11:00"})[0])
    assert movida["estado"] == "por_confirmar"
    assert not h.ejecutar("cancelar_cita", {"cita_id": cita["cita_id"]})[1]


def test_panel_solicitudes_confirmar_y_rechazar(panel, db):
    n = _pre_reserva()
    marta, laura = entrar(panel, "marta"), entrar(panel, "laura")
    # El panel de la prueba usa CLINICA; creamos las solicitudes directo en la agenda de la clínica en pre-reserva
    ag = Agenda(db, n, ahora)
    a = ag.reservar("573001112233", "Ana Gómez", "Valoración odontológica", "2026-11-10", "09:00", profesional="Dra. Laura Gómez")["cita_id"]
    b = ag.reservar("573001112244", "Luis Pérez", "Valoración odontológica", "2026-11-10", "09:00", profesional="Dr. Andrés Ríos")["cita_id"]
    lista = panel.get("/panel/api/solicitudes", headers=marta).json()
    assert [c["nombre"] for c in lista] == ["Ana Gómez", "Luis Pérez"] and lista[0]["estado"] == "por_confirmar"
    assert [c["nombre"] for c in panel.get("/panel/api/solicitudes", headers=laura).json()] == ["Ana Gómez"]  # el odontólogo, solo las suyas
    assert panel.post(f"/panel/api/citas/{a}/estado", headers=marta, json={"estado": "confirmada"}).status_code == 200
    assert panel.post(f"/panel/api/citas/{b}/estado", headers=marta, json={"estado": "cancelada"}).status_code == 200
    assert panel.get("/panel/api/solicitudes", headers=marta).json() == []
    # Rechazar libera el horario
    assert "09:00" in ag.libres(date(2026, 11, 10), ag.servicio("Valoración odontológica"))
    dueno = entrar(panel, "dueno1")
    acciones = [f["accion"] for f in panel.get("/panel/api/bitacora", headers=dueno).json()]
    assert "solicitud_confirmada" in acciones and "solicitud_rechazada" in acciones


def test_recordatorios_ignoran_solicitudes_sin_confirmar(db):
    n = _pre_reserva()
    Agenda(db, n, ahora).reservar("573001112233", "Ana Gómez", "Valoración odontológica", "2026-11-10", "15:00")  # asistente: por confirmar
    enviados = []
    assert recordatorios.ciclo(db, {n.id: n}, lambda *a: enviados.append(a) or "w", datetime(2026, 11, 9, 15, 30))["enviados"] == 0


def test_prompt_y_configuracion_de_pre_reserva(tmp_path):
    assert "solicitada" in prompt_sistema(_pre_reserva()) and "solicitada" not in prompt_sistema(CLINICA)
    from vertice.negocio import cargar_negocio
    ruta = tmp_path / "malo.yaml"
    ruta.write_text((Path(__file__).parent.parent / "negocios" / "clinica-demo.yaml").read_text(encoding="utf-8") + "\nmodo_agenda: manual\n", encoding="utf-8")
    with pytest.raises(ValueError):
        cargar_negocio(ruta)


# --- P0-8: robustez, salud, respaldos y privacidad ----------------------------
from vertice import app as modulo_app, monitor, respaldo, salud as modulo_salud  # noqa: E402


def test_un_aviso_al_equipo_que_falla_no_tumba_la_conversacion(db):
    def roto(neg, texto):
        raise RuntimeError("401 token vencido")
    h = Herramientas(db, CLINICA, "573001112233", ahora, notificar_dueno=roto)
    salida, err = h.ejecutar("pasar_a_humano", {"motivo": "Dolor fuerte"})
    assert not err and json.loads(salida)["equipo_notificado"] is True       # el caso quedó registrado y Sofía puede seguir
    assert db.filas("escalaciones", CLINICA.id)[0]["motivo"] == "Dolor fuerte"
    assert db.fallos_desde("2000-01-01") == {"envio": 1}


def test_si_whatsapp_rechaza_la_respuesta_queda_un_caso_para_el_equipo(db):
    n = _reemplazar(CLINICA, whatsapp_phone_number_id="123")

    def rechaza(pid, para, t):
        raise RuntimeError("131047 fuera de la ventana de 24 h")
    c = TestClient(crear_app(Asistente(db, APIFalsa([respuesta(texto("Hola"))]), ahora), {n.id: n}, enviar=rechaza, recordatorios_activos=False))
    assert c.post("/webhook", json=payload()).status_code == 200
    assert db.fallos_desde("2000-01-01") == {"envio": 1}
    assert "No se pudo enviar la respuesta" in db.filas("escalaciones", n.id)[0]["motivo"]


def test_error_inesperado_no_deja_al_paciente_sin_respuesta_ni_pierde_su_mensaje(db):
    n = _reemplazar(CLINICA, whatsapp_phone_number_id="123")
    enviados = []

    class Roto(Asistente):
        def responder(self, *a, **k):
            raise ZeroDivisionError("bug")
    c = TestClient(crear_app(Roto(db, APIFalsa([]), ahora), {n.id: n}, enviar=lambda pid, para, t: enviados.append(t),
                             recordatorios_activos=False))
    c.post("/webhook", json=payload(texto_msg="Necesito una cita urgente"))
    from vertice.agente import RESPUESTA_FALLA
    assert enviados == [RESPUESTA_FALLA]
    assert db.mensajes_chat(n.id, "573001112233")[0]["texto"] == "Necesito una cita urgente"
    assert "Respóndele a mano" in db.filas("escalaciones", n.id)[0]["motivo"]
    assert db.fallos_desde("2000-01-01") == {"atender": 1}


def test_modo_produccion_exige_secretos_y_oculta_la_documentacion(db, monkeypatch):
    n = _reemplazar(CLINICA, whatsapp_phone_number_id="123")
    monkeypatch.setenv("VERTICE_ENTORNO", "produccion")
    for var in ("WHATSAPP_TOKEN",):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(modulo_app, "APP_SECRET", "")
    monkeypatch.setattr(modulo_app, "VERIFY_TOKEN", "")
    with pytest.raises(RuntimeError, match="WHATSAPP_APP_SECRET"):
        crear_app(Asistente(db, APIFalsa([]), ahora), {n.id: n})
    monkeypatch.setattr(modulo_app, "APP_SECRET", "s")
    monkeypatch.setattr(modulo_app, "VERIFY_TOKEN", "v")
    monkeypatch.setenv("WHATSAPP_TOKEN", "t")
    c = TestClient(crear_app(Asistente(db, APIFalsa([]), ahora), {n.id: n}, recordatorios_activos=False))
    assert c.get("/docs").status_code == 404 and c.get("/openapi.json").status_code == 404
    assert c.post("/webhook", json=payload()).status_code == 401            # sin firma: rechazado
    assert db.fallos_desde("2000-01-01") == {"firma": 1}


def test_salud_publica_no_revela_nada_y_el_detalle_exige_token(db, monkeypatch):
    monkeypatch.setattr(modulo_app, "MONITOR_TOKEN", "secreto-monitor")
    c = TestClient(crear_app(Asistente(db, APIFalsa([]), ahora), {CLINICA.id: CLINICA}, recordatorios_activos=False))
    assert c.get("/salud").json() == {"ok": True}
    assert c.get("/salud/detalle").status_code == 404
    assert c.get("/salud/detalle", headers={"X-Monitor": "otro"}).status_code == 404
    d = c.get("/salud/detalle", headers={"X-Monitor": "secreto-monitor"}).json()
    assert {"ultimo_webhook", "fallos_ultima_hora", "disco_libre_pct", "casos_abiertos"} <= d.keys()


def test_el_panel_envia_cabeceras_de_seguridad(db):
    c = TestClient(crear_app(Asistente(db, APIFalsa([]), ahora), {CLINICA.id: CLINICA}, recordatorios_activos=False))
    h = c.get("/panel").headers
    assert h["cache-control"] == "no-store" and h["x-frame-options"] == "DENY" and "frame-ancestors 'none'" in h["content-security-policy"]


def test_webhook_registra_cuando_llego_el_ultimo_mensaje(db):
    n = _reemplazar(CLINICA, whatsapp_phone_number_id="123")
    c = TestClient(crear_app(Asistente(db, APIFalsa([respuesta(texto("Hola"))]), ahora), {n.id: n}, enviar=lambda *a: "w", recordatorios_activos=False))
    c.post("/webhook", json=payload())
    assert db.estado("ultimo_webhook") == AHORA.isoformat(timespec="seconds")


@pytest.fixture
def disco_sano(monkeypatch):
    monkeypatch.setattr(modulo_salud.shutil, "disk_usage", lambda ruta: SimpleNamespace(total=100, used=10, free=90))


def test_evaluar_detecta_los_problemas_que_dejan_sin_servicio(db, disco_sano):
    from datetime import timedelta
    base = modulo_salud.recolectar(db, {CLINICA.id: CLINICA}, AHORA)
    assert modulo_salud.evaluar(base, AHORA) == {}                      # sistema nuevo y sano: ninguna alerta
    mal = {**base, "fallos_ultima_hora": {"envio": 3, "modelo": 3, "atender": 1, "firma": 1, "recordatorio": 4},
           "ultimo_webhook": (AHORA - timedelta(hours=40)).isoformat(), "ultimo_ciclo_recordatorios": (AHORA - timedelta(minutes=30)).isoformat(),
           "caso_mas_antiguo_min": 300, "casos_abiertos": 2, "solicitud_mas_antigua_min": 200, "solicitudes_pendientes": 1,
           "disco_libre_pct": 5.0, "respaldos_configurados": True, "ultimo_respaldo": (AHORA - timedelta(hours=30)).isoformat(),
           "subida_configurada": True, "ultima_subida": None}
    assert set(modulo_salud.evaluar(mal, AHORA)) == {"envio", "modelo", "atender", "firma", "recordatorio", "sin_mensajes", "ciclo",
                                                      "casos", "solicitudes", "disco", "respaldo", "respaldo_remoto"}


def test_monitor_avisa_una_vez_repite_a_las_6_h_y_avisa_la_recuperacion(db, disco_sano):
    from datetime import timedelta
    enviados = []
    ok = lambda url: True  # noqa: E731
    for _ in range(3):
        db.registrar_fallo(CLINICA.id, "envio", "token vencido")
    # db._ahora está fijo en AHORA: los fallos cuentan como "de la última hora"
    r1 = monitor.ejecutar(db, {CLINICA.id: CLINICA}, AHORA, enviados.append, responde=ok)
    assert "envio" in r1 and len(enviados) == 1 and enviados[0].startswith("🔴")
    monitor.ejecutar(db, {CLINICA.id: CLINICA}, AHORA + timedelta(minutes=5), enviados.append, responde=ok)
    assert len(enviados) == 1                                           # no se repite cada 5 minutos
    monitor.ejecutar(db, {CLINICA.id: CLINICA}, AHORA + timedelta(minutes=30), enviados.append, responde=ok)
    assert len(enviados) == 1
    # Pasan las horas: el problema ya no está en la última hora -> recuperado
    monitor.ejecutar(db, {CLINICA.id: CLINICA}, AHORA + timedelta(hours=7), enviados.append, responde=ok)
    assert enviados[-1] == "✅ Recuperado: envio"
    # El servidor deja de responder desde afuera
    r = monitor.ejecutar(db, {CLINICA.id: CLINICA}, AHORA + timedelta(hours=8), enviados.append, url_publica="https://x.test", responde=lambda u: False)
    assert "caido" in r and "no responde" in enviados[-1]


def _base_con_datos(tmp_path):
    ruta = tmp_path / "vertice.db"
    base = BaseDatos(ruta)
    base.crear_usuario("c", "ana", "Ana", "dueno", "", "hash")
    Agenda(base, CLINICA, ahora).reservar("573001112233", "Ana Gómez", "Valoración odontológica", "2026-11-10", "09:00")
    base.guardar_historial("c", "573001112233", [{"role": "user", "content": "hola"}], AHORA)
    return ruta, base


def test_respaldo_crear_verificar_y_restaurar_con_los_mismos_datos(tmp_path):
    ruta, base = _base_con_datos(tmp_path)
    carpeta = tmp_path / "respaldos"
    f = respaldo.crear(ruta, carpeta, AHORA)
    assert f.name == "vertice-20261109-0900.db.gz" and oct(f.stat().st_mode)[-3:] == "600"
    base.crear_usuario("c", "luis", "Luis", "recepcion", "", "hash")   # cambios posteriores no entran al respaldo ya hecho
    assert respaldo.verificar(carpeta)["registros"] == {"citas": 1, "conversaciones": 1, "usuarios": 1, "prospectos": 0}
    destino = tmp_path / "restaurada.db"
    assert respaldo.restaurar(f, destino)["citas"] == 1
    assert len(BaseDatos(destino).citas_entre(CLINICA.id, "2026-11-01", "2026-12-01")) == 1
    with pytest.raises(respaldo.ErrorRespaldo):                          # no pisa una base existente sin permiso
        respaldo.restaurar(f, destino)


def test_respaldo_retencion_diaria_y_semanal(tmp_path):
    from datetime import timedelta
    ruta, _ = _base_con_datos(tmp_path)
    carpeta = tmp_path / "r"
    inicio = datetime(2026, 8, 1, 3, 0)
    for dia in range(100):
        respaldo.crear(ruta, carpeta, inicio + timedelta(days=dia), diarios=14, semanales=8)
    nombres = sorted(f.name for f in carpeta.glob("vertice-*"))
    fechas = [datetime.strptime(n[8:21], "%Y%m%d-%H%M") for n in nombres]
    hoy = inicio + timedelta(days=99)
    assert sum(1 for f in fechas if hoy - f <= timedelta(days=14)) == 15      # los últimos 14 días
    assert all(f.weekday() == 6 for f in fechas if hoy - f > timedelta(days=14))  # y de ahí atrás solo domingos
    assert max(hoy - f for f in fechas) <= timedelta(weeks=8)


@pytest.mark.skipif(shutil.which("openssl") is None, reason="requiere openssl")
def test_respaldo_cifrado_y_subida_a_otro_lugar(tmp_path):
    ruta, _ = _base_con_datos(tmp_path)
    otro = tmp_path / "otro_lugar"
    otro.mkdir()
    f = respaldo.crear(ruta, tmp_path / "r", AHORA, clave="clave-larga-segura", subir=f"cp {{archivo}} {otro}/")
    assert f.name.endswith(".db.gz.enc") and b"SQLite" not in f.read_bytes()      # no se puede leer sin la clave
    assert (otro / f.name).exists() and (tmp_path / "r" / "subida_ok.txt").exists()
    with pytest.raises(respaldo.ErrorRespaldo, match="falta"):
        respaldo.restaurar(f, tmp_path / "x.db")
    with pytest.raises(respaldo.ErrorRespaldo):
        respaldo.restaurar(f, tmp_path / "y.db", clave="otra-clave")
    assert respaldo.restaurar(f, tmp_path / "z.db", clave="clave-larga-segura")["citas"] == 1
    with pytest.raises(respaldo.ErrorRespaldo, match="NO se pudo subir"):
        respaldo.crear(ruta, tmp_path / "r2", AHORA, subir="false {archivo}")


def test_respaldo_detecta_una_copia_danada(tmp_path):
    import gzip
    carpeta = tmp_path / "r"
    carpeta.mkdir()
    malo = carpeta / "vertice-20261109-0900.db.gz"
    malo.write_bytes(gzip.compress(b"esto no es una base de datos" * 100))
    with pytest.raises(respaldo.ErrorRespaldo):
        respaldo.verificar(carpeta)


def test_aviso_de_privacidad_se_entrega_una_sola_vez_y_queda_registrado(db):
    n = _reemplazar(CLINICA, whatsapp_phone_number_id="123", aviso_privacidad=True, politica_url="https://clinica.test/datos")
    api = APIFalsa([respuesta(texto("¡Hola!")), respuesta(texto("Claro"))])
    enviados = []
    c = TestClient(crear_app(Asistente(db, api, ahora), {n.id: n}, enviar=lambda pid, para, t: enviados.append(t) or "w", recordatorios_activos=False))
    c.post("/webhook", json=payload(msg_id="wamid.1"))
    assert len(enviados) == 2 and "asistente virtual" in enviados[0] and "https://clinica.test/datos" in enviados[0] and enviados[1] == "¡Hola!"
    c.post("/webhook", json=payload(msg_id="wamid.2"))                  # el segundo mensaje ya no repite el aviso
    assert len(enviados) == 3 and enviados[2] == "Claro"
    assert db.con.execute("SELECT version FROM autorizaciones").fetchone()["version"] == "v1"


def test_derechos_del_paciente_exportar_y_eliminar(panel, db):
    dueno, marta = entrar(panel, "dueno1"), entrar(panel, "marta")
    cli = "573001112233"
    Agenda(db, CLINICA, ahora).reservar(cli, "Ana Gómez", "Valoración odontológica", "2026-11-10", "09:00")   # cita futura
    db.registrar_prospecto(CLINICA.id, cli, "Ana Gómez", "Blanqueamiento", "pidió precio")
    db.guardar_mensaje_chat(CLINICA.id, cli, "paciente", "Hola, soy Ana", "whatsapp")
    db.guardar_historial(CLINICA.id, cli, [{"role": "user", "content": "[Mensaje recibido el lunes 2026-11-09 a las 09:00] Hola"}], AHORA)
    db.registrar_autorizacion(CLINICA.id, cli, "v1")
    assert panel.get(f"/panel/api/pacientes/{cli}/datos", headers=marta).status_code == 403              # solo el dueño
    assert panel.delete(f"/panel/api/pacientes/{cli}/datos", headers=marta).status_code == 403
    datos = panel.get(f"/panel/api/pacientes/{cli}/datos", headers=dueno).json()
    assert datos["citas"][0]["nombre"] == "Ana Gómez" and datos["interesados"][0]["interes"] == "Blanqueamiento" and datos["autorizacion"]
    assert datos["conversaciones"][0]["mensajes"][0]["texto"] == "Hola"
    assert panel.delete("/panel/api/pacientes/abc/datos", headers=dueno).status_code == 400
    r = panel.delete(f"/panel/api/pacientes/{cli}/datos", headers=dueno).json()
    assert (r["conversaciones"], r["interesados"], r["citas_futuras_canceladas"], r["citas_anonimizadas"]) == (1, 1, 1, 1)
    despues = panel.get(f"/panel/api/pacientes/{cli}/datos", headers=dueno).json()
    assert not despues["citas"] and not despues["conversaciones"] and not despues["interesados"] and not despues["autorizacion"]
    fila = db.con.execute("SELECT nombre, cliente, estado FROM citas").fetchone()
    assert (fila["nombre"], fila["cliente"], fila["estado"]) == ("Paciente eliminado", "eliminado", "cancelada")
    bit = " ".join(f["detalle"] for f in panel.get("/panel/api/bitacora", headers=dueno).json())
    assert cli not in bit                                                                                  # ni el teléfono queda en el historial


def test_demasiados_intentos_desde_una_misma_red_se_bloquean(panel):
    for _ in range(30):
        assert panel.get("/panel/api/sesion", headers={"X-Negocio": CLINICA.id, "X-Clave": "mala"}).status_code == 401
    assert panel.get("/panel/api/sesion", headers={"X-Negocio": CLINICA.id, "X-Clave": "demo123"}).status_code == 429


# --- Varios odontólogos: el paciente puede pedir uno ---------------------------
def test_paciente_pide_un_odontologo_en_particular(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    # Martes: los dos atienden. Con "Andrés" (solo una parte del nombre) se filtran sus horarios y se agenda con él.
    d = json.loads(h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-10", "servicio": "Valoración odontológica", "profesional": "andrés"})[0])
    assert d["horarios_de"] == "Dr. Andrés Ríos" and d["atienden_este_servicio"] == ["Dra. Laura Gómez", "Dr. Andrés Ríos"]
    cita = json.loads(h.ejecutar("agendar_cita", {"nombre": "Ana Gómez", "servicio": "Valoración odontológica", "fecha": "2026-11-10",
                                                  "hora": "09:00", "profesional": "Andrés"})[0])
    assert cita["profesional"] == "Dr. Andrés Ríos"
    # Esa hora con Andrés ya no está; con Laura sí. Si insisten en Andrés, no se la da a otro
    d2 = json.loads(Herramientas(db, CLINICA, "2", ahora).ejecutar("consultar_disponibilidad", {"fecha": "2026-11-10", "servicio": "Valoración odontológica", "profesional": "Andrés"})[0])
    assert "09:00" not in d2["horarios_libres"]
    _, err = Herramientas(db, CLINICA, "2", ahora).ejecutar("agendar_cita", {"nombre": "Luis Pérez", "servicio": "Valoración odontológica", "fecha": "2026-11-10", "hora": "09:00", "profesional": "Andrés"})
    assert err
    sin_preferencia = json.loads(Herramientas(db, CLINICA, "2", ahora).ejecutar("agendar_cita", {"nombre": "Luis Pérez", "servicio": "Valoración odontológica",
                                                                                              "fecha": "2026-11-10", "hora": "09:00", "profesional": ""})[0])
    assert sin_preferencia["profesional"] == "Dra. Laura Gómez"


def test_profesional_inexistente_o_que_no_hace_ese_servicio(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    salida, err = h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-10", "servicio": "Resina estética", "profesional": "Andrés"})
    assert err and "Dra. Laura Gómez" in salida                       # el Dr. Andrés no hace resinas: se ofrece a quien sí
    assert h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-10", "servicio": "Valoración odontológica", "profesional": "Pedro"})[1]
    assert h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-10", "servicio": "Valoración odontológica", "profesional": "Dr"})[1]  # ambiguo


def test_clinica_con_un_solo_consultorio_ignora_el_profesional(db):
    n = _reemplazar(CLINICA, profesionales=[])
    h = Herramientas(db, n, "573001112233", ahora)
    d = json.loads(h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-10", "servicio": "Valoración odontológica", "profesional": "cualquiera"})[0])
    assert "atienden_este_servicio" not in d and d["horarios_libres"]


def test_el_prompt_lista_al_equipo_solo_si_hay_varios():
    texto = prompt_sistema(CLINICA)
    assert "Dr. Andrés Ríos: solo Valoración de ortodoncia" in texto and "Dra. Laura Gómez: todos los servicios" in texto and "campo profesional" in texto
    assert "Deja siempre vacío el campo profesional" in prompt_sistema(_reemplazar(CLINICA, profesionales=[]))
