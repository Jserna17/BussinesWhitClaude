# 📓 Bitácora de sesiones

> Diario cronológico. Cada sesión agrega una entrada al final. No se editan entradas antiguas.

---

## Sesión #1 — 2026-10-27 — Fundación

**Pedido del fundador:** construir un negocio y escalarlo hasta tener clientes recurrentes;
Claude se encarga de adquisición, marketing, soluciones y administración; investigar los mejores
negocios actuales, habilidades, skills, conectores y herramientas; documentarlo todo y crear una memoria.

**Qué se hizo:**
- Investigación web: modelos de ingreso recurrente 2026, precios de agencias de automatización IA,
  frameworks de Hormozi ($100M Offers / $100M Leads), conectores MCP para negocio, mercado de
  agentes IA en WhatsApp en LATAM y cambios de precios de Meta.
- Se eligió (propuesta) el modelo: **Recepcionista IA 24/7 por WhatsApp** para clínicas estéticas/odontológicas.
- Se crearon: `MEMORIA.md`, `CLAUDE.md`, `README.md`, `docs/01` a `docs/08`, y `plantillas/`.
- Inventario de herramientas en la sesión: skills de marketing (campaign-plan, email-sequence,
  seo-audit, competitive-brief, content-creation…), skills creativas (ads, UGC, video), conectores
  activos (Shopify, Canva, Notion, Google Drive, Higgsfield, GitHub). Conectores de HubSpot, Gmail,
  Calendar, Slack, Klaviyo, Ahrefs, Similarweb fallaron al conectar (error de proxy 403) — reintentar.

**Decisiones:** ver `MEMORIA.md` §6.

**Próximos pasos:**
1. Fundador responde preguntas abiertas (`MEMORIA.md` §7).
2. Construir demo del agente para el nicho.
3. Armar lista de 200 prospectos y lanzar outreach (semana 1–2 del plan de 90 días).

---

## Sesión #2 — 2026-10-27 — Pereira, presupuesto y ampliación del servicio

**Respuestas del fundador:**
- Empezamos en **Colombia, ciudad de Pereira**.
- Tiempo disponible: "unas dos horas en total" (se asume 2 h/día; pendiente confirmar).
- Conoce a algunos dueños de negocios.
- Le gusta el modelo (ya lo tenía en mente) y quiere ampliarlo a **automatizar otros procesos de negocios
  locales**, no solo WhatsApp para clínicas.
- Pidió estimar el presupuesto y en qué se invierte.

**Qué se hizo:**
- Investigación de tarifas de WhatsApp API en Colombia (oct-2026): servicio/utilidad ~USD 0,0008/mensaje,
  marketing ~USD 0,0125 → costo de mensajería casi insignificante.
- Nuevo `docs/09-presupuesto.md`: mínimo ~COP 950.000, recomendado ~COP 2.000.000 para 90 días.
- Nuevo `docs/10-catalogo-servicios-automatizacion.md`: 12 módulos, paquetes por vertical de Pereira,
  precios en COP (450k / 850k / 1,5M mensuales).
- `docs/08-plan-90-dias.md` reescrito para Pereira y 2 h/día (meta: 8 clientes, ~COP 5 M MRR al día 90).
- `MEMORIA.md` actualizada (ubicación, modelo ampliado, precios COP, recursos, metas, decisiones).

**Próximos pasos:**
1. Fundador confirma horas (¿día o semana?) y presupuesto.
2. Fundador envía lista de sus contactos dueños de negocio → Claude redacta un mensaje personalizado para cada uno.
3. Claude propone nombres de marca y construye la demo.

---

## Sesión #3 — 2026-10-27 — Presupuesto de COP 500.000, stack técnico, marca y adquisición sin red

**Respuestas del fundador:**
- 2 horas **al día** (confirmado).
- Puede invertir **COP 500.000**.
- Pide analizar si n8n sigue siendo lo más viable para montar el agente y cómo se montan hoy.
- No tiene red cálida: conoce negocios donde ha sido cliente, pero sin relación con los dueños.
- Pide propuestas de nombre de marca.

