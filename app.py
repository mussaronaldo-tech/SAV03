import os, requests
from flask import Flask, request

app = Flask(__name__)

API_KEY = os.environ.get("PEAKERR_API_KEY", "")
API_URL = os.environ.get("API_URL", "https://peakerr.com/api/v2")

def _page(body):
    return f"""<main style="max-width:680px;margin:40px auto;font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial">
    <header style="display:flex;justify-content:space-between;align-items:center">
      <a href="/" style="font-weight:700;text-decoration:none;color:#111">SAV03</a>
      <nav style="display:flex;gap:14px;font-size:14px">
        <a href="/order">Pedido</a>
        <a href="/services">Servicios</a>
        <a href="/admin">Admin</a>
      </nav>
    </header>
    {body}
    <footer style="margin-top:40px;font-size:12px;opacity:.7">© SAV03</footer>
    </main>"""

@app.route("/")
def index():
    return _page("<h1>Bienvenido a SAV03 🚀</h1><p>Tu panel está activo.</p>")

@app.route("/admin")
def admin():
    return _page("<h2>Panel Admin de SAV03</h2><p>Funcionalidad próximamente.</p>")

ORDER_FORM = """
<h2>Crear pedido</h2>
<form method="post" style="display:grid;gap:12px;max-width:520px">
  <label>Service ID<br><input name="service" placeholder="p. ej. 27243" required></label>
  <label>Link/Usuario<br><input name="link" placeholder="https://instagram.com/usuario" required></label>
  <label>Cantidad<br><input name="quantity" type="number" min="10" required></label>
  <button type="submit" style="padding:10px 14px">Enviar</button>
</form>
<p style="font-size:12px;opacity:.7">Asegúrate de cumplir las normas de cada plataforma.</p>
"""

@app.route("/order", methods=["GET","POST"])
def order():
    if request.method == "POST":
        link = request.form.get("link","").strip()
        service = request.form.get("service","").strip()
        qty = request.form.get("quantity","").strip()
        if not (API_KEY and link and service and qty):
            return _page('<p style="color:red">Faltan datos o la API key no está configurada.</p>'+ORDER_FORM)
        try:
            r = requests.post(API_URL, data={
                "key": API_KEY,
                "action": "add",
                "service": service,
                "link": link,
                "quantity": qty
            }, timeout=20)
            data = r.json() if "application/json" in r.headers.get("content-type","") else {"raw": r.text}
            if "order" in data:
                return _page(f'<p>✅ Pedido creado. ID: <b>{data["order"]}</b></p>'+ORDER_FORM)
            else:
                return _page(f'<p style="color:red">❌ Error: {data}</p>'+ORDER_FORM)
        except Exception as e:
            return _page(f'<p style="color:red">❌ Error de conexión: {e}</p>'+ORDER_FORM)
    return _page(ORDER_FORM)

@app.route("/services")
def services():
    if not API_KEY:
        return _page('<p style="color:red">Configura PEAKERR_API_KEY.</p>')
    try:
        r = requests.post(API_URL, data={"key": API_KEY, "action": "services"}, timeout=20)
        data = r.json() if "application/json" in r.headers.get("content-type","") else None
        if not data:
            return _page("<p>No se pudo leer servicios.</p><pre>"+r.text+"</pre>")
        items = "".join(
            f"<li>#{s.get('service')} {s.get('name')} — min:{s.get('min')} max:{s.get('max')} rate:{s.get('rate')}</li>"
            for s in data[:100]
        )
        return _page("<h2>Servicios (primeros 100)</h2><ul>"+items+"</ul>")
    except Exception as e:
        return _page(f"<p style='color:red'>Error: {e}</p>")
from flask import Flask, request
import os, requests

app = Flask(__name__)

API_URL = "https://peakerr.com/api/v2"
API_KEY = os.environ.get("PEAKERR_API_KEY", "")

def _page(body: str) -> str:
    return f"""
<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SAV03</title>
<style>
 body{{font-family:system-ui,Arial,sans-serif;max-width:720px;margin:24px auto;padding:0 16px}}
 nav a{{margin-right:12px}}
 input,button{{padding:10px;margin:6px 0;width:100%;max-width:420px}}
 .ok{{color:#09814a}} .err{{color:#c62828}}
</style></head><body>
<nav>
  <a href="/">Pedido</a>
  <a href="/services">Servicios</a>
  <a href="/status">Estado</a>
  <a href="/balance">Saldo</a>
  <a href="/admin">Admin</a>
</nav>
{body}
<footer style="margin-top:24px;font-size:12px;color:#666">© SAV03</footer>
</body></html>
"""

@app.route("/", methods=["GET","POST"])
def index():
    msg = ""
    if request.method == "POST":
        service = request.form.get("service")
        link = request.form.get("link")
        quantity = request.form.get("quantity")
        try:
            r = requests.post(API_URL, data={
                "key": API_KEY, "action": "add",
                "service": service, "link": link, "quantity": quantity
            }, timeout=25)
            data = r.json()
            oid = data.get("order") or data.get("order_id") or "?"
            msg = f"<p class='ok'>Pedido creado. ID: <b>{oid}</b></p>"
        except Exception as e:
            msg = f"<p class='err'>Error creando el pedido: {e}</p>"

    form = """
<h2>Crear pedido</h2>
<form method="post">
  <input name="service" placeholder="Service ID (p. ej., 27243)" required>
  <input name="link" placeholder="https://instagram.com/usuario" required>
  <input name="quantity" type="number" placeholder="Cantidad" required>
  <button type="submit">Enviar</button>
</form>
"""
    return _page(msg + form)

@app.route("/services")
def services():
    try:
        r = requests.post(API_URL, data={"key": API_KEY, "action": "services"}, timeout=25)
        data = r.json()
        items = "".join(
            f"<li>#{s.get('service')} — {s.get('name')} — ${s.get('rate')}/1k</li>"
            for s in (data if isinstance(data, list) else [])
        )
        body = f"<h2>Servicios</h2><ul>{items or '<li>No disponible</li>'}</ul>"
    except Exception as e:
        body = f"<p class='err'>Error cargando servicios: {e}</p>"
    return _page(body)

@app.route("/status")
def status():
    order_id = request.args.get("order_id")
    if not order_id:
        return _page("""
<h2>Estado de pedido</h2>
<form method="get">
  <input name="order_id" placeholder="ID de pedido">
  <button type="submit">Consultar</button>
</form>""")
    try:
        r = requests.post(API_URL, data={"key": API_KEY, "action": "status", "order": order_id}, timeout=25)
        data = r.json()
        body = f"""
<h3>Pedido {order_id}</h3>
<p>Estado: <b>{data.get('status')}</b></p>
<p>Inicio: {data.get('start_count')}</p>
<p>Restantes: {data.get('remains')}</p>
<p>Cargo: {data.get('charge')}</p>
"""
    except Exception as e:
        body = f"<p class='err'>Error consultando estado: {e}</p>"
    return _page(body)

@app.route("/balance")
def balance():
    try:
        r = requests.post(API_URL, data={"key": API_KEY, "action": "balance"}, timeout=25)
        data = r.json()
        body = f"<h3>Saldo</h3><p>Balance: <b>{data.get('balance')}</b> {data.get('currency','')}</p>"
    except Exception as e:
        body = f"<p class='err'>Error consultando saldo: {e}</p>"
    return _page(body)

@app.route("/admin")
def admin():
    return _page("<h2>Panel Admin</h2><p>(en construcción)</p>")