# 🧠 MEMORIA DEL NEGOCIO — Fuente única de verdad

> **Regla #1:** Este archivo es la memoria permanente del proyecto. Cualquier sesión de Claude
> (o persona) debe leerlo ANTES de trabajar y actualizarlo DESPUÉS de cualquier decisión,
> aprendizaje o cambio de estado. Si algo no está aquí, no existe.
>
> Última actualización: 2026-10-28 · Sesión #20 (los 8 imprescindibles de docs/14 construidos; falta servidor y pruebas reales)

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
- **Nicho: 100 % clínicas dentales de Pereira y Dosquebradas** (decisión 2026-10-27). Otras verticales
  (estética, talleres, veterinarias…) quedan para después de tener casos de éxito dentales.
- **Oferta principal: "Sistema Vértice de Pacientes Nuevos"** (`docs/13-sistema-pacientes-dentales.md`):
  anuncios Meta "clic a WhatsApp" + asistente IA que responde y agenda 24/7 + ficha de Google y reseñas +
  contenido + reactivación + reporte mensual. COP 1.200.000 setup + 1.500.000/mes (anuncios aparte, los paga
  la clínica a Meta; mínimo recomendado 0,8–1,5 M/mes). El asistente solo (450k) queda como plan de entrada.
  ✅ **Precios y garantía aprobados por el fundador** (2026-10-27).
- **Puerta de entrada en frío:** "Auditoría gratis de pacientes perdidos" (`plantillas/auditoria-pacientes-perdidos.md`).
- **Tecnología:** agente propio "Clara" con **Claude API + Cloud API de Meta** en un VPS barato, multi-cliente;
  n8n solo como puente opcional (análisis en `docs/11-stack-tecnico-agentes-2026.md`).
- **Marca: Vértice — Automatización con IA** ✅ confirmada por el fundador. **Dominio pospuesto hasta la
  primera venta** (sugerido `verticeautomatizacion.com`, disponible al 2026-10-27). Ver `docs/12-marca.md`.
- **Asistente demo v0.1 construido** en `agente/` (Python + FastAPI + Claude API + Cloud API de WhatsApp):
  agenda, cancela y muestra citas, guarda prospectos, pasa a humano avisando al dueño; multi-negocio por YAML;
  demos "Clínica Dental Sonríe" (Sofía) y "MotoTaller Express" (Max); simulador en terminal; 12 pruebas OK.
  **Motores intercambiables** (`VERTICE_PROVEEDOR=claude|openai`): por ahora se prueba con la API key de
  OpenAI que ya tiene el fundador. ✅ **Probado en vivo** (2026-10-27) con `gpt-5.4-mini` desde el entorno de Claude
  (red y secreto `OPENAI_API_KEY` habilitados): 20/20 escenarios de la batería; transcripción en
  `agente/resultados/`. Falta: conectar el número de prueba de Meta (WhatsApp real).
- **Agenda sin cruces + panel del médico (v0.2, 2026-10-28):** varios odontólogos, almuerzo, bloqueos, reservas
  atómicas (probado con 20 pacientes simultáneos); panel web `/panel` con indicadores, agenda semanal (asistió/no
  asistió/cancelar, nueva cita, bloqueos), conversaciones completas y casos/interesados. Capturas en `demo/capturas/`.
  Probado en vivo con OpenAI: 20/20. Falta: publicarlo en un servidor (VPS) para que el médico lo abra desde su celular.
- **Panel rediseñado (v0.3):** navegación lateral, resumen Hoy/Periodo, agenda tipo calendario por odontólogo,
  panel lateral para citas y bloqueos, conversaciones con buscador y ficha del paciente.
- **Panel demo sin servidor:** https://claude.ai/artifact/WaS72eAXnZiXdQcAqS82sR (`demo/panel-demo.html`, generado con
  `python -m vertice.exportar_demo`): foto de los datos + simulador; se puede agendar/bloquear/marcar, los cambios no se guardan. Privado.
- **Página demo para visitas:** https://claude.ai/artifact/QNoA7pa8cbFn5WqLEwce34 (`demo/sofia.html`): chat tipo
  WhatsApp con Sofía (corre con Claude dentro de claude.ai, con la cuenta de quien la abre) + panel "lo que ve la
  clínica" (agenda, avisos al equipo, interesados) + personalizar nombre/dirección de la clínica visitada. Privada.