**Qué se hizo:**
- Investigación de cómo se construyen hoy los agentes de WhatsApp: n8n quedó como herramienta de
  "control para desarrolladores" y back-office; el mercado usa plataformas gestionadas (Botpress, Cliengo,
  Wati, Respond.io…, USD 15–113/cliente/mes) o agentes con SDK de modelos. Política de Meta: desde
  15-ene-2026 se prohíben chatbots de propósito general en la API; los asistentes de negocio están permitidos.
- **Decisión:** agente propio multi-cliente con Claude API + Cloud API de Meta (`docs/11`).
- Nombres generados con el conector de Shopify + dominios verificados: recomendado **Clara**
  (`atiendeclara.com` disponible); alternativas Tinto IA, Brío, Atiendo (`docs/12`).
- Presupuesto rehecho a COP 500.000 (`docs/09`).
- Adquisición "semi-cálida" presencial + guion de visita (`docs/03` §2b, `plantillas/guiones-outreach.md`).
- Plan de 90 días y `MEMORIA.md` actualizados.

**Próximos pasos:**
1. Fundador elige nombre y registra el dominio.
2. Fundador lista 15–20 negocios donde ha sido cliente.
3. Fundador crea cuenta de Meta for Developers (Claude le da la guía paso a paso).
4. Claude empieza a construir el agente "Clara" y la Clínica Demo.

---

## Sesión #4 — 2026-10-27 — Marca profesional y base de prospectos

**Pedido del fundador:** no le gusta "Clara"; quiere un nombre que suene a agencia profesional. Pide que
Claude busque en Google Maps negocios de Pereira y Dosquebradas con toda su información de contacto.

**Qué se hizo:**
- Nombres profesionales generados y dominios verificados (conector Shopify). Recomendado **Vértice
  Automatización** (`verticeautomatizacion.com` disponible); alternativas Axioma (`axiomaautomation.com`),
  Prisma (`prismaautomatizacion.com`). `docs/12-marca.md` v2.
- Google Maps y la descarga directa de páginas están bloqueados por el proxy del entorno → se usó búsqueda
  web sobre sitios oficiales, redes y directorios.
- Base de **62 prospectos** (`prospectos/prospectos-pereira-dosquebradas.csv`): 18 odontología, 12 medicina
  estética/dermatología/cirugía plástica, 8 estética/spa, 9 inmobiliarias, 6 veterinarias, 6 talleres,
  3 gimnasios. 39 con celular/WhatsApp (prioridad A). Cada fila con su fuente. Top 15 y ruta de visitas
  (Megacentro Pinares, Edificio Oval) en `prospectos/README.md`.

**Próximos pasos:**
1. Fundador aprueba nombre y registra dominio.
2. Fundador marca en qué negocios ha sido cliente.
3. Mystery shopping a los 15 primeros (WhatsApp fuera de horario) y primeras visitas en Megacentro Pinares.
4. Claude construye el agente demo.

---

## Sesión #5 — 2026-10-27 — Marca Vértice y asistente demo v0.1

**Pedido del fundador:** le gusta Vértice; empezar a construir el asistente demo.

**Qué se hizo:**
- Marca **Vértice** confirmada (MEMORIA §7).
- Código en `agente/`: Python + FastAPI + SDK de Anthropic 2.3 + Cloud API de WhatsApp.
  - Herramientas estrictas: consultar_disponibilidad, agendar_cita, ver_mis_citas, cancelar_cita,
    registrar_interes, pasar_a_humano (avisa al dueño por WhatsApp).
  - Multi-negocio por YAML; demos `clinica-demo` (Sofía) y `taller-demo` (Max).
  - Caché del prompt (prompt fijo por negocio, fecha en cada mensaje), respaldo `fallbacks: "default"`
    (omitido en Haiku), historial completo con reinicio a las 24 h, idempotencia del webhook y firma de Meta.
  - Simulador en terminal (`python -m vertice.chat clinica-demo`).
- Verificación: 12 pruebas sin conexión OK + prueba de punta a punta con el SDK real contra un servidor
  local que imita la API (peticiones bien formadas; bloques de razonamiento y herramientas ida y vuelta).
