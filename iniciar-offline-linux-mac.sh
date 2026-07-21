#!/bin/bash
# Golf Challenge — modo offline (dois cliques)
cd "$(dirname "$0")"
echo "============================================"
echo "  GOLF CHALLENGE — iniciando modo offline"
echo "  (o navegador vai abrir sozinho)"
echo "============================================"
echo
python3 servidor.py
