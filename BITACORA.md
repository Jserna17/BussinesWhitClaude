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