- **No probado aún contra la API real** (no hay API key en el entorno) ni contra Meta.

**Próximos pasos:**
1. Fundador crea API key en console.anthropic.com y prueba el simulador.
2. Fundador crea app en Meta for Developers (número de prueba) → conectar webhook.
3. Comparar Haiku 5.5 vs Opus 5.5 en 20 conversaciones de prueba y fijar el modelo.
4. Grabar video demo de 60 s para las visitas.

---

## Sesión #6 — 2026-10-27 — Motor OpenAI para pruebas; dominio pospuesto

**Pedido del fundador:** usar por ahora su API key de ChatGPT (OpenAI) para probar; no comprar el dominio
hasta vender.

**Qué se hizo:**
- `agente/vertice/motores.py`: motores intercambiables `MotorClaude` y `MotorOpenAI` (Chat Completions con
  herramientas `strict`), elegidos con `VERTICE_PROVEEDOR`. Modelo OpenAI por defecto `gpt-5-mini`
  (configurable con `VERTICE_MODELO_OPENAI`). Historial guardado por proveedor.
- 13 pruebas OK + prueba de punta a punta con los SDK reales de OpenAI y de Anthropic contra servidores
  locales simulados.
- `api.openai.com` está bloqueado por la red del entorno de Claude → la prueba en vivo queda pendiente
  (opciones: PC del fundador, o habilitar el dominio y guardar la key como secreto del entorno).
- Dominio pospuesto hasta la primera venta (MEMORIA §7, presupuesto y plan actualizados).

**Próximos pasos:**
1. Fundador elige cómo probar en vivo y corre 20 conversaciones de prueba.
2. Conectar el número de prueba de Meta.
3. Video demo de 60 s y primeras visitas (Megacentro Pinares).

---

## Sesión #7 — 2026-10-27 — Foco en clínicas dentales y Sistema de Pacientes Nuevos

**Pedido del fundador:** no ha sido cliente de ninguna clínica; empezar con clínicas dentales (las más
numerosas y que más necesitan pacientes) y crear un sistema de adquisición de clientes para ellas, porque
muchas no hacen anuncios ni tienen buena presencia en redes.

**Qué se hizo:**
- Investigación: benchmarks de anuncios dentales (EE. UU.: ~USD 77 por lead en Meta, el sector más caro;
  sin datos públicos de Colombia), modelos de agencias dentales (gestión + IA de respuesta inmediata),
  normas: Estatuto del Consumidor/SIC, habilitación REPS (alertas de Supersalud), políticas de Meta para salud
  (antes/después con reglas poco claras en 2026).
- `docs/13-sistema-pacientes-dentales.md`: oferta "Sistema Vértice de Pacientes Nuevos" (anuncios clic a
  WhatsApp + asistente IA + Google + contenido + reactivación + reporte), planes 450k / 1,5 M / 2,2 M al mes,
  garantía condicionada, matemática para la clínica (hipótesis 🧪), cumplimiento y operación.
- `plantillas/auditoria-pacientes-perdidos.md`: auditoría gratis con puntaje 0–100, formato de una página y
  guion de visita en frío.
- `plantillas/anuncios-dentales.md`: 6 anuncios clic a WhatsApp + configuración + lista de verificación.
- Prospectos: +11 clínicas dentales; nueva lista de trabajo `prospectos/clinicas-dentales.csv` (29 clínicas,
  14 con WhatsApp) con columnas de auditoría.
- MEMORIA, plan de 90 días y README actualizados.

**Próximos pasos:**
1. Fundador aprueba precios y garantía del Sistema de Pacientes.
2. Auditar 10 clínicas (mystery shopping a las 7–8 p. m. + Google + Instagram + Biblioteca de anuncios).
3. Probar la demo en vivo (pendiente elegir: PC del fundador o habilitar `api.openai.com` en el entorno).
4. Primeras visitas en Megacentro Pinares con la auditoría impresa.

---

## Sesión #8 — 2026-10-27 — Precios aprobados y pruebas en vivo preparadas

**Pedido del fundador:** aprueba los precios; quiere probar habilitando OpenAI en el entorno de Claude.

