# Poner Vértice en un servidor (producción)

> **Estado:** los scripts y archivos de esta carpeta están revisados (sintaxis de bash y de systemd comprobada) pero **todavía no se han probado en un servidor real**,
> porque aún no hay uno contratado. La primera instalación real puede pedir ajustes: se hace con calma y se anota aquí lo que cambie.
>
> **Requiere aprobación del fundador antes de empezar** (gasto o cuentas nuevas): el servidor (VPS), el dominio (o usar uno gratuito de prueba) y dónde guardar los respaldos.

## Qué se necesita
| Cosa | Para qué | Costo orientativo* |
|---|---|---|
| Servidor VPS con Ubuntu 24.04 LTS, 1 vCPU y 1–2 GB de RAM | Corre la app (SQLite, pocas clínicas: sobra) | ~USD 5–12 / mes |
| Dominio propio (ej. `app.verticeautomatizacion.com`) | HTTPS del panel y del webhook | ~USD 12 / año. **Mientras no haya primera venta:** usar `IP-con-guiones.sslip.io` (gratis, con certificado real) |
| Lugar para copias de seguridad **fuera del servidor** | Si el servidor se pierde, no se pierden los datos | Google Drive del fundador con `rclone` (gratis), u otro servidor |
| App **ntfy** en el celular (gratis) | Recibir las alertas | USD 0 |
\* Verificar precios vigentes antes de decidir; son cifras de referencia, no cotizaciones.

## Pasos
**1. Crear el servidor.** Ubuntu 24.04 LTS, con la llave SSH del fundador (no con contraseña). Anotar la IP.

**2. Copiar el código al servidor** (desde el computador donde está el repositorio):
```bash
ssh root@IP "mkdir -p /opt/vertice"
scp -r agente root@IP:/opt/vertice/
```

**3. Instalar** (en el servidor, como root):
```bash
bash /opt/vertice/agente/despliegue/instalar.sh TU-DOMINIO      # la primera vez se detiene y crea /etc/vertice/vertice.env
nano /etc/vertice/vertice.env                                  # completar (ver los comentarios del archivo)
bash /opt/vertice/agente/despliegue/instalar.sh TU-DOMINIO      # la segunda vez termina la instalación
```
Si el dominio es nuevo, apuntar su registro **A** a la IP del servidor *antes* de este paso (Caddy necesita que resuelva para emitir el certificado).

**4. Las clínicas.** Un archivo por clínica en `/etc/vertice/negocios/` (copiar `clinica-demo.yaml` y editar servicios, horarios, profesionales, `whatsapp_phone_number_id`, `modo_agenda`,
`politica_url`…). Después: `systemctl restart vertice`.

**5. Conectar WhatsApp (Meta).** En Meta for Developers:
- Crear un **usuario del sistema** y generar su **token permanente** (el temporal vence en 24 h y es la causa más común de que "se caiga" el asistente) → `WHATSAPP_TOKEN`.
- Copiar el **App Secret** → `WHATSAPP_APP_SECRET`.
- Webhook: URL `https://TU-DOMINIO/webhook` y el mismo `WHATSAPP_VERIFY_TOKEN`; suscribir el campo **messages** y, si la clínica usa su número actual junto a la app (coexistencia), también **smb_message_echoes**.
- Crear y aprobar la plantilla `recordatorio_cita` (`plantillas/plantillas-whatsapp-meta.md`).
- Con `VERTICE_ENTORNO=produccion` el servidor **no arranca** si falta alguno de estos secretos (a propósito: mejor caído y avisado que abierto a mensajes falsos).

**6. Crear a las personas de la clínica.** Entrar a `https://TU-DOMINIO/panel` con el código de la clínica y la clave de soporte (`VERTICE_PANEL_CLAVE_<ID>`, **sin** escribir usuario), ir a *Equipo* y crear al
dueño (y a recepción / odontólogos). Desde ese momento cada persona entra con su usuario y clave.

**7. Alertas y respaldos.**
- `VERTICE_ALERTA_URL=https://ntfy.sh/<un-tema-largo-e-inventado>` y suscribirse a ese tema en la app ntfy.
- `VERTICE_RESPALDO_CLAVE` (guardarla en un gestor de contraseñas, **fuera** del servidor) y `VERTICE_RESPALDO_SUBIR` (ej. `rclone copy {archivo} remoto:vertice`, tras configurar `rclone config` como usuario `vertice`).
- Probar: `sudo -u vertice env $(grep -v '^#' /etc/vertice/vertice.env | xargs) /opt/vertice/venv/bin/python -m vertice.respaldo crear` y luego `... -m vertice.respaldo verificar`.
- Probar el monitor: `systemctl start vertice-monitor.service` (debe terminar sin alertas) y apagar el servicio un momento para comprobar que llega el aviso al celular.

