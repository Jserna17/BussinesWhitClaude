# Vértice · Asistente de WhatsApp (demo v0.1)

Recepcionista con IA que atiende el WhatsApp de un negocio: responde preguntas, da precios y horarios,
**consulta disponibilidad, agenda, muestra y cancela citas**, guarda prospectos y **pasa a una persona**
los casos delicados (avisando al dueño por WhatsApp).

Un solo servidor atiende a **muchos negocios**: cada cliente es un archivo en `negocios/`.

## Qué incluye
| Archivo | Para qué |
|---|---|
| `vertice/agente.py` | Prompt de cada negocio + ciclo con la API de Claude (herramientas, caché, respaldo) |
| `vertice/herramientas.py` | Agenda (disponibilidad, agendar, ver, cancelar), prospectos, traspaso a humano |
| `vertice/whatsapp.py` | Cloud API de Meta: firma del webhook, lectura de mensajes, envío |
| `vertice/app.py` | Servidor web (FastAPI) con el webhook `/webhook` y `/salud` |
| `vertice/salud.py`, `vertice/monitor.py` | Qué medir y cuándo avisar (WhatsApp rechazando, modelo caído, sin mensajes, respaldos viejos…) |
| `vertice/respaldo.py` | Respaldos consistentes, verificados, cifrados, con retención y subida a otro lugar; restauración |
| `vertice/usuarios.py` | Usuarios, roles y permisos del panel |
| `despliegue/` | Guía y scripts para instalar en un servidor (HTTPS, servicios, respaldos, monitoreo) — ver `despliegue/README.md` |
| `vertice/chat.py` | **Simulador en la terminal** para probar o hacer demos sin WhatsApp |
| `vertice/db.py` | SQLite: conversaciones, citas, prospectos, casos para humanos |
| `negocios/clinica-demo.yaml` | Clínica dental ficticia ("Sofía") para demos |
| `negocios/taller-demo.yaml` | Taller de motos ficticio ("Max") para demos |
| `vertice/motores.py` | Motores intercambiables: Claude u OpenAI |
| `vertice/agenda.py` | Motor de agenda sin cruces (profesionales, almuerzo, bloqueos, reservas atómicas) |
| `vertice/panel.py` + `panel.html` | Panel web del médico (API + página) |
| `vertice/transcripcion.py` | Convierte el historial en chat legible para el panel |
| `vertice/datos_demo.py` | Datos de ejemplo para mostrar el panel |
| `tests/` | 22 pruebas sin conexión |

## Decisiones técnicas
- **Modelo:** `claude-opus-5-5` con esfuerzo `low` (respuestas rápidas). Se cambia con las variables
  `VERTICE_MODELO` y `VERTICE_ESFUERZO`, sin tocar código. Ver costos abajo.
- **Respaldo:** si el modelo declina un mensaje, la API lo reintenta en otro modelo (`fallbacks: "default"`).
  Si aun así falla, el cliente recibe un mensaje amable y el dueño un aviso.
- **Caché del prompt:** el prompt de cada negocio es fijo (sin fechas) y la fecha va en cada mensaje,
  así la información del negocio se cobra ~10 % en mensajes siguientes.
- **Política de Meta:** el asistente solo habla del negocio (Meta prohíbe chatbots de propósito general
  desde el 15-ene-2026).
- **Historial:** se guarda completo; tras 24 h sin mensajes o 60 mensajes empieza una conversación nueva.
- **Seguridad:** valida la firma de Meta, ignora entregas duplicadas, nunca agenda horas ocupadas ni
  cancela citas de otro número.

## Agenda sin cruces (v0.2)
Motor en `vertice/agenda.py`, compartido por el asistente y el panel, así ambos aplican las mismas reglas:
- **Varios odontólogos/sillas** (`profesionales` en el YAML; cada uno puede limitarse a ciertos servicios).
  Una hora está libre si **algún** profesional que hace ese servicio está libre durante **toda** la duración.
- **Horario partido** (almuerzo): `lunes: [["08:00","12:00"],["14:00","18:00"]]`. Un servicio nunca se cruza
  con el cierre ni con el almuerzo.
- **Bloqueos** desde el panel (toda la clínica o un profesional): festivos, congresos, reuniones.
- **Sin dobles reservas**: la reserva se vuelve a comprobar dentro de una transacción exclusiva de SQLite
  (`BEGIN IMMEDIATE`), así dos pacientes escribiendo al mismo tiempo nunca reciben la misma silla. Probado con
  20 reservas simultáneas → solo entran las que caben.
- Cancelar libera el horario; "asistió / no asistió" queda registrado para medir inasistencia.
- El asistente solo agenda con **nombre y apellido** reales (regla en el código).

## Panel del médico (`/panel`)
Mismo servidor del webhook: `http://SERVIDOR/panel`. Entra con el código de la clínica (`clinica-demo`) y su
clave (`panel_clave` en el YAML o variable `VERTICE_PANEL_CLAVE_<ID>`; la demo usa `demo123`).
- **Resumen:** mensajes atendidos, % fuera de horario, citas agendadas por el asistente, citas de hoy,
  casos abiertos, interesados, inasistencia, gráfica de mensajes por día y próximas citas.
- **Agenda semanal:** citas por día con su origen (asistente o recepción), botones Asistió / No asistió /
  Cancelar, nueva cita (solo muestra horas realmente libres) y bloqueos de horario.
