# Base de prospectos — Pereira y Dosquebradas

> **Foco actual (2026-10-27): clínicas dentales.** Lista de trabajo: [`clinicas-dentales.csv`](clinicas-dentales.csv)
> (29 clínicas, 14 con WhatsApp, con columnas para la auditoría gratis). El archivo general se conserva para
> verticales futuras.

Archivo principal: [`prospectos-pereira-dosquebradas.csv`](prospectos-pereira-dosquebradas.csv) (se abre en
Excel o Google Sheets). Primera versión: 2026-10-27 · **62 negocios**.

## Cómo se construyó
- Google Maps está bloqueado por la red de este entorno (proxy 403), y la descarga directa de páginas
  también. La lista se armó con **búsqueda web** sobre fuentes públicas: sitios oficiales de cada negocio,
  Instagram/Facebook, Doctoralia, Megacentro Pinares, directorios (PlanetaColombia, Nexdu, InformaColombia,
  2pos, Guía del Eje, Fitfit, ClinicasYHospitales).
- **Cada fila tiene su fuente** (columna `fuente`). Algunos datos tienen años: **verificar antes de contactar**.
- Cadenas nacionales (Smart Fit, Bodytech, Comfamiliar) se excluyeron: deciden fuera de Pereira.

## Resumen
| Vertical | Negocios |
|---|---|
| Odontología (incl. ortodoncia/implantes) | 18 |
| Medicina estética, dermatología y cirugía plástica | 12 |
| Estética / spa | 8 |
| Inmobiliarias | 9 |
| Veterinarias | 6 |
| Talleres de motos y carros | 6 |
| Gimnasios | 3 |

- **Prioridad A (39):** tienen celular/WhatsApp publicado → contacto inmediato.
- **Prioridad B (23):** solo fijo, número incompleto o hay que sacarlo del sitio web.
- Pereira: 40 · Dosquebradas: 20 · ambas: 2.

## Columnas
`id, nombre, vertical, ciudad, direccion, telefono_fijo, celular_whatsapp, web_redes, email, prioridad, etapa, notas, fuente`

Etapas: `Nuevo → Mystery shop → Contactado → Respondió → Visita/Llamada → Demo → Propuesta → Ganado / Perdido`.
Agregar columnas al usarla: `tiempo_respuesta_mystery`, `fecha_ultimo_contacto`, `proximo_paso`.

## Top 15 para empezar (clínicas, núcleo del negocio, con WhatsApp)
| # | Negocio | Por qué |
|---|---|---|
| 1 | Proced Odontología (id 1) | WhatsApp público, zona Circunvalar |
| 2 | Del Castillo Odontología (2) | Implantes/ortodoncia = ticket alto |
| 3 | PB Odontología (10) | Ortodoncia, Megacentro Pinares |
| 4 | Dra. Johanna Calderón (11) | Implantes, Cerritos Mall, horario extendido |
| 5 | Odontología AGB (12) | Implantes y ortodoncia, centro |
| 6 | Tu Odontólogo Pereira (8) | Ya agenda por WhatsApp → dolor directo |
| 7 | Dr. Roberto Granados (3) | Consultorio independiente |
| 8 | Arte Dental DG (16) | Dosquebradas |
| 9 | Dra. Duarte (19) | Ya invierte en contenido; Cerritos Mall |
| 10 | Biomédica Estética IPS (20) | Multiespecialidad → plan Integral |
| 11 | Dra. Oriana Morales (21) | Pinares |
| 12 | UDL Grupo Dermatológico (25) | Dos sedes → plan Integral |
| 13 | Piel y Belleza (24) | Megacentro Pinares |
| 14 | Adriana Ramírez Med. Cosmética (30) | Dosquebradas |
| 15 | Dr. Mauricio Ramírez (28) | Cirugía plástica = ticket muy alto |

**Ruta eficiente de visitas:** Megacentro Pinares (ids 4, 10, 24, 27, 28) y Edificio Oval / Av. Juan B. Gutiérrez
(20, 21, 29) concentran muchos consultorios: se pueden visitar 3–5 en una sola salida.

## Reglas de uso
- Son datos de contacto comerciales publicados por los propios negocios. Aun así, por la Ley 1581 de 2012
  y las políticas de WhatsApp: mensajes **uno a uno y personalizados** (nada de envíos masivos), identificarse
  siempre y retirar de la lista a quien pida no ser contactado.
- Ningún mensaje se envía sin aprobación del fundador.
- Actualizar el CSV después de cada contacto (o migrarlo a Google Sheets/Notion para editarlo desde el celular).

## Próximas ampliaciones
- Completar los números de prioridad B (fundador o Claude en una sesión con acceso a Google Maps).
- Agregar: restaurantes con domicilio, salones de belleza/barberías, hoteles y fincas del Eje Cafetero,
  academias, Santa Rosa de Cabal y La Virginia.
