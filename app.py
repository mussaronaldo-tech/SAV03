import os
import requests
from flask import Flask, render_template, request, redirect, url_for, session

# --- Configuración básica
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esta-clave")

API_URL = "https://peakerr.com/api/v2"
API_KEY = os.environ.get("PEAKERR_API_KEY", "")

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123")

def smm_post(payload: dict):
    """Helper: llama a la API de Peakerr y devuelve (data, error)."""
    if not API_KEY:
        return None, "Falta PEAKERR_API_KEY en variables de entorno."
    data = {"key": API_KEY}
    data.update(payload)
    try:
        r = requests.post(API_URL, data=data, timeout=25)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, f"Error llamando a la API: {e}"

# ---------- Rutas públicas

@app.route("/", methods=["GET", "POST"])
def index():
    """Crear pedido."""
    created_id = None
    error = None

    if request.method == "POST":
        service_id = request.form.get("service_id", "").strip()
        link = request.form.get("link", "").strip()
        quantity = request.form.get("quantity", "").strip()

        if not service_id or not link or not quantity:
            error = "Rellena todos los campos."
        else:
            data, err = smm_post({
                "action": "add",
                "service": service_id,
                "link": link,
                "quantity": quantity
            })
            if err:
                error = err
            else:
                created_id = data.get("order") or data.get("order_id")
                if not created_id:
                    error = f"Respuesta inesperada: {data}"

    return render_template("pedido.html", created_id=created_id, error=error)

@app.route("/servicios")
def servicios():
    """Lista de servicios."""
    items, error = None, None
    data, err = smm_post({"action": "services"})
    if err:
        error = err
    else:
        items = data if isinstance(data, list) else None
        if items is None:
            error = f"Respuesta inesperada: {data}"
    return render_template("servicios.html", items=items, error=error)

@app.route("/estado")
def status():
    """Consultar estado por order_id (GET ?order_id=123)."""
    order_id = request.args.get("order_id", "").strip()
    data, error = None, None

    if order_id:
        data, err = smm_post({"action": "status", "order": order_id})
        if err:
            error = err
        elif not isinstance(data, dict):
            error = f"Respuesta inesperada: {data}"

    return render_template("estado.html", order_id=order_id, data=data, error=error)

@app.route("/saldo")
def balance():
    """Mostrar saldo de la API."""
    data, error = smm_post({"action": "balance"})
    if error:
        return render_template("saldo.html", data=None, error=error)
    return render_template("saldo.html", data=data, error=None)

# ---------- Admin (login muy simple)

@app.route("/admin", methods=["GET", "POST"])
def admin():
    if session.get("auth"):
        # Panel (placeholder)
        return render_template("admin.html")

    error = None
    if request.method == "POST":
        u = request.form.get("user", "")
        p = request.form.get("password", "")
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["auth"] = True
            return redirect(url_for("admin"))
        error = "Usuario o contraseña incorrectos."
    return render_template("admin_login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# ---------- Healthcheck opcional
@app.route("/healthz")
def healthz():
    return "ok", 200