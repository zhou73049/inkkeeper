#!/bin/bash
# ==================== start.sh ====================
# InkKeeper 快速启动脚本

#!/bin/bash
set -e

echo "[InkKeeper] 启动 CUPS..."
cupsd
sleep 2

if [ -n "$PRINTER_IP" ] && [ "$PRINTER_CONNECTION" = "cups" ]; then
    echo "[InkKeeper] 配置打印机 ${PRINTER_NAME} -> ${PRINTER_IP}..."
    lpadmin -p "${PRINTER_NAME}" -E -v "ipp://${PRINTER_IP}/ipp/print" -m everywhere 2>/dev/null || true
    cupsenable "${PRINTER_NAME}" 2>/dev/null || true
    lpadmin -d "${PRINTER_NAME}" 2>/dev/null || true
    echo "[InkKeeper] 打印机已配置"
fi

echo "[InkKeeper] 启动 Web 服务..."
exec gunicorn --bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120 app:app
