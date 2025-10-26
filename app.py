# app.py
import os
import re
import requests
from flask import Flask, request, redirect, url_for, session

# ------------------ Config ------------------
API_URL = "https://peakerr.com/api/v2"
API_KEY = os.environ.get("PEAKERR_API_KEY", "").strip()

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "cambia-esto-por-un-secreto-largo")

# ------------------ Helpers ------------------
def _page(title: str, body_html: str, flash_html: str = "") -> str:
    nav = (
        '<p style="margin:12px 0">'
        '<a href="/">Pedido</a> · '
        '<a href="/services">Servicios</a> · '
        '<a href="/status">Estado</a> · '
        '<a href="/balance">Saldo</a> · '
        '<a href="/admin">Admin</a>'
        "</p>"
    )
    return f"""
    <!doctype html>
    <meta charset="utf-8">
    <title>{title} · SAV03</title>
    <style>
      body {{ font-family: -apple-system, system-ui, Segoe UI, Roboto, Arial, sans-serif; max-width: 720px; margin: 24px auto; padding: 0 12px; }}
      input, button {{ width: 100%; padding: 10px 12px; margin: 8px 0; border-radius: 12px; border: 1px solid #ddd; }}
      button {{ background: #eee; cursor: pointer; }}
      table {{ width: 100%; border-collapse: collapse; }}
      th, td {{ border-bottom: 1px solid #eee; padding: 8px; text-align: left; font-size: 14px; }}
      .ok {{ color: #0a7d32; }}
      .err {{ color: #c40000; }}
      small.mono {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; }}
    </style>
    <h1>{title}</h1>
    {nav}
    {flash_html}
    {body_html}
    <p><small>© SAV03</small></p>
    """

def looks_like_url(x: str) -> bool:
    return bool(re.match(r"^https?://", (x or "").strip(), re.I))

def api_post(payload: dict):
    """POST a Peakerr con manejo de errores simples."""
    if not API_KEY:
        raise RuntimeError("Falta la variable de entorno PEAKERR_API_KEY.")
    data = {"key": API_KEY}
    data.update(payload)
    r = requests.post(API_URL, data=data, timeout=30)
    r.raise_for_status()
    return r.json()

def get_services():
    """Lista de servicios o [] si falla."""
    try:
        return api_post({"action": "services"})
    except Exception:
        return []

def get_service_limits(service_id: str):
    """Devuelve (min, max) del servicio o (None, None) si no se encuentran."""
    for s in get_services():
        sid = str(s.get("service") or s.get("id"))
        if sid == str(service_id):
            mn = int(s.get("min", 1))
            mx = int(s.get("max", 1000000))
            return mn, mx
    return None, None

# ------------------ Rutas ------------------
@app.route("/", methods=["GET", "POST"])
def index():
    flash = ""
    if request.method == "POST":
        sid = (request.form.get("service_id") or "").strip()
        link = (request.form.get("link") or "").strip()
        qty_raw = (request.form.get("quantity") or "").strip()

        errors = []
        if not sid.isdigit():
            errors.append("Service ID debe ser numérico.")
        if not looks_like_url(link):
            errors.append("El link debe empezar por http(s)://")
        try:
            qty = int(qty_raw)
            if qty <= 0:
                raise ValueError
        except Exception:
            qty = 0
            errors.append("Cantidad debe ser un entero positivo.")

        if not API_KEY:
            errors.append("Configura la variable PEAKERR_API_KEY en el servidor.")

        # Valida min/max del servicio si es posible
        if not errors:
            mn, mx = get_service_limits(sid)
            if mn is not None and (qty < mn or qty > mx):
                errors.append(f"La cantidad para el servicio {sid} debe estar entre {mn} y {mx}.")

        if errors:
            flash = '<p class="err">' + "<br>".join("• " + e for e in errors) + "</p>"
        else:
            try:
                data = api_post({
                    "action": "add",
                    "service": sid,
                    "link": link,
                    "quantity": qty
                })
                if "order" in data:
                    flash = f'<p class="ok">Pedido creado. ID: <b>{data["order"]}</b></p>'
                else:
                    flash = f'<p class="err">Error al crear el pedido: <small class="mono">{data}</small></p>'
            except Exception as e:
                flash = f'<p class="err">Error de red: {e}</p>'

    body = """
    <form method="post" autocomplete="on">
      <input name="service_id" placeholder="Service ID (p. ej., 27243)">
      <input name="link" placeholder="https://instagram.com/usuario">
      <input name="quantity" placeholder="Cantidad">
      <button type="submit">Enviar</button>
    </form>
    """
    return _page("Crear pedido", body, flash)

