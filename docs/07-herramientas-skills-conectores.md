# 07 · Herramientas, skills y conectores

> Inventario al 2026-10-27. Actualizar cuando se conecten/desconecten herramientas.

## 1. Skills disponibles en el entorno de Claude

### Marketing y ventas
| Skill | Para qué la usaremos |
|---|---|
| `marketing:campaign-plan` | Planes de campaña trimestrales con calendario y métricas |
| `marketing:content-creation` / `marketing:draft-content` | Posts, landing, casos de estudio, emails |
| `marketing:email-sequence` | Secuencias de nurture y onboarding |
| `marketing:competitive-brief` | Análisis de competidores (otras agencias / bots de WhatsApp) |
| `marketing:seo-audit` | SEO de nuestra web y como add-on para clientes |
| `marketing:brand-review` | Revisar textos contra la voz de marca |
| `marketing:performance-report` | Reportes mensuales de marketing y a clientes |

### Creativos (anuncios y video)
| Skill | Uso |
|---|---|
| `anthropic-skills:ads-image-architect` | Kit de 7 prompts de imagen para Meta Ads |
| `anthropic-skills:estratega-avatarhype` | Guiones UGC de respuesta directa |
| `anthropic-skills:ugc-prompt-engineer`, `avatar-master-prompt` | Imágenes realistas tipo UGC |
| `anthropic-skills:vox-animated-ad`, `director-creativo-seedance`, `aigc-ads-lite` | Videos de anuncio |
| `anthropic-skills:nano-banana-prompt`, `gpt-image-2-ultrarrealista` | Prompts de imagen |

### Documentos y análisis
`anthropic-skills:deep-research` (investigación profunda), `docs`, `xlsx` (modelos financieros, CRM),
`pptx` (pitch deck), `pdf` (propuestas), `dataviz` (tableros), `skill-creator` (crear nuestras propias skills,
p. ej. "generar-propuesta-clinica").

## 2. Conectores (MCP)

| Conector | Estado | Uso en el negocio |
|---|---|---|
| **Shopify** | ✅ Activo | Generar nombres de marca y verificar dominios; tienda para vender planes/add-ons si aplica |
| **Canva** | ✅ Activo | Logo, kit de marca, posts, propuestas visuales |
| **Notion** | ✅ Activo | Wiki/CRM alternativo, memoria persistente fuera de GitHub |
| **Google Drive** | ✅ Activo | Hojas de CRM, reportes a clientes, contratos |
| **Higgsfield** | ✅ Activo | Videos/imágenes de anuncios, landing page (website builder), publicación en TikTok |
| **GitHub** | ✅ Activo | Este repositorio = cerebro documental |
| HubSpot | ⚠️ Falló al conectar (proxy 403) | CRM de ventas profesional |
| Gmail / Google Calendar | ⚠️ Falló al conectar | Outreach por email y agenda de llamadas |
| Slack | ⚠️ Falló al conectar | Comunicación interna/alertas |
| Klaviyo | ⚠️ Falló al conectar | Email marketing |
| Ahrefs / Similarweb | ⚠️ Falló al conectar | SEO e inteligencia competitiva |
| Amplitude / Supermetrics / Figma | ⚠️ Falló al conectar | Analítica y diseño |

> Los conectores con ⚠️ están configurados pero el proxy de red del entorno bloqueó la conexión.
> Solución: revisar la política de red del entorno en claude.ai/code o reintentar en otra sesión.

## 3. Herramientas externas recomendadas (no-Claude)
| Categoría | Herramienta | Por qué |
|---|---|---|
| WhatsApp API | 360dialog, Twilio, ezcontact, Chattigo | Acceso oficial a la API de WhatsApp en LATAM |
| Automatización | n8n, Make, Zapier | Conectar WhatsApp + IA + calendario + CRM |
| Voz IA | Retell, Vapi, ElevenLabs | Agente de llamadas (plan Premium) |
| Agenda | Google Calendar, Calendly, Cal.com | Citas |
| Prospección | Google Maps, Apollo, PhantomBuster | Construir listas |
| Video de ventas | Loom | Videos personalizados de 60 s |
| Cobros | Stripe, Mercado Pago, Wompi, PayU | Pagos recurrentes |

## 4. Conocimiento base (marcos de negocio)
- **$100M Offers (Hormozi):** ecuación de valor, oferta Grand Slam, garantías, escasez, urgencia, bonos.
- **$100M Leads (Hormozi):** Core Four, regla del 100, "más, mejor, nuevo", dar antes de pedir.
- **Tres palancas de crecimiento:** más clientes, mayor ticket, mayor frecuencia/permanencia.
- **SaaS metrics:** MRR, churn, LTV/CAC, payback.

## Fuentes
- [Coupler.io — Best Claude connectors for business 2026](https://blog.coupler.io/best-claude-connectors/)
- [Drag — Best Claude MCP servers for business 2026](https://www.dragapp.com/blog/best-claude-mcp-servers/)
- [Breakcold — Sales software with Claude integration](https://www.breakcold.com/blog/best-sales-software-with-claude-integration)
- [SyncGTM — Claude Code HubSpot integration](https://syncgtm.com/blog/claude-code-hubspot-integration)
- [Coupler.io — Claude Code for marketing](https://blog.coupler.io/claude-code-for-marketing/)
- [Towards AI — Claude's Shopify MCP connector guide](https://pub.towardsai.net/claudes-shopify-mcp-connector-complete-guide-2026-b696bdaab9cf)
- [Shortform — $100M Leads](https://www.shortform.com/blog/wp-json/wp/v2/posts/146297)
- [SuperSummary — $100M Offers](https://www.supersummary.com/100m-offers/summary/)
- [Amy Porterfield — Core Four](https://www.amyporterfield.com/2024/02/650/)