## Comprobaciones diarias, semanales y mensuales
| Cuándo | Qué | Cómo |
|---|---|---|
| Siempre | Alertas | Llegan al celular (ntfy). Cada una dice qué revisar. |
| Semanal | Estado del servicio | `systemctl status vertice vertice-monitor.timer vertice-respaldo.timer` · `journalctl -u vertice -n 100` |
| **Mensual** | **Prueba de restauración** | `... -m vertice.respaldo verificar` (restaura el último respaldo en una carpeta temporal y cuenta los registros). Un respaldo que nunca se probó no es un respaldo. |
| Mensual | Espacio en disco y actualizaciones | `df -h` · el sistema se actualiza solo (unattended-upgrades); reiniciar si lo pide |
| Cada actualización | Código nuevo | Copiar el código y `bash actualizar.sh` (hace un respaldo antes y comprueba que responda) |
| Cada año | Renovar | Dominio y la vigencia del token/claves de los proveedores |

## Si el servidor se pierde (recuperación)
1. Crear un servidor nuevo y repetir los pasos 1–5 (el mismo `vertice.env`, que debe estar guardado fuera del servidor junto con la clave de los respaldos).
2. Bajar el último respaldo del lugar remoto y restaurarlo:
   `python -m vertice.respaldo restaurar vertice-AAAAMMDD-HHMM.db.gz.enc /var/lib/vertice/vertice.db` (con `VERTICE_RESPALDO_CLAVE` definida), y `chown vertice:vertice` al archivo.
3. `systemctl restart vertice` y comprobar `https://TU-DOMINIO/salud`.
4. Cambiar el DNS si la IP cambió. Se pierde, como máximo, lo ocurrido desde el último respaldo (hasta 24 h): por eso conviene subirlo a otro lugar todos los días.

## Seguridad: lista de verificación
- [ ] Acceso al servidor solo con llave SSH (en `/etc/ssh/sshd_config`: `PasswordAuthentication no`). Cortafuegos y `fail2ban` activos (los instala el script).
- [ ] `/etc/vertice/vertice.env` con permisos 600 (el script los pone) y **no** copiado a ningún chat, correo ni repositorio.
- [ ] Llaves de IA creadas a nombre del negocio, con **tope de gasto mensual** en el panel del proveedor.
- [ ] `VERTICE_ENTORNO=produccion`. `/docs` y `/salud/detalle` no son accesibles desde internet (Caddy los bloquea; la app además los apaga o exige token).
- [ ] Respaldos cifrados, subidos a otro lugar, y la última prueba de restauración hecha hace menos de un mes.
- [ ] Solo se usan personas con usuario propio; la clave de soporte se guarda aparte y se cambia si alguien que la conocía sale del equipo.

## Qué vigila el monitoreo (y qué hacer cuando avisa)
| Alerta | Probable causa | Qué hacer |
|---|---|---|
| WhatsApp rechazó envíos | Token vencido/revocado o número bloqueado | Generar token permanente nuevo → `WHATSAPP_TOKEN` → `systemctl restart vertice` |
| El modelo de IA falló | Sin saldo, tope de gasto alcanzado o caída del proveedor | Revisar la cuenta del proveedor; el paciente recibe una disculpa y el caso queda para el equipo |
| Mensajes que fallaron por error del sistema | Error de programación | `journalctl -u vertice`; los pacientes quedaron como casos para atender a mano |
| Webhooks con firma inválida | Cambió el App Secret o intento falso | Verificar `WHATSAPP_APP_SECRET` en Meta |
| No llega ningún mensaje hace > 36 h | Webhook desactivado en Meta, DNS o servidor caído | Revisar el webhook en Meta y `systemctl status vertice caddy` |
| Servidor no responde | Caído | `systemctl restart vertice caddy`; revisar `journalctl` |
| Casos / solicitudes sin atender > 2 h | La clínica no está mirando el panel | Avisar a la clínica (y reforzar el aviso al dueño) |
| Poco espacio / respaldo viejo / respaldo no se copia | Disco lleno, falla del temporizador o de `rclone` | `df -h`; `systemctl status vertice-respaldo`; revisar `rclone` |
