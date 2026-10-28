#!/usr/bin/env bash
# Actualiza Vértice después de copiar el código nuevo a /opt/vertice/agente. Uso (como root):  bash actualizar.sh
# Antes de reiniciar hace un respaldo, y después comprueba que el servicio responda.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Ejecuta como root"; exit 1; }
cd /opt/vertice/agente
echo "==> Respaldo previo"
systemctl start vertice-respaldo.service
echo "==> Dependencias"
grep -v -i '^pytest' requirements.txt | /opt/vertice/venv/bin/pip install -r /dev/stdin
chown -R root:vertice /opt/vertice && chmod -R g+rX,o-rwx /opt/vertice
cp despliegue/vertice*.service despliegue/vertice*.timer /etc/systemd/system/ && systemctl daemon-reload
echo "==> Reinicio"
systemctl restart vertice.service
sleep 3
curl -fsS http://127.0.0.1:8000/salud && echo && echo "Actualizado." || { echo "EL SERVICIO NO RESPONDE: revisa  journalctl -u vertice -n 50"; exit 1; }
