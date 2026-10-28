# 14 · Integración de la agenda de la clínica y riesgos de operación

> Pregunta del fundador (2026-10-28): ¿qué le falta al panel para garantizar el funcionamiento?, ¿cómo
> incorporamos la agenda de un médico que decida trabajar con nosotros?, ¿qué factores no estamos viendo?
>
> Regla de oro: **una cita solo existe en un lugar.** Si la clínica tiene dos agendas (la nuestra y su cuaderno,
> Excel o software), tarde o temprano habrá dos pacientes en la misma silla. Todo lo de abajo protege esa regla.

---

## 1. Cómo incorporamos la agenda de la clínica

### 1.1 Primero averiguar dónde vive hoy (pregunta obligatoria en la visita)
"¿Dónde anotan hoy las citas?". Respuestas típicas en Pereira y lo que hacemos en cada caso:

| Dónde está la agenda hoy | Modo Vértice | Qué implica |
|---|---|---|
| Cuaderno, agenda física, Excel, el celular de la recepcionista | **A. Vértice es la agenda** | Cargamos las citas futuras y desde ese día todo se agenda en el panel (también las llamadas y los que llegan en persona). Es el caso más fácil y probablemente el más común. |
| Google Calendar | **B. Sincronizada** | Conexión con Google Calendar en los dos sentidos: sus eventos bloquean horas para Sofía y las citas de Sofía aparecen en su calendario. API gratuita. |
| Software odontológico con API (Dentalink, AgendaPro, Medesk…) | **B. Sincronizada** (adaptador por software) | Hay que pedir el acceso a la API a cada proveedor y construir un conector. Se hace cuando un cliente real lo use, no antes. |
| Software sin API, o la clínica no quiere cambiar | **C. Pre-reserva** | Sofía ve la disponibilidad que la clínica publique (o un horario de franjas) pero **no confirma**: deja la cita "por confirmar" y la recepción la confirma desde el panel con un clic. Ya ahorra el 80 % del trabajo y no rompe nada. |

No encontré una fuente confiable sobre qué software usan más las clínicas en Colombia; varias páginas
de proveedores (AgendaPro, Medesk, Dentalink) se promocionan, pero no hay una medición del mercado. **Lo medimos nosotros:
la pregunta va en la hoja de auditoría y la anotamos en `prospectos/clinicas-dentales.csv`.**

### 1.2 Reglas técnicas para los modos sincronizados
- Una interfaz "fuente de agenda" en el código (`ocupado(día)` y `crear(cita)`): el motor de `agenda.py` no cambia, solo
  se suman las horas ocupadas que vienen de afuera.
- **Re-verificar contra la fuente externa en el momento de reservar** (no solo cuando se consulta disponibilidad).
- Si la fuente externa no responde: no confirmar; pasar a pre-reserva y avisar a recepción.
- Registro de cada sincronización (qué se leyó y qué se escribió), para resolver reclamos.

### 1.3 Proceso de incorporación (se agrega al onboarding)
1. **Diagnóstico** (visita de cierre): dónde está la agenda, quién la maneja, cuántos profesionales y sillas, horarios de cada
   uno, duración real de cada servicio, festivos y vacaciones previstas.
2. **Carga inicial:** citas de los próximos 60 días (foto del cuaderno, Excel o exportación del software → las cargamos nosotros).
3. **Semana de sombra:** Sofía responde pero las citas quedan "por confirmar"; la recepción las aprueba. Revisión diaria juntos.
4. **Encendido:** Sofía confirma sola. Durante 2 semanas: comparar cada mañana la agenda del panel con lo que realmente pasó.
5. **Corte del papel:** acordado por escrito: desde la fecha X, la agenda oficial es el panel (modo A) o su sistema (modo B/C).

---

## 2. Factores que todavía no estamos teniendo en cuenta

### 2.1 El número de WhatsApp (el mayor riesgo de adopción)
- Las clínicas ya tienen un número que conocen sus pacientes, normalmente en **WhatsApp Business (app del celular)**. No van a
  cambiar de número.