**Qué se hizo:**
- Precios y garantía del Sistema de Pacientes aprobados (MEMORIA §7).
- Verificado: en esta sesión aún no hay `OPENAI_API_KEY` y `api.openai.com` sigue bloqueado.
- `agente/vertice/pruebas_vivo.py`: batería de 20 conversaciones (precios, agendar, domingo cerrado, fuera de
  tema, urgencia, cancelar, financiación, EPS, descuento, usted, cliente molesto, ¿robot?, manipulación,
  sin nombre, prospecto, pregunta médica, reprogramar…) con verificaciones automáticas (cita creada, pasó a
  humano, prospecto, palabras clave) y transcripciones en `agente/resultados/`. Probada contra un servidor
  local simulado; 13 pruebas unitarias OK.

**Pasos para el fundador (habilitar OpenAI):**
1. En claude.ai/code, menú del entorno en la barra de título de la sesión → **Edit**.
2. *Network access* → agregar `api.openai.com` en dominios permitidos (dejar marcada la casilla de gestores de paquetes).
3. Agregar la key como secreto / variable de entorno con el nombre **`OPENAI_API_KEY`** (no pegarla en el chat).
4. Abrir una sesión nueva y escribir: "Corre las pruebas en vivo".

**Próximos pasos:**
1. Correr la batería, leer transcripciones y ajustar prompt/negocio demo.
2. Auditar las primeras 10 clínicas y primeras visitas en Megacentro Pinares.

---

## Sesión #9 — 2026-10-27 — Explicación simple para habilitar OpenAI + Sofía en ChatGPT

**Pedido del fundador:** no entendió los pasos para habilitar OpenAI en el entorno.

**Qué se hizo:**
- Explicación paso a paso en lenguaje simple (qué es y dónde se hace).
- Alternativa sin configurar nada: `plantillas/sofia-para-chatgpt.md` — prompt de Sofía para pegar en
  chatgpt.com y ver cómo responde (sin agenda real), útil también para mostrar en visitas.

**Próximos pasos:** el fundador prueba Sofía en ChatGPT y/o habilita el entorno con ayuda; seguir con auditorías.

---

## Sesión #10 — 2026-10-27 — Primera prueba en vivo con OpenAI

**Pedido del fundador:** habilitó OpenAI en el entorno (red + secreto `OPENAI_API_KEY`).

**Qué se hizo:**
- Verificado: clave válida, 134 modelos disponibles; elegido `gpt-5.4-mini` (nuevo default del motor OpenAI).
- Batería de 20 conversaciones en vivo (Clínica Dental Sonríe / Sofía). Errores encontrados y corregidos:
  1. Pedían cita "en la tarde" y solo veía horarios de la mañana (la herramienta cortaba en 12 horarios) →
     ahora devuelve horarios separados en mañana y tarde.
  2. Ofrecía "recordarle" la cita (todavía no existe) → regla: no ofrecer acciones sin herramienta.
  3. Ofrecía agendar blanqueamiento directo aunque requiere valoración → nuevo campo `requiere_valoracion`
     en los servicios; la herramienta lo bloquea y propone la valoración (regla en el código, no solo en el prompt).
  4. Respondía "¡Claro!" ante un descuento no autorizado → regla de no confirmar descuentos/excepciones.
  5. Demo con precios de ortodoncia de inicio y valoración de ortodoncia.
- Resultado final: 19/20 + 1 falso negativo de la verificación (escenario 18 sin precio porque no lo pidieron;
  verificación ajustada). Transcripción en `agente/resultados/pruebas-openai-20261027-221102.md`.
- 14 pruebas unitarias OK.

**Próximos pasos:**
1. Conectar el número de prueba de Meta para usar a Sofía en un WhatsApp real (demo en el celular).
2. Auditorías de las primeras 10 clínicas y visitas en Megacentro Pinares.

---

## Sesión #11 — 2026-10-27 — Página demo de Sofía

**Pedido del fundador:** ¿cómo ve la interfaz o lo que Claude estaba ejecutando?

**Qué se hizo:**
- Explicado: lo ejecutado eran comandos en el computador en la nube de Claude (sin interfaz); los resultados
  quedan en archivos como `agente/resultados/…md`.