- **Conversaciones:** cada chat completo como en WhatsApp, con las acciones del asistente (citas agendadas,
  avisos al equipo, intentos que el sistema frenó).
- **Casos e interesados:** lo que el asistente pasó al equipo (marcar resuelto) y pacientes para seguimiento.

Ver capturas en `../demo/capturas/`. Para una base de demostración con datos:
```bash
python -m vertice.pruebas_vivo --proveedor openai --db demo.db   # 20 conversaciones reales
python -m vertice.datos_demo demo.db                              # citas y bloqueo de ejemplo
VERTICE_DB=demo.db uvicorn vertice.app:app --port 8000            # abrir http://localhost:8000/panel
```

## Motores de IA: Claude u OpenAI
El asistente funciona con dos proveedores; se elige con `VERTICE_PROVEEDOR`:

| Proveedor | Variables | Modelo por defecto |
|---|---|---|
| `claude` (por defecto) | `ANTHROPIC_API_KEY`, `VERTICE_MODELO`, `VERTICE_ESFUERZO` | `claude-opus-5-5` |
| `openai` | `OPENAI_API_KEY`, `VERTICE_MODELO_OPENAI` | `gpt-5.4-mini` (probado: 20/20 en la batería, 2026-10-27) |

Las herramientas, el prompt y la base de datos son los mismos; cada proveedor guarda su historial aparte.

## Probarlo en la terminal (simulador)
```bash
cd agente
pip install -r requirements.txt

# Con OpenAI (prueba inicial)
export VERTICE_PROVEEDOR=openai
export OPENAI_API_KEY=sk-...              # nunca la pegues en un chat ni la subas al repositorio

# o con Claude
# export ANTHROPIC_API_KEY=sk-ant-...

python -m vertice.chat clinica-demo         # o taller-demo; agrega --debug para ver herramientas
```
En Windows (PowerShell) usa `$env:OPENAI_API_KEY="sk-..."` y `$env:VERTICE_PROVEEDOR="openai"`.
Ejemplos para probar: "¿Cuánto vale una limpieza?", "Quiero cita mañana en la tarde",
"¿Qué citas tengo?", "Me duele mucho una muela" (debe pasar a humano), "¿Quién ganó el partido?"
(debe negarse con amabilidad).

## Conectarlo a WhatsApp (Cloud API de Meta)
1. Crear una cuenta en **developers.facebook.com** → *Crear app* → tipo *Empresa* → agregar el producto **WhatsApp**.
2. En *WhatsApp → Configuración de la API* Meta da un **número de prueba gratis**, su **Phone number ID**
   y un **token temporal**. Agregar tu celular como destinatario de prueba.
3. Poner el *Phone number ID* en `whatsapp_phone_number_id` del YAML del negocio.
4. Publicar el servidor con HTTPS (un VPS con Caddy, o para pruebas un túnel como `cloudflared`):
   ```bash
   export WHATSAPP_TOKEN=...            # token de acceso
   export WHATSAPP_VERIFY_TOKEN=...     # una clave que tú inventas
   export WHATSAPP_APP_SECRET=...       # Configuración básica de la app → Clave secreta
   uvicorn vertice.app:app --host 0.0.0.0 --port 8000
   ```
5. En *WhatsApp → Configuración → Webhook*: URL `https://TU-DOMINIO/webhook`, el mismo verify token, y
   suscribirse al campo **messages**.
6. Escribir al número de prueba desde tu celular. 🎉

Para un cliente real: su número debe estar en su propia cuenta de WhatsApp Business (verificada) y se
necesita un token permanente (usuario del sistema). Los recordatorios y campañas requieren plantillas
aprobadas por Meta (fase siguiente).

## Costos estimados del modelo (por verificar con uso real)
Precios por millón de tokens: Opus 5.5 USD 4 entrada / 20 salida; Haiku 5.5 USD 0,10 / 0,50.
Una conversación típica (5–6 mensajes con herramientas) consume aprox. 10.000 tokens de entrada no
cacheados y 3.000 de salida:
| Modelo | Por conversación | 300 conversaciones/mes por cliente |
|---|---|---|
| `claude-opus-5-5` (actual) | ~USD 0,10 (~COP 400) | ~COP 120.000 |
| `claude-haiku-5-5` | ~USD 0,003 | ~COP 3.500 |

Con el plan Arranque (COP 450.000) Opus deja menos margen. Recomendación: hacer las demos con Opus y
**probar Haiku con las mismas conversaciones antes del primer cliente**; usar el más barato que
mantenga la calidad. Se mide con `--debug` (muestra tokens por mensaje).

## Pruebas
```bash
python -m pytest -q                                   # 22 pruebas sin conexión (gratis)
python -m vertice.pruebas_vivo --proveedor openai      # 20 conversaciones reales (gasta créditos, ~centavos de USD)
python -m vertice.pruebas_vivo --proveedor openai --solo 2,5   # solo algunos escenarios
```
La batería en vivo guarda las transcripciones y las verificaciones en `resultados/`.

## Próximas versiones
- Google Calendar del negocio en lugar de la agenda interna.
- Recordatorios 24 h / 2 h antes (plantillas de Meta) y campañas de reactivación.
- Panel simple para el dueño (citas, prospectos, casos) y reporte semanal automático.
- Audios de WhatsApp (transcripción).