- **Coexistencia:** Meta permite conectar ese mismo número a la Cloud API sin perder la app. Condiciones reportadas por
  proveedores (verificar con Meta al conectar el primer cliente): la cuenta debe tener antigüedad y buena calidad, hay que
  abrir la app al menos cada 13 días, y algunas funciones de la app dejan de funcionar en esos chats.
- **Consecuencia crítica:** la recepcionista seguirá escribiendo desde el celular. Si Sofía no se entera, **los dos responden
  al mismo paciente**. Hay que construir:
  - **Pausa automática:** si una persona del equipo escribe en un chat (Meta envía copia de esos mensajes), Sofía se calla en
    ese chat por X horas.
  - **Botón "tomar control / devolver a Sofía"** en el panel, y responder desde el panel.
- Fuera de las 24 h desde el último mensaje del paciente solo se pueden enviar **plantillas aprobadas** por Meta (con costo).
  Los recordatorios dependen de esto.

### 2.2 Cómo escriben los pacientes de verdad
- **Notas de voz:** en el mystery shopping varias clínicas respondieron con audios y los pacientes también los mandan. Hoy Sofía
  **no entiende audios** → transcribirlos (modelo de voz a texto) antes de pasarlos al asistente.
- Fotos (de la muela, de una orden, del carné), stickers, ubicación: responder con amabilidad y pasar a humano si es clínico.
- Preguntas muy colombianas que deben estar en la ficha de cada clínica: **¿atienden por EPS / prepagada / póliza (Sura,
  Colsanitas, Coomeva…)?**, formas de pago (Nequi, Daviplata, datáfono, crédito/financiación), parqueadero, si atienden niños.

### 2.3 La agenda real es más compleja que la demo
- **Festivos de Colombia** (18 al año, la mayoría se corren al lunes): hoy Sofía podría agendar un festivo. → Calendario de
  festivos automático; la clínica decide si abre.
- **Horario distinto por profesional** (el ortodoncista solo martes y jueves, la higienista medio día) y **vacaciones**.
- **Sillas/consultorios como recurso:** 3 odontólogos pero 2 sillas = máximo 2 citas a la vez.
- **Tratamientos por sesiones** (ortodoncia con controles mensuales, endodoncia en 2–3 citas, implantes con meses entre
  fases): agendar la siguiente sesión desde la cita actual.
- **Cupos de urgencia** reservados cada día y **tiempo de limpieza** entre pacientes.
- Pacientes nuevos vs. antiguos (la valoración de un nuevo dura más).

### 2.4 Inasistencias (el dolor que más plata le cuesta a la clínica)
- **Recordatorios automáticos** 24 h y 2 h antes, con botones "Confirmo / Necesito cambiarla" (plantillas de Meta).
- **Reprogramar** (hoy solo se puede cancelar) desde el chat y desde el panel.
- **Lista de espera:** si alguien cancela, ofrecer el cupo a los que pidieron una hora más cercana.
- Opcional más adelante: **abono** de la valoración por enlace de pago (Wompi, Bold, Nequi) para los que fallan seguido.

### 2.5 Personas y permisos
- Hoy hay **una sola clave por clínica**. Se necesitan **usuarios con rol**: dueño (todo, indicadores), recepción (agenda y
  chats), odontólogo (solo su agenda del día).
- **Bitácora de cambios:** quién creó, movió o canceló cada cita. Evita discusiones internas y nos protege a nosotros.
- **Miedo de la recepcionista** a ser reemplazada: presentarla como "la que supervisa a Sofía"; capacitarla primero y
  darle el control. Si ella no la adopta, el sistema fracasa aunque el dueño haya pagado.

### 2.6 Lo que el dueño necesita ver para seguir pagando (y para nuestra garantía)
- **Atribución:** de dónde vino cada paciente (anuncio de Meta "clic a WhatsApp" — Meta envía el anuncio de origen en el
  webhook —, orgánico, Google, recomendado). Sin esto **no podemos demostrar la garantía** de citas atribuibles.