- Página web demo publicada (privada): https://claude.ai/artifact/QNoA7pa8cbFn5WqLEwce34 — chat estilo
  WhatsApp con Sofía (modelo de Claude vía la cuenta de quien abre la página, nivel "quick"), agenda real dentro
  de la página con las mismas reglas que el sistema (horario, 30 min, 1 h de anticipación, requiere valoración),
  panel de citas / avisos al equipo / interesados, botones de preguntas rápidas y personalización del nombre de la
  clínica. Sintaxis del script verificada; la conversación no se pudo probar desde el entorno (requiere abrirla en claude.ai).

**Próximos pasos:** el fundador la prueba en su celular y la usa en las primeras visitas.

---

## Sesión #12 — 2026-10-28 — Lista para mystery shopping

**Pedido del fundador:** la lista de clínicas para escribirles en ese momento (~9:30 p. m., fuera de horario).
**Qué se hizo:** se le entregaron las 13 clínicas dentales con WhatsApp de `prospectos/clinicas-dentales.csv` y el
mensaje de paciente para la auditoría. **Próximo paso:** el fundador anota hora de envío y de respuesta de cada una;
Claude arma las hojas de auditoría.

---

## Sesión #13 — 2026-10-27 (noche) — Resultados del mystery shopping #1

**Qué pasó:** el fundador escribió como paciente a ~20 clínicas entre 9:37 y 10:19 p. m. y compartió capturas.
**Resultados:** solo 3 respondieron algo útil esa noche; ninguna agendó. Ortocentro tiene un asistente IA ("Ana",
sobre Meta) que responde al instante pero no ve la agenda, pide cédula y repite "una asesora te contactará". La
auxiliar de la Dra. Calderón responde con plantillas y deja todo para "mañana". Varias no entregan o tienen ausencia.
**Qué se hizo:** `prospectos/mystery-shopping-2026-10-27.md` (tabla, aprendizajes y ángulo de venta); CSV de
prospectos actualizados (6 números nuevos, etapa "Mystery shop", columna respuesta_whatsapp); MEMORIA actualizada.
**Próximos pasos:** mañana a mediodía el fundador revisa quién respondió y a qué hora; Claude arma las hojas de
auditoría y la ruta de visitas (prioridad: Megacentro Pinares — PB Odontología, Dr. Orozco — y Ortocentro).

---

## Sesión #14 — 2026-10-28 — Primera respuesta del día siguiente

El fundador reporta que una clínica le respondió a las 6:00 a. m. en punto (≈8 h después). Pendiente: qué clínica y
qué dijo (captura). Registrado en `prospectos/mystery-shopping-2026-10-27.md`.

---

## Sesión #15 — 2026-10-28 — Respuestas del día siguiente

**Qué pasó:** capturas a la 1:39 p. m. 16 de ~20 clínicas respondieron entre 7:56 y 11:38 a. m. (mediana ≈ 10,8 h
después del mensaje de las ~10 p. m.); casi todas personas (notas de voz de hasta 1:41 min, ofertas de hora, precios
de valoración $90.000–$97.000). DentalEs ofreció cita para el viernes 2:30 p. m. Sin respuesta: Proced, Odontología y
Sonrisa, @Richo5555.
**Qué se hizo:** tabla completa en `prospectos/mystery-shopping-2026-10-27.md`, CSV actualizados, MEMORIA (nuevo dato
de venta: espera típica ~11 h).
**Próximos pasos:** cerrar con amabilidad los chats con cita ofrecida; elegir 5 clínicas para visitar; hojas de auditoría.

---

## Sesión #16 — 2026-10-28 — Agenda sin cruces y panel del médico

**Pedido del fundador:** antes de las visitas, armar todo el sistema de agendamiento sin cruces (que el agente
sepa qué está disponible) y un dashboard para el médico con datos y las conversaciones.

**Qué se hizo:**
- `agente/vertice/agenda.py`: motor único de agenda (asistente + panel): varios profesionales con sus servicios,
  horario partido (almuerzo), bloqueos generales o por profesional, intervalo y anticipación configurables.
