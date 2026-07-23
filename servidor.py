#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Golf Challenge — servidor (telão + formulário + API NocoDB).

Rodar:            python3 servidor.py
Configurar banco: edite nocodb.json (url + token) e rode: python3 servidor.py --setup

Páginas:
  /        → telão do jogo (código, cronômetro, tacadas, celebrações)
  /form    → formulário público (celular) que gera o código

API:
  POST /api/inscricao  {nome, whatsapp, email}  → {code}
  GET  /api/inscricao?code=XXXX                 → {nome, code}
  POST /api/jogada     {registro da jogada}     → {ok}

Se o NocoDB estiver configurado, tudo é gravado lá; sem ele, cai num
armazenamento local (pasta data/) para testes/contingência.
"""
import json
import os
import random
import ssl
import sys
import threading
import urllib.request
import urllib.error
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

PORT = 8000
PORT_HTTPS = 8443
BASE = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE, "data")
NOCO_CFG = os.path.join(BASE, "nocodb.json")
CERT = os.path.join(BASE, "cert.pem")
KEY = os.path.join(BASE, "key.pem")

CODE_CHARS = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # sem I/L/O/0/1 (evita confusão)
CODE_LEN = 4

lock = threading.Lock()


# ============================ NocoDB ============================
def noco_cfg():
    try:
        with open(NOCO_CFG, encoding="utf-8") as f:
            c = json.load(f)
    except (OSError, ValueError):
        c = {}
    # token fora do repositório: arquivo local nocodb.token (gitignorado)
    if not c.get("token"):
        try:
            with open(os.path.join(BASE, "nocodb.token"), encoding="utf-8") as f:
                c["token"] = f.read().strip()
        except OSError:
            pass
    # variáveis de ambiente têm prioridade (deploy sem segredos no repositório)
    if os.environ.get("NOCODB_URL"):
        c["url"] = os.environ["NOCODB_URL"]
    if os.environ.get("NOCODB_TOKEN"):
        c["token"] = os.environ["NOCODB_TOKEN"]
    return c


def noco_save_cfg(cfg):
    with open(NOCO_CFG, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def noco_ready(cfg=None):
    c = cfg or noco_cfg()
    return bool(c.get("url") and c.get("token") and c.get("tables"))


def noco_req(method, path, body=None):
    c = noco_cfg()
    url = c["url"].rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("xc-token", c["token"])
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.loads(r.read().decode("utf-8") or "{}")


def noco_setup():
    """Cria a base 'Golf Challenge' e as tabelas no NocoDB."""
    c = noco_cfg()
    if not c.get("url") or not c.get("token"):
        print("✗ Preencha url e token em nocodb.json antes do --setup")
        sys.exit(1)
    print("→ Conectando em", c["url"])
    bases = noco_req("GET", "/api/v2/meta/bases")
    base_id = None
    for b in bases.get("list", []):
        if b.get("title") == "Golf Challenge":
            base_id = b["id"]
            print("• Base 'Golf Challenge' já existe:", base_id)
            break
    if not base_id:
        nb = noco_req("POST", "/api/v2/meta/bases", {"title": "Golf Challenge"})
        base_id = nb["id"]
        print("✓ Base criada:", base_id)

    existing = noco_req("GET", f"/api/v2/meta/bases/{base_id}/tables")
    have = {t["title"]: t["id"] for t in existing.get("list", [])}

    def ensure_table(title, columns):
        if title in have:
            print(f"• Tabela '{title}' já existe:", have[title])
            return have[title]
        t = noco_req("POST", f"/api/v2/meta/bases/{base_id}/tables", {
            "table_name": title, "title": title, "columns": columns,
        })
        print(f"✓ Tabela '{title}' criada:", t["id"])
        return t["id"]

    insc_id = ensure_table("inscricoes", [
        {"column_name": "Codigo",   "title": "Codigo",   "uidt": "SingleLineText"},
        {"column_name": "Nome",     "title": "Nome",     "uidt": "SingleLineText"},
        {"column_name": "WhatsApp", "title": "WhatsApp", "uidt": "SingleLineText"},
        {"column_name": "Email",    "title": "Email",    "uidt": "SingleLineText"},
        {"column_name": "CriadoEm", "title": "CriadoEm", "uidt": "SingleLineText"},
    ])
    jog_id = ensure_table("jogadas", [
        {"column_name": "LocalId",  "title": "LocalId",  "uidt": "SingleLineText"},
        {"column_name": "Codigo",   "title": "Codigo",   "uidt": "SingleLineText"},
        {"column_name": "Nome",     "title": "Nome",     "uidt": "SingleLineText"},
        {"column_name": "Tacadas",  "title": "Tacadas",  "uidt": "Number"},
        {"column_name": "TempoMs",  "title": "TempoMs",  "uidt": "Number"},
        {"column_name": "Tempo",    "title": "Tempo",    "uidt": "SingleLineText"},
        {"column_name": "Status",   "title": "Status",   "uidt": "SingleLineText"},
        {"column_name": "Auto",     "title": "Auto",     "uidt": "Checkbox"},
        {"column_name": "Dia",      "title": "Dia",      "uidt": "SingleLineText"},
        {"column_name": "CriadoEm", "title": "CriadoEm", "uidt": "SingleLineText"},
    ])

    c["baseId"] = base_id
    c["tables"] = {"inscricoes": insc_id, "jogadas": jog_id}
    noco_save_cfg(c)
    print("\n✓ nocodb.json atualizado — banco pronto!")


# ==================== armazenamento local (fallback) ====================
def _local_path(name):
    os.makedirs(DATA_DIR, exist_ok=True)
    return os.path.join(DATA_DIR, name + ".json")


def local_load(name):
    try:
        with open(_local_path(name), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return []


def local_save(name, rows):
    with open(_local_path(name), "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=1, ensure_ascii=False)


# ============================ operações ============================
def gen_code(existing):
    while True:
        code = "".join(random.choice(CODE_CHARS) for _ in range(CODE_LEN))
        if code not in existing:
            return code


def db_create_inscricao(nome, whatsapp, email):
    from datetime import datetime
    now = datetime.now().isoformat(timespec="seconds")
    if noco_ready():
        try:
            tid = noco_cfg()["tables"]["inscricoes"]
            # códigos existentes (últimos 1000)
            rows = noco_req("GET", f"/api/v2/tables/{tid}/records?limit=1000&fields=Codigo")
            existing = {r.get("Codigo") for r in rows.get("list", [])}
            code = gen_code(existing)
            noco_req("POST", f"/api/v2/tables/{tid}/records",
                     {"Codigo": code, "Nome": nome, "WhatsApp": whatsapp, "Email": email, "CriadoEm": now})
            return code
        except Exception:
            pass  # sem internet/banco → PLANO B: salva local e sincroniza depois
    with lock:
        rows = local_load("inscricoes")
        code = gen_code({r["Codigo"] for r in rows})
        rows.append({"Codigo": code, "Nome": nome, "WhatsApp": whatsapp, "Email": email,
                     "CriadoEm": now, "_pendente": True})
        local_save("inscricoes", rows)
    return code


def db_find_inscricao(code):
    code = code.strip().upper()
    if noco_ready():
        try:
            tid = noco_cfg()["tables"]["inscricoes"]
            rows = noco_req("GET", f"/api/v2/tables/{tid}/records?where=(Codigo,eq,{code})&limit=1")
            lst = rows.get("list", [])
            if lst:
                return lst[0]
        except Exception:
            pass  # cai na busca local
    with lock:
        for r in local_load("inscricoes"):
            if r["Codigo"] == code:
                return r
    return None


def _noco_all(tid, fields=None):
    out, offset = [], 0
    extra = f"&fields={fields}" if fields else ""
    while True:
        page = noco_req("GET", f"/api/v2/tables/{tid}/records?limit=200&offset={offset}{extra}").get("list", [])
        out += page
        if len(page) < 200:
            return out
        offset += 200


def db_list_codigos():
    """Todos os cadastros em ordem de chegada, marcando quem já jogou."""
    ins, jogados = [], set()
    if noco_ready():
        try:
            c = noco_cfg()["tables"]
            ins = _noco_all(c["inscricoes"])
            jogados = {r.get("Codigo") for r in _noco_all(c["jogadas"], "Codigo") if r.get("Codigo")}
        except Exception:
            ins = []
    if not ins:
        with lock:
            ins = local_load("inscricoes")
            jogados |= {r.get("Codigo") for r in local_load("jogadas") if r.get("Codigo")}
    ins.sort(key=lambda r: r.get("CriadoEm") or "")
    out = []
    for r in ins:
        w = str(r.get("WhatsApp") or "")
        out.append({
            "code": r.get("Codigo"), "nome": r.get("Nome"),
            "whatsapp": ("…" + w[-4:]) if len(w) >= 4 else "",
            "criado": r.get("CriadoEm") or "",
            "jogou": r.get("Codigo") in jogados,
        })
    return out


def db_save_jogada(j):
    row = {
        "LocalId": str(j.get("id", "")), "Codigo": j.get("code") or "",
        "Nome": j.get("name", ""), "Tacadas": j.get("strokes") or 0,
        "TempoMs": j.get("timeMs") or 0,
        "Tempo": _fmt_ms(j.get("timeMs") or 0),
        "Status": j.get("status", ""), "Auto": bool(j.get("auto")),
        "Dia": j.get("day", ""), "CriadoEm": j.get("createdAt", ""),
    }
    if noco_ready():
        try:
            tid = noco_cfg()["tables"]["jogadas"]
            found = noco_req("GET", f"/api/v2/tables/{tid}/records?where=(LocalId,eq,{row['LocalId']})&limit=1").get("list", [])
            if found:
                row["Id"] = found[0]["Id"]
                noco_req("PATCH", f"/api/v2/tables/{tid}/records", [row])
            else:
                noco_req("POST", f"/api/v2/tables/{tid}/records", row)
            return
        except Exception:
            pass  # sem internet/banco → PLANO B: salva local e sincroniza depois
    with lock:
        rows = local_load("jogadas")
        rows = [r for r in rows if r.get("LocalId") != row["LocalId"]]
        row["_pendente"] = True
        rows.append(row)
        local_save("jogadas", rows)


def _fmt_ms(ms):
    ms = max(0, int(ms))
    return f"{ms//60000}:{(ms%60000)//1000:02d}.{(ms%1000)//100}"


# ============================ HTTP ============================
class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE, **kwargs)

    def _json(self, code, obj):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        n = int(self.headers.get("Content-Length", 0) or 0)
        try:
            return json.loads(self.rfile.read(n).decode("utf-8") or "{}")
        except ValueError:
            return None

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/api/inscricao"):
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query)
            code = (q.get("code") or [""])[0]
            if not code:
                return self._json(400, {"error": "Informe o código"})
            try:
                r = db_find_inscricao(code)
            except Exception as e:
                return self._json(424, {"error": "Banco indisponível: " + str(e)[:120]})
            if not r:
                return self._json(404, {"error": "Código não encontrado"})
            return self._json(200, {"nome": r.get("Nome"), "code": r.get("Codigo")})
        if self.path == "/api/codigos":
            try:
                return self._json(200, {"list": db_list_codigos()})
            except Exception as e:
                return self._json(424, {"error": str(e)[:120]})
        if self.path in ("/form", "/form/"):
            self.path = "/form.html"
        elif self.path in ("/camera", "/camera/"):
            self.path = "/camera.html"
        elif self.path in ("/codigos", "/codigos/"):
            self.path = "/codigos.html"
        elif self.path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        if self.path == "/api/inscricao":
            b = self._body()
            if not b or not str(b.get("nome", "")).strip():
                return self._json(400, {"error": "Nome obrigatório"})
            if len(str(b.get("whatsapp", "")).strip()) < 10:
                return self._json(400, {"error": "WhatsApp inválido"})
            try:
                code = db_create_inscricao(
                    str(b["nome"]).strip()[:120],
                    str(b.get("whatsapp", "")).strip()[:30],
                    str(b.get("email", "")).strip()[:120])
            except Exception as e:
                return self._json(424, {"error": "Falha no banco: " + str(e)[:120]})
            return self._json(200, {"code": code})
        if self.path == "/api/jogada":
            b = self._body()
            if not b:
                return self._json(400, {"error": "JSON inválido"})
            try:
                db_save_jogada(b)
            except Exception as e:
                return self._json(424, {"error": "Falha no banco: " + str(e)[:120]})
            return self._json(200, {"ok": True})
        self._json(404, {"error": "rota inexistente"})

    def log_message(self, *args):
        pass


def ips_locais():
    import socket
    ips = set()
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("10.255.255.255", 1))
        ips.add(s.getsockname()[0])
        s.close()
    except OSError:
        pass
    return sorted(ips)


def noco_sync():
    """Sobe para o NocoDB tudo que ficou salvo localmente (modo offline)."""
    if not noco_ready():
        print("✗ NocoDB não configurado (nocodb.json / NOCODB_TOKEN). Nada a fazer.")
        return
    try:
        noco_req("GET", "/api/v2/meta/bases")
    except Exception as e:
        print(f"✗ Sem conexão com o NocoDB agora ({e}). Tente de novo quando a internet voltar.")
        return

    ins = local_load("inscricoes")
    tid = noco_cfg()["tables"]["inscricoes"]
    subidas = 0
    for r in ins:
        try:
            found = noco_req("GET", f"/api/v2/tables/{tid}/records?where=(Codigo,eq,{r['Codigo']})&limit=1").get("list", [])
            if not found:
                noco_req("POST", f"/api/v2/tables/{tid}/records",
                         {k: v for k, v in r.items() if not k.startswith("_")})
                subidas += 1
            r.pop("_pendente", None)
        except Exception as e:
            print(f"  ! inscrição {r.get('Codigo')}: {e}")
    local_save("inscricoes", ins)
    print(f"✓ Inscrições: {subidas} enviada(s) ao NocoDB ({len(ins)} no arquivo local)")

    jog = local_load("jogadas")
    enviadas = 0
    for r in jog:
        try:
            db_save_jogada({
                "id": r.get("LocalId"), "code": r.get("Codigo"), "name": r.get("Nome"),
                "strokes": r.get("Tacadas"), "timeMs": r.get("TempoMs"),
                "status": r.get("Status"), "auto": r.get("Auto"),
                "day": r.get("Dia"), "createdAt": r.get("CriadoEm"),
            })
            r.pop("_pendente", None)
            enviadas += 1
        except Exception as e:
            print(f"  ! jogada {r.get('LocalId')}: {e}")
    local_save("jogadas", jog)
    print(f"✓ Jogadas: {enviadas} sincronizada(s) ao NocoDB ({len(jog)} no arquivo local)")


if __name__ == "__main__":
    os.chdir(BASE)
    if "--setup" in sys.argv:
        noco_setup()
        sys.exit(0)
    if "--sync" in sys.argv:
        noco_sync()
        sys.exit(0)

    if not os.path.exists(NOCO_CFG):
        noco_save_cfg({"url": "", "token": "", "tables": None})

    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    if os.path.exists(CERT) and os.path.exists(KEY):
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.load_cert_chain(CERT, KEY)
        srv_https = ThreadingHTTPServer(("0.0.0.0", PORT_HTTPS), Handler)
        srv_https.socket = ctx.wrap_socket(srv_https.socket, server_side=True)
        threading.Thread(target=srv_https.serve_forever, daemon=True).start()

    nc = "NocoDB ✓ conectado" if noco_ready() else "NocoDB ✗ não configurado (usando armazenamento local ./data)"
    print("=" * 60)
    print("  GOLF CHALLENGE — servidor")
    print("=" * 60)
    print()
    print("  Telão (nesta máquina):  http://localhost:%d" % PORT)
    print("  Formulário público:     http://localhost:%d/form" % PORT)
    for ip in ips_locais():
        print(f"                          http://{ip}:{PORT}/form")
    print()
    print(" ", nc)
    print("  (Ctrl+C para encerrar)")
    print()
    try:
        webbrowser.open(f"http://localhost:{PORT}")
    except Exception:
        pass
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        sys.exit(0)
