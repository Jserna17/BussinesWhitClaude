# 🧠 MEMORIA DEL NEGOCIO — Fuente única de verdad

> **Regla #1:** Este archivo es la memoria permanente del proyecto. Cualquier sesión de Claude
> (o persona) debe leerlo ANTES de trabajar y actualizarlo DESPUÉS de cualquier decisión,
> aprendizaje o cambio de estado. Si algo no está aquí, no existe.
>
> Última actualización: 2026-10-27 · Sesión #4 (marca profesional, base de 62 prospectos)

---

## 1. Quiénes somos y qué estamos construyendo

- **Socios:** Juan José Serna (fundador, decisiones finales, cara del negocio ante clientes)
  + Claude (operador: adquisición, marketing, diseño de soluciones, administración y documentación).
- **Misión:** Construir un negocio de **ingresos recurrentes** (MRR) y escalarlo con clientes que pagan cada mes.
- **Ubicación:** **Pereira, Risaralda, Colombia** (área metropolitana: Pereira, Dosquebradas, La Virginia;
  expansión natural al Eje Cafetero: Manizales, Armenia, Santa Rosa de Cabal).
- **Repositorio:** `jserna17/bussineswhitclaude` — aquí vive toda la documentación del negocio.

## 2. Modelo de negocio (confirmado por el fundador)

**Agencia de automatización con IA para negocios locales**, con suscripción mensual.

- **Producto de entrada:** "Recepcionista IA 24/7 por WhatsApp" (responde, califica, agenda, recuerda, reactiva).
- **Expansión dentro de cada cliente:** automatizar más procesos con módulos reutilizables (agendamiento,
  reseñas, cotizaciones, cobranza, pedidos, Instagram DM, reportes, contenido, voz, back-office).
  Catálogo completo en `docs/10-catalogo-servicios-automatizacion.md`.
- **Nicho de lanzamiento (marketing y prospección en frío):** clínicas odontológicas y estéticas de Pereira.
- **Verticales secundarias** (vía contactos del fundador): talleres de motos/carros, gimnasios, turismo/fincas
  cafeteras, restaurantes, inmobiliarias, veterinarias/salones.
- **Tecnología:** agente propio "Clara" con **Claude API + Cloud API de Meta** en un VPS barato, multi-cliente;
  n8n solo como puente opcional (análisis en `docs/11-stack-tecnico-agentes-2026.md`).
- **Marca propuesta:** **Vértice — Automatización con IA** (`verticeautomatizacion.com` disponible al 2026-10-27).
  "Clara" fue descartada por el fundador (quiere un nombre de agencia profesional). Alternativas: Axioma, Prisma. Ver `docs/12-marca.md`.
- **Prospectos:** base de 62 negocios de Pereira y Dosquebradas en `prospectos/prospectos-pereira-dosquebradas.csv`
  (39 con WhatsApp/celular). Construida con búsqueda web (Google Maps bloqueado en el entorno de Claude).
- **Por qué:** WhatsApp tiene ~90–99 % de penetración en Colombia; las pymes pierden ventas por responder
  tarde; la mensajería de Meta en Colombia es muy barata (~USD 0,0008 por mensaje de servicio/utilidad).

## 3. Oferta y precios (v2, COP)

| Plan | Setup (único) | Mensualidad | Incluye |
|---|---|---|---|
| **Arranque** | 600.000 | 450.000 | 1 módulo (normalmente recepcionista WhatsApp) + reporte mensual |
| **Crecimiento** ⭐ | 900.000 | 850.000 | Hasta 3 módulos + optimización mensual |
| **Integral** | 1.500.000 | 1.500.000 | Hasta 6 módulos + optimización quincenal + soporte prioritario |

- Módulos extra: COP 150.000–300.000/mes. Proyectos a la medida desde COP 800.000 + mantenimiento mensual.
- Mensajería de Meta se traslada al cliente (en Colombia es casi insignificante).
- **Garantía:** si en 30 días el sistema no genera al menos 10 citas/ventas atribuibles, devolvemos el setup y seguimos gratis hasta lograrlo.
- 3 meses mínimo, luego mes a mes. Pago anual = 2 meses gratis.
- **Pilotos:** los 3 primeros clientes (idealmente conocidos del fundador) sin costo de setup a cambio de testimonio en video + caso de estudio.