- `db.py`: reservas re-validadas dentro de `BEGIN IMMEDIATE` (sin dobles reservas aunque haya varios procesos),
  estados asistió/no asistió, origen (asistente/panel), bloqueos, casos resueltos, hora de Bogotá, migración automática.
- `panel.py` + `panel.html` + `transcripcion.py`: panel web con login por clínica; resumen con 8 indicadores y
  gráfica; agenda semanal con acciones; nueva cita y bloqueos; conversaciones legibles con acciones del asistente;
  casos e interesados.
- Errores reales encontrados con la batería en vivo y corregidos: el asistente agendaba con nombre "Cliente"
  (ahora el código exige nombre y apellido); pasaba al equipo cuando pedían "esta semana" (ahora ofrece 2–3
  horarios); mostraba IDs internos; hora UTC en registros.
- Demo `clinica-demo` con 2 odontólogos y almuerzo; `datos_demo.py` para poblar el panel.
- Verificación: 22 pruebas (incluye 20 reservas simultáneas, repetida 15 veces sin fallas), batería en vivo
  OpenAI 20/20, capturas del panel sin errores de consola (`demo/capturas/`).

**Próximos pasos:** publicar en un VPS (webhook + panel); número de prueba de Meta; hojas de auditoría y visitas.

---

## Sesión #17 — 2026-10-28 — Panel visible desde el equipo del fundador

**Pedido:** ver el sistema en su propio equipo. No tiene carpetas conectadas por Remote Control.
**Qué se hizo:** `vertice/exportar_demo.py` genera una copia del panel que funciona sola en el navegador (foto de
los datos del servidor + simulador de la API: agenda sin cruces, bloqueos, estados). Publicada (privada):
https://claude.ai/artifact/WaS72eAXnZiXdQcAqS82sR. Probada con navegador automático: agendar quita la hora de las
libres, sin errores. Panel con modo claro/oscuro según elección del usuario.
**Próximo paso:** si quiere correr el sistema completo en su PC, guía según su sistema operativo; luego VPS + Meta.

---

## Sesión #18 — 2026-10-28 — Rediseño del panel del médico

**Pedido:** interfaz limpia, profesional y moderna, reorganizada visualmente.
**Qué se hizo (`agente/vertice/panel.html`):**
- Navegación lateral con íconos y ficha de la clínica (en celular pasa a barra superior compacta).
- Resumen en dos bloques: **Hoy** (citas de hoy, próximas, casos abiertos, interesados) y **Lo que hizo el
  asistente** (mensajes, % fuera de horario, citas agendadas por Sofía, inasistencia) con selector 7/30 días;
  gráfica, tarjeta "Requiere atención" y próximas citas en línea de tiempo.
- Agenda tipo calendario: horas en el eje vertical, un carril por odontólogo, almuerzo y horas cerradas rayadas,
  línea de "ahora", vista Semana/Día (Día por defecto en celular). Detalle de cita, nueva cita (botones de horas
  libres) y bloqueos en un panel lateral.
- Conversaciones en tres columnas: lista con buscador, chat y ficha del paciente con las acciones de Sofía.
- **Error real encontrado:** el panel nuevo pide varios datos a la vez y la base fallaba con lecturas en paralelo
  (error 500). Arreglado: toda consulta toma el candado (`db.py`). Prueba nueva con 8 hilos (falla sin el arreglo).
- Datos de ejemplo con nombres en vez de "#1"; demo regenerada y re-publicada (mismo enlace). 23 pruebas OK.
- Capturas nuevas en `demo/capturas/` (incluye detalle de cita, nueva cita, modo oscuro y celular).

**Próximos pasos:** hojas de auditoría para las 5 clínicas prioritarias y visitas; luego VPS + Meta.

---

## Sesión #19 — 2026-10-28 — Integración de agenda y riesgos de operación