- **Prospectos:** base general de 73 negocios en `prospectos/prospectos-pereira-dosquebradas.csv`; **lista de trabajo:
  29 clínicas dentales** en `prospectos/clinicas-dentales.csv` (14 con WhatsApp) con columnas de auditoría. Construida con búsqueda web (Google Maps bloqueado en el entorno de Claude).
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
- **Red:** **ninguna** — no ha sido cliente de ninguna clínica de la lista (confirmado 2026-10-27).
  ➜ Adquisición 100 % en frío: auditoría gratis (mystery shopping + Google + Instagram + anuncios) → visita
  presencial con la hoja impresa y demo en el celular.
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
- [x] Nombre elegido: Vértice
- [x] Asistente demo v0.1 (código + pruebas) — `agente/README.md`
- [x] Motor OpenAI agregado al asistente (para probar con la key que ya tiene el fundador)
- [x] Batería de 20 conversaciones de prueba (`python -m vertice.pruebas_vivo`) lista
- [x] OpenAI habilitado en el entorno; batería en vivo 20/20 con `gpt-5.4-mini`; errores encontrados y corregidos
  (horarios de la tarde ocultos, servicios que requieren valoración, promesas de descuento/recordatorios)
- [ ] Elegir modelo de producción comparando calidad/costo (OpenAI vs Claude Haiku/Opus) con conversaciones reales
- [ ] Registrar `verticeautomatizacion.com` — **después de la primera venta**
- [x] Foco definido: clínicas dentales · oferta "Sistema de Pacientes Nuevos" · auditoría gratis · plantillas de anuncios
- [x] Mystery shopping #1 (27-oct, 9:37–10:19 p. m.): ~20 clínicas; solo 3 respondieron algo útil de noche y **ninguna agendó**;
  la única con IA (Ortocentro, "Ana") no ve la agenda. Detalle: `prospectos/mystery-shopping-2026-10-27.md`
- [x] Respuestas del día siguiente: 16 de ~20 respondieron entre 7:56 y 11:38 a. m. (mediana ≈ 10,8 h, casi todas personas,
  varias con notas de voz); 3 nunca respondieron (Proced, Odontología y Sonrisa, @Richo5555)
