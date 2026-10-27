# 11 · ¿Cómo se montan hoy los agentes de WhatsApp? ¿Sigue siendo n8n la mejor opción?

> Investigación del 2026-10-27. Fuentes mayormente de proveedores (comparativas con sesgo comercial).

## 1. Respuesta corta

**n8n ya no es la mejor base para el agente conversacional en nuestro caso.** Sigue vigente y muy usado,
pero hoy se posiciona como la herramienta de "control para desarrolladores" e integraciones de back-office,
y para WhatsApp exige cablear a mano la Cloud API de Meta. Para el **agente que conversa** el mercado se movió a:

1. **Plataformas gestionadas de agentes** (Botpress, Voiceflow, Cliengo, Kommo, Wati, Respond.io, Leadsales…): rápidas, pero cobran por cliente/mes.
2. **Agentes construidos con el SDK de un modelo** (Claude API con herramientas, Claude Agent SDK / Managed Agents, OpenAI Agents…), conectados directo a la Cloud API de Meta: más baratos y flexibles, requieren código.
3. **Híbrido** (lo más recomendado en las comparativas): el agente atiende la conversación y n8n/Make mueve datos y dispara tareas de back-office.

**Nuestra decisión:** opción 2 — **agente propio con la Claude API + Cloud API de Meta**, construido y
mantenido por Claude (Claude Code). n8n queda como herramienta opcional para integraciones puntuales.
Plataformas gestionadas solo como plan B si el cliente exige panel/bandeja propia.

## 2. Comparativa

| Criterio | n8n (autohospedado) | Plataforma gestionada (Botpress, Cliengo, Wati…) | **Agente propio (Claude API + Cloud API Meta)** ⭐ |
|---|---|---|---|
| Costo fijo por cliente | ~0 (servidor compartido) | ~USD 15–113/mes por cuenta (Callbell/Manychat ~15, Wati ~49, Respond.io ~79, Trengo ~113) + posible recargo por mensaje | ~0 (un solo servicio para todos los clientes) |
| Costo variable | Tokens del LLM | Tokens/“créditos IA” con recargo | Solo tokens de Claude + mensajes de Meta |
| Margen con plan de COP 450.000 (~USD 112) | Alto | **Bajo o negativo** en planes caros | **Muy alto (~90 %)** |
| Velocidad para lanzar | Media | **Muy alta** | Media (Claude lo construye; ~1–2 semanas la primera vez) |
| Multi-cliente (1 sistema, N negocios) | Torpe (un flujo por cliente, mantenimiento manual) | Una cuenta por cliente | **Nativo**: misma base de código, configuración por cliente |
| Calidad conversacional / memoria | Aceptable, frágil en conversaciones largas | Buena | **La mejor**: control total del prompt, herramientas y memoria |
| Panel para el cliente (bandeja humana) | No trae | **Sí** | Hay que construirlo (o usar WhatsApp Business App en coexistencia) |
| Dependencia de terceros | Baja | Alta (precios y reglas del proveedor) | Baja |
| Quién lo mantiene | Persona técnica | Cualquiera | Claude |

**Por qué gana el agente propio para nosotros:** nuestra ventaja competitiva es que Claude programa,
prueba y mantiene el sistema. Con un presupuesto de COP 500.000 y precios de COP 450.000/mes por cliente,
no podemos pagar USD 49–79 por cliente a una plataforma sin perder la mitad del margen.

## 3. Arquitectura elegida

```
Cliente final ─WhatsApp─▶ Cloud API de Meta (webhook)
                                 │
                                 ▼
                 Servicio "Clara" (Python o Node, un VPS barato)
                 ├─ Identifica a qué negocio pertenece el número
                 ├─ Carga su configuración (FAQ, precios, horarios, tono, reglas)
                 ├─ Llama a la Claude API con herramientas (tool use):
                 │     • consultar_disponibilidad / agendar_cita  → Google Calendar
                 │     • registrar_lead / actualizar_cliente     → Google Sheets (CRM)
                 │     • pasar_a_humano                           → alerta al dueño por WhatsApp
                 ├─ Guarda historial de la conversación (SQLite/Postgres)
                 └─ Tareas programadas: recordatorios, reactivación, reporte semanal
```

- **Modelo:** el modelo pequeño/rápido de Claude para la mayoría de mensajes (barato) y uno superior solo
  para casos complejos. Usar *prompt caching* para la base de conocimiento de cada negocio (abarata mucho).
- **Claude Managed Agents** (beta desde abril 2026, ~USD 0,08 por hora de sesión activa + tokens): pensado para
  agentes largos con sandbox; para chats cortos de WhatsApp es innecesario y más caro. No lo usamos por ahora.