- Embudo: conversaciones → interesados → citas → asistieron → (opcional) valor del tratamiento.
- **Resumen diario por WhatsApp al dueño** a las 7 a. m.: citas de hoy, casos pendientes, citas que agendó Sofía anoche.
- Exportar a Excel.

### 2.7 Que nunca se caiga (operación técnica)
- Servidor en VPS con HTTPS, **copia de seguridad diaria** de la base fuera del servidor, y prueba de restauración.
- **Monitoreo:** alerta a nosotros si el webhook deja de recibir mensajes, si el modelo de IA falla o si un caso lleva más
  de 30 min sin atender.
- Si la IA falla: mensaje amable de respaldo + aviso a recepción (ya existe) — y **nunca perder el mensaje del paciente**.
- **Llaves de API a nombre del negocio** (no la key personal del fundador), con tope de gasto por cliente.
- Configuración de la clínica (servicios, precios, horarios, preguntas frecuentes) **editable desde el panel**; hoy es un
  archivo YAML que solo nosotros podemos cambiar → cada cambio de precio sería una llamada a soporte.

### 2.8 Legal (Colombia)
- **Datos de salud = datos sensibles** (Ley 1581 de 2012). Necesitamos:
  - Aviso de privacidad corto en el primer mensaje de Sofía y autorización del paciente.
  - **Contrato de transmisión de datos**: la clínica es responsable; Vértice es encargado del tratamiento.
  - Decir que los mensajes se procesan con proveedores de IA en el exterior (transferencia internacional).
  - Procedimiento para que un paciente pida borrar sus datos.
- **No manejar historia clínica.** Nos quedamos en agenda y conversación; la historia clínica tiene sus propias reglas
  (Ley 2015 de 2020 y Resolución 866 de 2021 de interoperabilidad) y no queremos esa carga.
- Sofía ya tiene prohibido dar consejo médico y pasa a humano los temas clínicos; mantenerlo.
- Revisión con abogado antes del primer cliente pagando (ya presupuestado con el primer setup).

---

## 3. Prioridades propuestas

**P0 · Antes del primer cliente (sin esto no se debe encender en una clínica real)**
1. Festivos de Colombia + horario y vacaciones por profesional.
2. Pausa automática / tomar control del chat + responder desde el panel (coexistencia).
3. Notas de voz (transcripción).
4. Reprogramar citas (chat y panel).
5. Recordatorios con confirmación (plantillas de Meta).
6. Usuarios con rol + bitácora de cambios.
7. Modo pre-reserva (C) y semana de sombra.
8. VPS, respaldos diarios y monitoreo; aviso de privacidad.

**P1 · Primer mes con clientes**
Sincronización con Google Calendar · lista de espera · atribución de anuncios y embudo · resumen diario al dueño ·
configuración editable desde el panel · sillas como recurso · exportar a Excel.

**P2 · Cuando haya demanda real**
Conectores con software odontológico (según lo que usen nuestros clientes) · abonos con enlace de pago · tratamientos por
sesiones · reactivación de pacientes antiguos.

---