- [ ] Cerrar con amabilidad los chats donde ofrecieron cita (no dejar cupos apartados)
- [ ] Completar Google/Instagram/anuncios de las clínicas prioritarias y armar hojas de auditoría
- [ ] Primeras 5 visitas con la auditoría impresa (ruta Megacentro Pinares)
- [ ] Ampliar lista dental a 60+ clínicas (cuando haya acceso a Google Maps o con ayuda del fundador)
- [ ] Fundador crea cuenta en Meta for Developers (número de prueba de WhatsApp)
- [ ] RUT + cuenta separada para el negocio
- [x] Agenda sin cruces (multi-profesional, almuerzo, bloqueos, reservas atómicas) y panel del médico — 22 pruebas OK
- [ ] Publicar el servidor (webhook + panel) en un VPS con HTTPS
- [x] Análisis de integración de agenda y riesgos de operación (`docs/14-integracion-agenda-y-operacion.md`)
- [x] P0-1 hecho (2026-10-28): festivos de Colombia calculados, horario y vacaciones por profesional, bloqueos de varios días, aviso de citas por reprogramar
- [x] P0-2 hecho (2026-10-28): Sofía se pausa si el equipo escribe (aviso de Meta o desde el panel), tomar control/devolver, responder desde el panel; falta confirmar el formato real del aviso con un número conectado
- [x] P0-3 notas de voz y P0-4 reprogramar citas hechos (2026-10-28); notas de voz probadas con audio sintético, falta con audios reales
- [x] P0-5 recordatorios con botones de confirmación hechos en código (2026-10-28); **falta que el fundador cree/apruebe la plantilla en Meta** (`plantillas/plantillas-whatsapp-meta.md`)
- [x] P0-6 usuarios con rol (dueño/recepción/odontólogo), sesiones con vencimiento y bitácora de cambios hechos (2026-10-28)
- [x] P0-7 modo pre-reserva (agenda en otro sistema / semana de sombra) hecho (2026-10-28)
- [x] P0-8 robustez, modo producción, monitoreo, respaldos cifrados, aviso de privacidad y kit de instalación hechos y probados en código (2026-10-28)
- [ ] **Contratar el servidor (VPS) y hacer la primera instalación real** (`agente/despliegue/README.md`) — requiere aprobación del fundador; la instalación nunca se ha probado en un servidor real
- [ ] Meta: token permanente + App Secret + webhook + plantilla `recordatorio_cita` aprobada; confirmar con número real los formatos de eco, botones y plantillas
- [ ] Abogado: revisar `plantillas/privacidad-y-tratamiento-de-datos.md` (aviso, contrato de encargado, política)
- [ ] Probar con audios y conversaciones reales (notas de voz, jerga) antes del primer cliente
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
| 2026-10-27 | **Marca confirmada: Vértice** | Aprobada por el fundador |
| 2026-10-27 | Asistente en Python/FastAPI, manual loop con Claude API, herramientas estrictas, SQLite, caché de prompt y respaldo `fallbacks: "default"` | Bajo costo, multi-cliente, mantenible por Claude |
| 2026-10-27 | Modelo por defecto `claude-opus-5-5` (esfuerzo low), configurable; evaluar Haiku 5.5 antes del primer cliente | Opus ≈ COP 120k/mes por cliente vs Haiku ≈ COP 3,5k; decisión del fundador tras comparar calidad |
| 2026-10-27 | Prospectos se guardan en `prospectos/*.csv` con columna de fuente y etapa | CRM simple, versionado y verificable |
| 2026-10-27 | Pruebas con la API de OpenAI (key existente del fundador); motor intercambiable Claude/OpenAI | Cero gasto nuevo; el modelo final se decide con datos |
| 2026-10-27 | Dominio se compra después de la primera venta | Prioridad: vender antes de gastar |
| 2026-10-27 | **Nicho único: clínicas dentales** (reemplaza clínicas estéticas + verticales secundarias por ahora) | Son las más numerosas y necesitan pacientes; foco = mensajes y casos de éxito más rápidos |
| 2026-10-27 | Oferta principal "Sistema de Pacientes Nuevos" (anuncios + IA + Google + contenido + reactivación), 1,2 M setup + 1,5 M/mes; anuncios pagados por la clínica | La mayoría no hace anuncios ni tiene buena presencia en redes; ticket mayor y más retención |
| 2026-10-27 | Adquisición 100 % en frío con auditoría gratis como gancho (reemplaza "semi-cálida") | El fundador no ha sido cliente de ninguna clínica |
| 2026-10-27 | **Precios del Sistema de Pacientes aprobados** (450k / 1,5 M / 2,2 M al mes; setup 0,6 / 1,2 / 1,5 M) y garantía de 20 valoraciones en 60 días | Aprobado por el fundador |
| 2026-10-27 | Prueba en vivo desde el entorno de Claude con OpenAI (red + secreto), no desde el PC del fundador | Elección del fundador; ahorra su tiempo |
| 2026-10-27 | Modelo por defecto para pruebas/demos: OpenAI `gpt-5.4-mini` | 20/20 en la batería, respuestas en 1–3 s, económico; decisión final de producción tras comparar costos reales |
| 2026-10-27 | Reglas de negocio críticas se validan en las herramientas, no solo en el prompt (p. ej. `requiere_valoracion`) | El modelo a veces ignora instrucciones; el código no |
| 2026-10-27 | Demo para visitas = página web en claude.ai (artifact) que el fundador abre en su celular | No requiere servidor ni WhatsApp conectado; muestra chat + agenda en vivo |
| 2026-10-27 | Mensaje central de venta: "de 20 clínicas, ninguna me dejó una cita agendada de noche" (dato propio del mystery shopping) | Evidencia real y local; más fuerte que cifras de internet |
| 2026-10-28 | Agenda: reglas en `vertice/agenda.py` (una sola fuente para asistente y panel); reserva re-validada en transacción exclusiva; nombre y apellido obligatorios para agendar | Evitar cruces y citas con datos basura; lo pidió el fundador |
| 2026-10-28 | Panel del médico servido por la misma app (`/panel`), con clave por clínica | Sin costo extra; el médico ve agenda, conversaciones e indicadores |
| 2026-10-28 | Dato de venta principal: "respondieron unas 11 horas después" (mediana real del mystery shopping) | Las clínicas sí quieren pacientes (responden, ofrecen citas) pero tarde y a mano |
| 2026-10-28 | Toda consulta a SQLite pasa por un candado (lecturas incluidas) | El panel pide datos en paralelo y la conexión compartida fallaba (error 500) |
| 2026-10-28 | Regla: una sola agenda oficial por clínica. Tres modos: A) Vértice es la agenda, B) sincronizada (Google Calendar / software con API), C) pre-reserva con confirmación humana; siempre semana de sombra antes de encender | Evitar dobles reservas con cuadernos o software existentes |
| 2026-10-28 | No manejar historia clínica; solo agenda y conversación | Carga legal (Ley 2015/2020, Res. 866/2021) fuera de nuestro alcance |
| 2026-10-28 | Las clínicas cierran en festivos colombianos por defecto (`abre_festivos: false`, configurable); cada profesional puede tener horario propio | Evitar agendar festivos y horarios que el odontólogo no atiende |
| 2026-10-28 | Si una persona del equipo escribe en un chat, Sofía se pausa 12 h (configurable) y el paciente que escribe en pausa queda "esperando al equipo" | Evitar que bot y recepcionista respondan al mismo paciente sin dejar a nadie sin respuesta |
| 2026-10-28 | Notas de voz: se transcriben con OpenAI aunque el motor de chat sea Claude, y Sofía confirma nombre/fecha/hora antes de agendar | Claude API no recibe audio; la transcripción puede equivocarse |
| 2026-10-28 | Recordatorios: día anterior y 2 h antes, solo de 8 a. m. a 8 p. m., con botones Confirmo/Necesito cambiarla; se reservan en la base antes de enviar | Reducir inasistencias sin molestar ni enviar dos veces |
| 2026-10-28 | Panel con usuarios y roles (dueño, recepción, odontólogo); permisos validados en el servidor; el acceso con la clave de la clínica queda como "Soporte Vértice" y se ve en el historial | Que cada persona vea solo lo suyo, saber quién hizo cada cambio y poder dar soporte con transparencia |
| 2026-10-28 | Modo pre-reserva: el asistente aparta el horario como "por confirmar" y la recepción confirma o rechaza; es el modo de la semana de sombra y de clínicas con agenda externa | Una sola agenda oficial y cero dobles reservas sin exigir cambiar su sistema |
| 2026-10-28 | Producción exige secretos (arranque bloqueado si faltan), respaldos cifrados y subidos a otro lugar, alertas al celular y aviso de privacidad en el primer mensaje | Mejor caído y avisado que abierto a mensajes falsos; los datos de salud son sensibles (Ley 1581) y un respaldo que solo vive en el servidor no es un respaldo |
| 2026-10-28 | Reprogramar es una sola operación atómica y el panel no avisa solo al paciente: ofrece un mensaje para que el equipo lo envíe | Evitar huecos y no contactar pacientes sin que una persona lo decida |

