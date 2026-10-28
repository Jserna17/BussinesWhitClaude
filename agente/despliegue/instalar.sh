#!/usr/bin/env bash
# Instala Vértice en un servidor Ubuntu 22.04 / 24.04 recién creado.
# Uso (como root):   bash instalar.sh TU-DOMINIO
#   - El código debe estar ya en /opt/vertice/agente (ver README.md, paso 2).
#   - La primera vez crea /etc/vertice/vertice.env y se detiene para que lo completes; luego vuelve a ejecutar el mismo comando.
set -euo pipefail

DOMINIO="${1:?Falta el dominio. Ejemplo: bash instalar.sh app.midominio.com   (o 203-0-113-10.sslip.io mientras no tengas dominio)}"
CODIGO=/opt/vertice/agente
[[ $EUID -eq 0 ]] || { echo "Ejecuta como root (sudo bash instalar.sh ...)"; exit 1; }
[[ -f "$CODIGO/requirements.txt" ]] || { echo "No encuentro el código en $CODIGO. Cópialo primero (README.md, paso 2)."; exit 1; }

echo "==> Paquetes del sistema"
export DEBIAN_FRONTEND=noninteractive
apt-get update -y
apt-get install -y python3 python3-venv python3-pip ufw fail2ban unattended-upgrades curl openssl \
    debian-keyring debian-archive-keyring apt-transport-https gpg
timedatectl set-timezone America/Bogota

echo "==> Caddy (HTTPS automático)"
if ! command -v caddy >/dev/null; then
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
  curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
  apt-get update -y
  apt-get install -y caddy
fi

echo "==> Usuario y carpetas"
id vertice >/dev/null 2>&1 || useradd --system --home /opt/vertice --shell /usr/sbin/nologin vertice
install -d -o vertice -g vertice -m 750 /var/lib/vertice /var/lib/vertice/respaldos
install -d -o root -g vertice -m 750 /etc/vertice /etc/vertice/negocios
chown -R root:vertice /opt/vertice && chmod -R g+rX,o-rwx /opt/vertice

echo "==> Entorno de Python"
[[ -d /opt/vertice/venv ]] || python3 -m venv /opt/vertice/venv
/opt/vertice/venv/bin/pip install --upgrade pip
grep -v -i '^pytest' "$CODIGO/requirements.txt" | /opt/vertice/venv/bin/pip install -r /dev/stdin

echo "==> Configuración"
if [[ ! -f /etc/vertice/vertice.env ]]; then
  install -m 600 -o root -g root "$CODIGO/despliegue/vertice.env.ejemplo" /etc/vertice/vertice.env
  echo
  echo "Se creó /etc/vertice/vertice.env. Complétalo (nano /etc/vertice/vertice.env) y vuelve a ejecutar:  bash instalar.sh $DOMINIO"
  exit 0
fi
if ! ls /etc/vertice/negocios/*.yaml >/dev/null 2>&1; then
  cp "$CODIGO"/negocios/*.yaml /etc/vertice/negocios/
  echo "Se copiaron las clínicas de ejemplo a /etc/vertice/negocios (reemplázalas por las reales)."
fi
chown -R root:vertice /etc/vertice/negocios && chmod 640 /etc/vertice/negocios/*.yaml

echo "==> Servicios"
cp "$CODIGO"/despliegue/vertice*.service "$CODIGO"/despliegue/vertice*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now vertice.service vertice-monitor.timer vertice-respaldo.timer

echo "==> HTTPS con Caddy para $DOMINIO"
sed "s/TU-DOMINIO/$DOMINIO/" "$CODIGO/despliegue/Caddyfile.ejemplo" > /etc/caddy/Caddyfile
mkdir -p /var/log/caddy && chown caddy:caddy /var/log/caddy
systemctl reload caddy || systemctl restart caddy

echo "==> Cortafuegos y protección contra intentos de acceso"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
systemctl enable --now fail2ban
dpkg-reconfigure -f noninteractive unattended-upgrades || true

echo
echo "Listo. Comprobaciones:"
sleep 3
systemctl is-active vertice.service || true
curl -fsS "https://$DOMINIO/salud" && echo || echo "(El HTTPS puede tardar un minuto en emitirse; revisa que el dominio apunte a este servidor.)"
echo "Panel:    https://$DOMINIO/panel"
echo "Webhook:  https://$DOMINIO/webhook   (se registra en Meta junto con WHATSAPP_VERIFY_TOKEN)"