## 4. Recursos del fundador

- **Tiempo:** **2 horas al día** (confirmado). Claude prepara todo; el fundador envía mensajes, visita
  negocios, hace demos y aprueba.
- **Red:** **no tiene red cálida** — conoce negocios donde ha sido cliente, sin relación con los dueños.
  ➜ Adquisición "semi-cálida" presencial (visitas con demo en el celular) + mystery shopping + frío digital.
- **Presupuesto:** **COP 500.000** para 90 días (confirmado). Distribución en `docs/09-presupuesto.md`.
  El abogado, correo pago y anuncios se pagan con el primer setup cobrado.

## 5. Metas y números clave (ajustadas a 2 h/día)

| Horizonte | Clientes activos | MRR objetivo (COP) |
|---|---|---|
| Día 30 | 2–3 pilotos | 0 (pilotos) |
| Día 90 | 8 | ~5.000.000 |
| Mes 6 | 18 | ~15.000.000 |
| Mes 12 | 40 | ~45.000.000 |

Punto de equilibrio: **2 clientes en plan Crecimiento** cubren todos los gastos mensuales.

KPIs que SIEMPRE se reportan: MRR, nuevos clientes, churn mensual (meta < 5 %), ticket promedio, CAC, LTV,
contactos/semana, reuniones agendadas, tasa de cierre.

## 6. Estado actual

- [x] Investigación de mercado inicial
- [x] Modelo de negocio, oferta y precios (v2 en COP)
- [x] Planes de adquisición, marketing, entrega y administración
- [x] Ciudad confirmada: Pereira · Modelo confirmado · Fundador tiene contactos
- [x] Presupuesto estimado y catálogo de servicios de automatización
- [x] Confirmado: 2 h/día, presupuesto COP 500.000, sin red cálida
- [x] Análisis de stack técnico (n8n vs alternativas) → agente propio con Claude API
- [x] Propuestas de marca con dominios verificados
- [x] Base de 62 prospectos (Pereira + Dosquebradas) con contacto y fuente
- [ ] Fundador elige nombre (recomendado Vértice) y registra dominio
- [ ] Fundador marca en la base los negocios donde ha sido cliente (semi-cálidos)
- [ ] Fundador crea cuenta en Meta for Developers (número de prueba de WhatsApp)
- [ ] RUT + cuenta separada para el negocio
- [ ] Construir demo funcional del agente
- [ ] Ampliar base a 150 negocios (restaurantes, salones, hoteles/fincas, Santa Rosa, La Virginia)
- [ ] Primeros 3 clientes piloto

## 7. Decisiones tomadas (registro inmutable — agregar, no borrar)