### Fuentes
- Coexistencia app + API: [360dialog](https://docs.360dialog.com/docs/hub/embedded-signup/whatsapp-coexistence),
  [Chatwerk](https://developer.chatwerk.de/docs/whatsapp-coexistence-business-app-api),
  [8x8](https://developer.8x8.com/connect/docs/whatsapp/whatsapp-business-app-coexistence),
  [Saysimple](https://www.saysimple.com/blog/whatsapp-coexistence-keep-app-add-automation)
- Software odontológico: [AgendaPro Colombia](https://agendapro.com/co/dental/software-odontologico),
  [Medesk](https://www.medesk.net/es/solutiones/odontologia), [Dentalink planes](https://web-es.softwaredentalink.com/en/planes)
- Historia clínica interoperable: [Resolución 866 de 2021 (MinSalud)](https://www.minsalud.gov.co/sites/rid/Lists/BibliotecaDigital/RIDE/DE/DIJ/resolucion-866-de-2021.pdf),
  [Impacto TIC](https://impactotic.co/historia-clinica-interoperable-en-colombia-avanza-en-normatividad-pero-falta-en-ejecucion/)

---

## 4. Estado de construcción (se actualiza en cada avance)

| P0 | Estado | Notas |
|---|---|---|
| 1. Festivos y horario/vacaciones por profesional | ✅ 2026-10-28 | `vertice/festivos.py`; horario propio por profesional; bloqueos de varios días; citas "por reprogramar" |
| 2. Pausa automática y tomar control del chat | ✅ 2026-10-28 | Ver detalle abajo |
| 3. Notas de voz | ✅ 2026-10-28 | Descarga de WhatsApp + transcripción (OpenAI `gpt-4o-mini-transcribe`, cambiable). Probado en vivo con audio sintético: 1–3 s, texto casi idéntico. **Falta probar con audios reales** (ruido, acentos, jerga) |
| 4. Reprogramar citas | ✅ 2026-10-28 | Atómico (la cita no se duplica ni choca consigo misma); herramienta de Sofía + botón en el panel + mensaje listo para avisar al paciente |
| 5. Recordatorios con confirmación | ✅ 2026-10-28 (código) | Falta: **aprobar la plantilla en Meta** (`plantillas/plantillas-whatsapp-meta.md`) y probar con un número real |
| 6. Usuarios con rol + bitácora | ✅ 2026-10-28 | Dueño / Recepción / Odontólogo con permisos que cumple el servidor; historial de quién hizo qué |
| 7. Modo pre-reserva | ⏳ | |
| 8. VPS, respaldos, monitoreo, aviso de privacidad | ⏳ | |

### P0-2 · cómo funciona
- Si una persona de la clínica escribe desde la app de WhatsApp Business, Meta avisa por el webhook `smb_message_echoes`;
  Sofía se pausa en ese chat `pausa_horas` (12 por defecto, configurable por clínica) y se reactiva sola. El equipo también puede
  **tomar control** o **devolver a Sofía** desde el panel, y **responder desde el panel**.
- Mientras Sofía está en pausa **no contesta**, pero los mensajes del paciente se guardan; el panel los marca "Esperando al equipo"
  (con contador en el menú) para que nadie quede sin respuesta.
- Al reactivarse, Sofía recibe una nota con lo que se habló mientras estaba en pausa, para no repetir ni contradecir.
- Respuestas desde el panel: WhatsApp solo permite texto libre dentro de las **24 h** posteriores al último mensaje del
  paciente; fuera de ese plazo el panel lo dice (hace falta una plantilla aprobada).
- Lo que envía Sofía se registra por su id para no confundirlo con un mensaje del equipo si Meta lo devuelve como eco.
- ⚠️ **Por confirmar con el primer número real:** el formato exacto del aviso `smb_message_echoes` (no pude consultar la
  documentación oficial desde este entorno). El lector es tolerante (acepta el destinatario en `to` o `recipient_id`), pero hay que
  probarlo con un mensaje real escrito desde el celular antes de dar por cerrado este punto.

### P0-3 · notas de voz
- Las notas de voz se descargan con el token de WhatsApp y se transcriben; Sofía recibe el texto marcado con 🎤 y está
  instruida para **confirmar nombre, fecha y hora** antes de agendar (la transcripción puede equivocarse).
- Si no se puede transcribir (audio muy largo —más de 5 MB—, falla de red o del proveedor) Sofía le pide al paciente que escriba.
- En un chat pausado (atiende el equipo) la nota de voz también se transcribe y se guarda para que el equipo la lea en el panel.
- La API de Claude no recibe audio: la transcripción siempre usa OpenAI (la misma `OPENAI_API_KEY`), aunque el motor de
  conversación sea Claude. Costo estimado: centavos de dólar por nota.

### P0-4 · reprogramar
- El horario viejo se libera y el nuevo se ocupa en una sola transacción; si el nuevo se ocupó, la cita queda donde estaba.
- Conserva al mismo odontólogo si puede; Sofía solo puede mover citas del propio paciente.
- Desde el panel, al mover una cita aparece un mensaje listo para avisar al paciente (enviar por WhatsApp si está dentro de las
  24 h, o copiar). **No se envía solo.**

### P0-5 · recordatorios con confirmación
- Ciclo en segundo plano cada 5 min (`VERTICE_RECORDATORIOS_SEGUNDOS`; apagable con `VERTICE_RECORDATORIOS=0`).
- Dos avisos por cita (día anterior y 2 h antes) con botones **Sí, confirmo / Necesito cambiarla**; solo de día (8 a. m.–8 p. m.),
  nunca repetidos, omite citas sin número de WhatsApp y las agendadas hace pocas horas.
- "Confirmo" → queda marcado en el panel (✓ en el calendario, conteo en el resumen) y se responde un agradecimiento fijo.
  "Necesito cambiarla" → Sofía ayuda a reprogramar con sus herramientas. Reprogramar reinicia la confirmación y los avisos.
- Si el paciente confirma con texto libre, Sofía usa la herramienta `confirmar_asistencia`.
- Los botones llegan del webhook como mensajes de tipo `button` con el `payload` que enviamos (`confirmar:<id>` / `cambiar:<id>`):
  **por confirmar con una plantilla real**, igual que el formato exacto de los envíos de plantilla.

### P0-6 · usuarios, roles e historial
| | Dueño | Recepción | Odontólogo |
|---|---|---|---|
| Resumen e indicadores | ✅ | ✅ | — |
| Agenda | completa, edita | completa, edita | **solo la suya**, marca asistió / no asistió |
| Conversaciones y casos | ✅ | ✅ | — |
| Equipo (crear personas, desactivar, restablecer clave) | ✅ | — | — |
| Historial de cambios | ✅ | — | — |

- Cada persona entra con **usuario y clave propios** (PBKDF2-SHA256 con sal; mínimo 8 caracteres con letras y números). El panel guarda solo una
  sesión que vence a las 12 h; cambiar o restablecer una clave, o desactivar a alguien, cierra sus sesiones al instante.
- Los permisos **los hace cumplir el servidor**, no solo la pantalla (hay pruebas que intentan lo prohibido con cada rol).
- **Historial:** cada cita creada, movida, cancelada o marcada, cada bloqueo, chat tomado, mensaje enviado, caso resuelto, persona agregada y
  cada ingreso (también los fallidos) queda con quién, cuándo y qué. También registra lo que hace Sofía (aparece como "asistente").
- Tras 5 intentos fallidos de un usuario, el ingreso se bloquea 10 minutos.
- No se puede desactivar al último dueño ni a uno mismo.
- **Acceso de soporte:** la clave de la clínica (`panel_clave` / `VERTICE_PANEL_CLAVE_<ID>`) sigue funcionando como acceso de Vértice con permisos de dueño y
  aparece en el historial como "Soporte Vértice" (el dueño ve cuándo entramos). Se usa para crear al primer dueño; también se puede con la línea de
  comandos: `python -m vertice.usuarios crear <clinica> <usuario> "<Nombre>" <rol> [profesional]`.
- **Pendiente para P0-8:** el límite de intentos del acceso de soporte (clave de la clínica) y por dirección IP debe hacerse en el servidor web de
  entrada (Caddy/Nginx) y todo debe ir por HTTPS: sin HTTPS las claves y sesiones viajan sin cifrar.
- La demo tiene un selector **"Ver como"** (dueño / recepción / odontólogo) para enseñar a cada tipo de persona lo que vería. Las personas de ejemplo
  usan la clave `Demo12345` solo en la base de demostración.