## 8. Preguntas abiertas para el fundador

1. ¿Creamos ya la app en Meta for Developers para probar a Sofía en un WhatsApp real (número de prueba gratis)? Claude guía paso a paso.
2. ¿Ya auditaste las primeras clínicas (mystery shopping a las 7–8 p. m.)?
3. ¿Tienes conocimientos técnicos o computador disponible para crear la cuenta de Meta for Developers con guía?
4. ¿Facturarás como persona natural al inicio? (recomendado; SAS después).
5. ¿Apruebas contratar el servidor (VPS ~USD 5–12/mes, verificar precio) y usar un dominio gratuito `sslip.io` hasta la primera venta, para hacer la primera instalación real? (`agente/despliegue/README.md`)
6. ¿Dónde guardamos los respaldos fuera del servidor (tu Google Drive con rclone, u otro)?

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
- `docs/13-sistema-pacientes-dentales.md` — oferta principal para clínicas dentales (sistema de adquisición)
- `docs/14-integracion-agenda-y-operacion.md` — incorporar la agenda de la clínica, riesgos de operación y prioridades P0/P1/P2
- `prospectos/` — base de prospectos (CSV) y guía de uso
- `agente/` — código del asistente de WhatsApp (README con instalación, conexión a Meta y costos)
- `plantillas/` — guiones, propuesta, contrato, onboarding, **auditoría gratis**, **anuncios dentales**, **plantillas de WhatsApp para Meta** y **privacidad y tratamiento de datos**
- `agente/despliegue/` — instalación en servidor (HTTPS, servicios, respaldos, monitoreo), rutina mensual y recuperación
- `BITACORA.md` — diario de sesiones