@app.route("/services")
def services():
    items = get_services()
    if not items:
        return _page("Servicios", '<p class="err">No se pudieron obtener los servicios ahora.</p>')
    rows = []
    for s in items[:600]:  # limitar para no saturar la página
        sid = s.get("service") or s.get("id")
        name = s.get("name", "")
        rate = s.get("rate") or s.get("price") or "?"
        mn = s.get("min", "?")
        mx = s.get("max", "?")
        rows.append(f"<tr><td>{sid}</td><td>{name}</td><td>{rate}</td><td>{mn}</td><td>{mx}</td></tr>")
    table = "<table><thead><tr><th>ID</th><th>Nombre</th><th>Precio/1k</th><th>Min</th><th>Max</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"
    return _page("Servicios", table)

@app.route("/status", methods=["GET"])
def status():
    order_id = (request.args.get("order_id") or "").strip()
    if not order_id:
        form = """
        <h3>Estado de pedido</h3>
        <form method="get">
          <input name="order_id" placeholder="ID del pedido">
          <button type="submit">Consultar</button>
        </form>
        """
        return _page("Estado", form)
    try:
        data = api_post({"action": "status", "order": order_id})
        html = f"""
        <h3>Pedido {order_id}</h3>
        <p>Estado: <b>{data.get('status')}</b></p>
        <p>Inicio: {data.get('start_count')}</p>
        <p>Restantes: {data.get('remains')}</p>
        <p>Charge: {data.get('charge')}</p>
        """
        return _page("Estado", html)
    except Exception as e:
        return _page("Estado", f'<p class="err">Error consultando estado: {e}</p>')

@app.route("/balance")
def balance():
    try:
        data = api_post({"action": "balance"})
        bal = data.get("balance")
        cur = data.get("currency", "")
        return _page("Saldo", f"<p>Saldo: <b>{bal} {cur}</b></p>")
    except Exception as e:
        return _page("Saldo", f'<p class="err">Error consultando saldo: {e}</p>')

# ------------------ Admin protegido ------------------
@app.route("/login", methods=["GET", "POST"])
def admin_login():
    err = ""
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if os.environ.get("ADMIN_PASSWORD") and pwd == os.environ.get("ADMIN_PASSWORD"):
            session["is_admin"] = True
            return redirect(url_for("admin"))
        err = "Contraseña incorrecta."
    form = f"""
    {'<p class="err">'+err+'</p>' if err else ''}
    <form method="post">
      <input type="password" name="password" placeholder="Contraseña">
      <button type="submit">Entrar</button>
    </form>
    """
    return _page("Login Admin", form)

@app.route("/admin")
def admin():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    body = """
    <p>Bienvenido al panel Admin.</p>
    <ul>
      <li>Próximamente: dashboard, últimos pedidos, etc.</li>
    </ul>
    <p><a href="/logout">Cerrar sesión</a></p>
    """
    return _page("Admin", body)

@app.route("/logout")
def logout():
    session.pop("is_admin", None)
    return redirect(url_for("index"))

# ------------------ Main (local) ------------------
if __name__ == "__main__":
    # Para pruebas locales únicamente
    app.run(host="0.0.0.0", port=10000, debug=True)