| Fecha | Decisión | Razón |
|---|---|---|
| 2026-10-27 | Modelo: servicio gestionado de agentes IA en WhatsApp con retainer | Recurrencia, baja inversión, demanda clara en LATAM |
| 2026-10-27 | Nicho inicial: clínicas estéticas/odontológicas | Ticket alto, dolor medible (inasistencias, respuesta lenta) |
| 2026-10-27 | Adquisición: Core Four de Hormozi, empezando por outreach cálido y frío | Cero presupuesto en ads al inicio |
| 2026-10-27 | `MEMORIA.md` + `BITACORA.md` como memoria persistente; `CLAUDE.md` la carga automáticamente | No perder contexto entre sesiones |
| 2026-10-27 | Mercado: Pereira, Colombia (luego Eje Cafetero) | Ciudad del fundador; venta presencial y confianza local |
| 2026-10-27 | Ampliar a "agencia de automatización IA para negocios locales"; WhatsApp = producto de entrada | Pedido del fundador; sube el ticket y la retención |
| 2026-10-27 | Precios en COP (v2): 450k / 850k / 1,5M mensuales | Ajuste al poder adquisitivo de Pereira |
| 2026-10-27 | Primeros pilotos salen de los contactos del fundador, en cualquier vertical | Ciclo de venta más corto; foco de marketing sigue en clínicas |
| 2026-10-27 | Stack inicial de bajo costo: Cloud API de Meta + n8n + Claude API + Google Sheets | Presupuesto mínimo |
| 2026-10-27 | **Reemplaza la anterior:** agente propio (Claude API + Cloud API de Meta, multi-cliente) como núcleo; n8n solo opcional | Plataformas gestionadas cuestan USD 15–113/cliente/mes y n8n es torpe multi-cliente; Claude construye y mantiene el código |
| 2026-10-27 | Presupuesto de arranque: COP 500.000 | Confirmado por el fundador |
| 2026-10-27 | **Reemplaza "pilotos de contactos":** adquisición semi-cálida presencial (negocios donde el fundador es cliente) + mystery shopping | El fundador no tiene relación con dueños |
| 2026-10-27 | El agente se limita al negocio del cliente (sin respuestas de propósito general) | Política de Meta vigente desde 15-ene-2026 |
| 2026-10-27 | Marca: descartada "Clara"; propuesta "Vértice Automatización" (pendiente aprobación) | El fundador quiere imagen de agencia profesional |
| 2026-10-27 | Prospectos se guardan en `prospectos/*.csv` con columna de fuente y etapa | CRM simple, versionado y verificable |

## 8. Preguntas abiertas para el fundador

1. ¿Qué nombre eliges? (recomendado: Vértice / verticeautomatizacion.com — ver `docs/12-marca.md`).
2. De la base de 62 prospectos, ¿en cuáles has sido cliente? ¿Hay otros que no estén?
3. ¿Tienes conocimientos técnicos o computador disponible para crear la cuenta de Meta for Developers con guía?
4. ¿Facturarás como persona natural al inicio? (recomendado; SAS después).

## 9. Reglas de operación para Claude

1. Leer `MEMORIA.md` y las últimas entradas de `BITACORA.md` al iniciar cada sesión.
2. Toda acción externa (enviar emails, publicar, gastar dinero, contactar clientes) requiere aprobación del fundador.
3. Registrar cada sesión en `BITACORA.md` y actualizar las secciones 6 y 7 de este archivo.
4. Las cifras de internet son orientativas: validar con datos reales de nuestros clientes.
5. Idioma de trabajo: español. Moneda: COP.
6. El fundador tiene poco tiempo: Claude deja todo listo para copiar/pegar y le pide solo decisiones o acciones concretas.

## 10. Mapa de documentos

- `README.md` — índice del proyecto
- `docs/01-investigacion-mercado.md` — negocios que funcionan hoy y por qué elegimos este
- `docs/02-modelo-de-negocio.md` — oferta, ecuación de valor, unit economics
- `docs/03-adquisicion-clientes.md` — Core Four, guiones, cadencias, embudo de ventas
- `docs/04-marketing.md` — marca, contenido, anuncios, calendario
- `docs/05-solucion-y-entrega.md` — stack técnico, onboarding, operación, retención
- `docs/06-administracion.md` — finanzas, contratos, legal, KPIs, rutinas
- `docs/07-herramientas-skills-conectores.md` — skills, conectores y herramientas disponibles
- `docs/08-plan-90-dias.md` — hoja de ruta semana a semana (Pereira, 2 h/día)
- `docs/09-presupuesto.md` — presupuesto inicial en COP y en qué se invierte
- `docs/10-catalogo-servicios-automatizacion.md` — módulos, paquetes por vertical y precios
- `docs/11-stack-tecnico-agentes-2026.md` — cómo se montan hoy los agentes; por qué agente propio y no n8n
- `docs/12-marca.md` — nombres propuestos y dominios verificados
- `prospectos/` — base de prospectos (CSV) y guía de uso
- `plantillas/` — guiones, propuesta, contrato y onboarding listos para usar
- `BITACORA.md` — diario de sesiones