- **Hosting:** un VPS pequeño (~COP 20.000–30.000/mes) sirve para decenas de clientes.
- **n8n (opcional):** si un cliente necesita conectar un software raro (facturación, POS), un flujo de n8n en el
  mismo VPS hace de puente.

## 4. Reglas de Meta que condicionan el diseño (importante)

- Desde el **15 de enero de 2026** Meta **prohíbe chatbots de IA de propósito general** (tipo ChatGPT) en la
  WhatsApp Business API. **Sí están permitidos los asistentes de IA de un negocio** (atención, citas, pedidos,
  recordatorios). ➜ Nuestro agente debe limitarse al negocio del cliente y rechazar temas ajenos.
- Mensajes iniciados por la empresa (recordatorios, reactivación) requieren **plantillas aprobadas** por Meta.
- Cada número requiere una cuenta de Meta Business (idealmente verificada) del cliente.
- Para pruebas, Meta da un **número de prueba gratuito** en la Cloud API → la demo no necesita gastar.
- La "coexistencia" permite usar el mismo número en la app de WhatsApp Business y en la API, para que el
  equipo del cliente siga respondiendo manualmente cuando el agente pasa a humano (verificar disponibilidad
  al configurar cada cliente).

## 5. Plan de construcción (Claude)

| Paso | Entregable | Tiempo estimado |
|---|---|---|
| 1 | App en Meta for Developers + número de prueba | 1 día (requiere que el fundador cree la cuenta) |
| 2 | Servicio webhook + Claude API + historial | 2–3 días |
| 3 | Herramientas: Google Calendar y Google Sheets | 2 días |
| 4 | Configuración multi-negocio (un archivo por cliente) + "Clínica Demo" y "Taller Demo" | 1–2 días |
| 5 | Pruebas con 30 conversaciones difíciles + video demo | 1 día |
| 6 | Despliegue en VPS, monitoreo y alertas | 1 día |

## 6. Plan B
Si el agente propio se retrasa o un cliente quiere un panel completo con bandeja de agentes humanos:
usar una plataforma con plan económico y API (p. ej. Wati, Kommo o Leadsales) para ese cliente y
**subir su precio** para cubrir el costo de la plataforma.

## Fuentes
- [Visito — n8n alternatives for WhatsApp AI agents 2026](https://www.visitoai.com/blog/n8n-alternatives-ai-agents-for-whatsapp-business)
- [Botpress — Best n8n alternatives 2026](https://botpress.com/blog/n8n-alternatives)
- [Composio — n8n alternatives tested 2026](https://composio.dev/content/top-n8n-alternatives)
- [CodeWords — Top tools for WhatsApp agents 2026](https://www.codewords.ai/blog/top-5-tools-for-building-whatsapp-agents-2026)
- [YourGPT — n8n alternatives for AI agents](https://yourgpt.ai/blog/comparison/best-n8n-alternatives-for-ai-agents)
- [Heym — Self-hosted n8n alternatives 2026](https://heym.run/blog/best-n8n-alternatives-2026)
- [Coworker — n8n alternatives](https://coworker.ai/blog/n8n-alternatives)
- [Anthropic — Managed Agents docs](https://platform.claude.com/docs/en/managed-agents/)
- [HatchWorks — Claude Agent SDK and Managed Agents](https://hatchworks.com/blog/claude/claude-agent-sdk-and-managed-agents/)
- [Composio — WhatsApp MCP with Claude Agent SDK](https://composio.dev/toolkits/whatsapp/framework/claude-agents-sdk)
- [Cliengo — Mejores chatbots de WhatsApp 2026](https://guiawabusiness.cliengo.com/mejores-chatbots-whatsapp)
- [Aurora Inbox — Cuánto cuesta un chatbot para WhatsApp 2026](https://www.aurorainbox.com/?p=38229)
- [YCloud — Proveedores de agentes IA para WhatsApp](https://www.ycloud.com/es/blog/top-whatsapp-ai-agent-providers)
- [Rework — Mejores plataformas de agentes IA 2026](https://resources.rework.com/es/tools/ai-agents/best-ai-agent-platforms-2026)
- [respond.io — WhatsApp general-purpose chatbots ban](https://respond.io/blog/whatsapp-general-purpose-chatbots-ban)
- [Gulf News — Meta bans major AI chatbots on WhatsApp](https://gulfnews.com/technology/no-more-chatgpt-and-perplexity-on-whatsapp-meta-bans-major-ai-chatbots-from-2026-1.500316016)
