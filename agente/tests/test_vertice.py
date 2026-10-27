"""Pruebas sin conexión: la API de Claude y WhatsApp se simulan."""

import hashlib
import hmac
import json
from datetime import datetime
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
# Fecha fija: lunes 2 de noviembre de 2026, 9:00 a. m.
AHORA = datetime(2026, 11, 2, 9, 0)


def ahora():
    return AHORA


@pytest.fixture
def db(tmp_path):
    return BaseDatos(tmp_path / "prueba.db")


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
def test_disponibilidad_respeta_horario_y_citas(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    salida, error = h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-02", "servicio": "Limpieza dental (profilaxis)"})
    datos = json.loads(salida)
    assert not error
    # Abre a las 08:00 pero solo se ofrece desde una hora después de "ahora" (09:00 -> 10:00).
    assert datos["horarios_libres"][0] == "10:00"

    h.ejecutar("agendar_cita", {"nombre": "Ana Gómez", "servicio": "limpieza", "fecha": "2026-11-02", "hora": "10:00"})
    datos = json.loads(h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-02", "servicio": "limpieza"})[0])
    assert "10:00" not in datos["horarios_libres"]
    assert "10:30" not in datos["horarios_libres"]  # la limpieza dura 45 min


def test_no_agenda_domingo_ni_hora_ocupada(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    domingo = json.loads(h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-08", "servicio": "Valoración odontológica"})[0])
    assert domingo["horarios_libres"] == []

    ok, error = h.ejecutar("agendar_cita", {"nombre": "Ana", "servicio": "Valoración odontológica", "fecha": "2026-11-03", "hora": "08:00"})
    assert not error
    otro = Herramientas(db, CLINICA, "573009998877", ahora)
    _, error = otro.ejecutar("agendar_cita", {"nombre": "Luis", "servicio": "Valoración odontológica", "fecha": "2026-11-03", "hora": "08:00"})
    assert error


def test_servicio_inexistente_y_fecha_pasada(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    salida, error = h.ejecutar("consultar_disponibilidad", {"fecha": "2026-11-03", "servicio": "Cirugía de rodilla"})
    assert error and "Servicios disponibles" in salida
    _, error = h.ejecutar("consultar_disponibilidad", {"fecha": "2026-10-01", "servicio": "limpieza"})
    assert error


def test_cancelar_solo_citas_propias(db):
    h = Herramientas(db, CLINICA, "573001112233", ahora)
    cita = json.loads(h.ejecutar("agendar_cita", {"nombre": "Ana", "servicio": "limpieza", "fecha": "2026-11-03", "hora": "09:00"})[0])
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
        respuesta(herramienta("t1", "consultar_disponibilidad", {"fecha": "2026-11-03", "servicio": "limpieza"}), parada="tool_use"),
        respuesta(texto("Mañana tengo *8:00* o *8:30*. ¿Cuál prefieres?")),
        respuesta(texto("¡Listo!")),
    ])
    asistente = Asistente(db, api, ahora)
    r = asistente.responder(CLINICA, "573001112233", "Quiero una limpieza mañana")
    assert "8:00" in r

    primera, segunda = api.peticiones[0], api.peticiones[1]
    assert primera["model"] and primera["fallbacks"] == "default"
    assert primera["cache_control"] == {"type": "ephemeral"}
    assert "[Mensaje recibido el lunes 2026-11-02 a las 09:00]" in primera["messages"][0]["content"]
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
                                                           "fecha": "2026-11-03", "hora": "09:00"})]),
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
