# Checklist de onboarding de cliente

## Antes de empezar
- [ ] Contrato firmado y acuerdo de tratamiento de datos
- [ ] Pago del setup recibido
- [ ] Carpeta del cliente creada (Drive) y fila en CRM marcada "Ganado"

## Formulario de onboarding (cliente)
- [ ] Nombre comercial, sedes, direcciones, horarios
- [ ] Lista de servicios con precios (o rangos) y duración
- [ ] 20 preguntas más frecuentes de pacientes y sus respuestas
- [ ] Políticas: cancelación, pagos, seguros/convenios, promociones vigentes
- [ ] Tono deseado (formal/cercano), emojis sí/no
- [ ] Casos que SIEMPRE pasan a humano (urgencias, quejas, temas clínicos)
- [ ] ¿Dónde vive hoy la agenda? (cuaderno/Excel → modo A · Google Calendar o software con API → modo B · software sin API → modo C pre-reserva). Ver `docs/14-integracion-agenda-y-operacion.md`
- [ ] Profesionales, sillas, horario y vacaciones de cada uno; duración real de cada servicio; días festivos que abren
- [ ] Citas de los próximos 60 días para la carga inicial
- [ ] ¿Atienden EPS/prepagadas/pólizas? Formas de pago, parqueadero, niños
- [ ] Número de WhatsApp a usar (coexistencia con la app actual o número nuevo) y verificación de Meta Business
- [ ] Usuarios del panel con rol (dueño, recepción, odontólogos)
- [ ] Base de pacientes antiguos para reactivación (con consentimiento)

## Construcción (Claude)
- [ ] Base de conocimiento cargada
- [ ] Flujos: bienvenida → calificación → agenda → confirmación → recordatorios
- [ ] Traspaso a humano configurado
- [ ] Plantillas de mensajes salientes enviadas a aprobación de Meta
- [ ] 30 conversaciones de prueba (incluye casos difíciles y fuera de tema)

## Lanzamiento
- [ ] Semana de sombra: Sofía deja citas "por confirmar" y recepción aprueba; revisión diaria
- [ ] Acuerdo escrito: desde la fecha X la agenda oficial es una sola
- [ ] Llamada de revisión con el cliente (30 min)
- [ ] Puesta en marcha y monitoreo intensivo 48 h
- [ ] Enviar "primera victoria" (captura de primera cita agendada)
- [ ] Programar revisión semanal y reporte mensual
