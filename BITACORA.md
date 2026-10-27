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