**Pregunta del fundador:** qué falta al panel para garantizar el funcionamiento, cómo incorporar la agenda de un médico
que se vuelva cliente y qué factores no estamos viendo.
**Qué se hizo:** `docs/14-integracion-agenda-y-operacion.md`: regla de una sola agenda; tres modos de integración
(A Vértice es la agenda, B sincronizada, C pre-reserva); proceso de incorporación con semana de sombra; riesgos no
cubiertos (número de WhatsApp y coexistencia, choque bot/recepcionista, notas de voz, festivos, horario por profesional,
sillas, recordatorios, reprogramar, roles, atribución para la garantía, respaldos/monitoreo, Ley 1581). Prioridades
P0/P1/P2. Checklist de onboarding actualizado; la pregunta "¿dónde llevan la agenda?" pasa a la visita.
**Próximo paso:** aprobación del fundador para construir los P0 en orden.

---

## Sesión #20 — 2026-10-28 — P0-1: festivos y horarios por profesional

**Pedido:** construir lo imprescindible de `docs/14` en orden.
**Hecho (P0-1):**
- `vertice/festivos.py`: festivos de Colombia calculados para cualquier año (Ley Emiliani + Semana Santa); verificado contra el calendario 2026 (18 festivos).
- Horario propio por profesional (`horario` dentro de `profesionales`) y `abre_festivos` por clínica; el motor de agenda ofrece solo horas en que cada odontólogo atiende. Demo: el Dr. Andrés solo martes, jueves y viernes tarde.
- El prompt de Sofía ahora muestra bien el horario partido (antes mostraba solo la primera franja) y los días de cada profesional; avisa si el día es festivo.
- Panel: festivos marcados, carriles con el horario de cada odontólogo, bloqueos de varios días (vacaciones, incapacidad), y las citas que quedan dentro de un festivo o bloqueo se marcan "por reprogramar" (el bloqueo no las cancela, avisa cuáles son).
- Corregido de paso: la base devolvía la hora real del servidor en las pruebas; ahora las pruebas usan reloj fijo. 28 pruebas OK.
- Demo publicada de nuevo (misma URL, versión 3).
**Siguiente:** P0-2 pausa automática y tomar control del chat.

### P0-2 (misma sesión)
- Webhook `smb_message_echoes`: si el equipo escribe desde el celular, Sofía se pausa; mensajes del paciente en pausa se guardan y quedan "esperando al equipo".
- Panel: Tomar control / Devolver a Sofía, caja para responder como la clínica (ventana de 24 h de WhatsApp), mensajes del equipo en el chat, contador en el menú.
- Al reactivarse, Sofía recibe una nota con lo que habló el equipo. `enviar_texto` devuelve el id para no confundir sus mensajes con ecos.
- 31 pruebas OK; demo republicada. **Por confirmar:** formato real del eco con un número conectado.
**Siguiente:** P0-3 notas de voz.

### P0-3 y P0-4 (misma sesión)
- **Notas de voz:** `vertice/voz.py` + descarga de WhatsApp; Sofía recibe el texto con 🎤 y confirma datos antes de agendar. Prueba real con audio sintético en español: 1–3 s, transcripción casi idéntica. Falla de transcripción → pide escribir.
- **Reprogramar:** transacción atómica en la base, herramienta `reprogramar_cita`, endpoint y botón en el panel con mensaje listo para avisar al paciente; la demo lo simula.
- 40 pruebas OK. Demo republicada.
**Siguiente:** P0-5 recordatorios con confirmación (plantillas de Meta).

### P0-5 (misma sesión)
- `vertice/recordatorios.py`: ciclo de recordatorios con plantilla de Meta y botones; reglas de horario, sin duplicados, reintento si falla; arranca con el servidor.
- Botones del paciente: "Confirmo" queda en el panel; "Necesito cambiarla" lo atiende Sofía. Herramienta `confirmar_asistencia` para respuestas en texto.
- Panel: ✓ / ↺ en el calendario, estado y recordatorios enviados en el detalle de la cita, conteo en el resumen.
- Guía `plantillas/plantillas-whatsapp-meta.md` con la plantilla exacta que hay que aprobar (acción del fundador).
- Error propio corregido: el panel mostraba "null" en el detalle de las citas (elementos opcionales del panel lateral) desde P0-1.
- 48 pruebas OK; demo republicada.
**Siguiente:** P0-6 usuarios con rol y bitácora de cambios.

