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