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
| `vertice/chat.py` | **Simulador en la terminal** para probar o hacer demos sin WhatsApp |
| `vertice/db.py` | SQLite: conversaciones, citas, prospectos, casos para humanos |
| `negocios/clinica-demo.yaml` | Clínica dental ficticia ("Sofía") para demos |
| `negocios/taller-demo.yaml` | Taller de motos ficticio ("Max") para demos |
| `tests/` | 12 pruebas sin conexión |

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

## Probarlo en la terminal (simulador)
```bash
cd agente
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...        # clave de console.anthropic.com
python -m vertice.chat clinica-demo         # o taller-demo; agrega --debug para ver herramientas
```
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
python -m pytest -q
```

## Próximas versiones
- Google Calendar del negocio en lugar de la agenda interna.
- Recordatorios 24 h / 2 h antes (plantillas de Meta) y campañas de reactivación.
- Panel simple para el dueño (citas, prospectos, casos) y reporte semanal automático.
- Audios de WhatsApp (transcripción).
