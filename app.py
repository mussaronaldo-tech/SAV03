import os
import logging
import traceback
import requests
from flask import (
    Flask, render_template, request, redirect, url_for, session
)

# -------------------- Config básica
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

API_URL  = "https://peakerr.com/api/v2"
API_KEY  = os.environ.get("PEAKERR_API_KEY", "")  # <- variable de entorno
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin123!X")

# Log a stdout (para ver errores en Koyeb)
logging.basicConfig(level=logging.INFO)

def smm_post(payload: dict):
    """Llama a la API de Peakerr y devuelve (data, error)."""
    if not API_KEY:
        return None, "Falta PEA KERR_API_KEY en variables de entorno."
    try:
        data = {"key": API_KEY}
        data.update(payload)
        r = requests.post(API_URL, data=data, timeout=20)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        logging.error("Error llamando a API: %s", e)
        logging.error(traceback.format_exc())
        return None, f"Error llamando a la API: {e}"

# -------------------- Rutas públicas
@app.route("/", methods=["GET", "POST"])
def index():
    """Formulario principal: crear pedido (mismo contenido que pedido.html)."""
    created_id = None
    error = None
    if request.method == "POST":
        service_id = (request.form.get("service_id") or "").strip()
        link      = (request.form.get("link") or "").strip()
        quantity  = (request.form.get("quantity") or "").strip()
        if not (service_id and link and quantity):
            error = "Completa todos los campos."
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
                created_id = data.get("order") or data.get("order_id") or data.get("data") or "?"
    return render_template("index.html", created_id=created_id, error=error)

@app.route("/pedido", methods=["GET", "POST"])
def pedido():
    # Misma lógica que index, por si usas /pedido en el menú
    return index()

@app.route("/services")
@app.route("/servicios")
def services():
    data, err = smm_post({"action": "services"})
    services_list = data if isinstance(data, list) else []
    return render_template("services.html", services=services_list, error=err)

@app.route("/status", methods=["GET"])
def status():
    order_id = (request.args.get("order_id") or "").strip()
    if not order_id:
        return render_template("status.html", data=None, error=None)
    data, err = smm_post({"action": "status", "order": order_id})
    return render_template("status.html", data=data or {}, error=err)

@app.route("/balance")
def balance():
    data, err = smm_post({"action": "balance"})
    bal = None if not isinstance(data, dict) else data.get("balance")
    return render_template("balance.html", balance=bal, error=err)

# -------------------- Admin (muy simple)
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        u = request.form.get("username", "")
        p = request.form.get("password", "")
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("admin_panel"))
        error = "Credenciales incorrectas."
    return render_template("admin_login.html", error=error)

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

@app.route("/admin")
def admin_panel():
    if not session.get("admin"):
        return redirect(url_for("admin_login"))
    return render_template("admin.html")

# -------------------- Salud y errores
@app.route("/health")
def health():
    return {"ok": True}, 200

@app.errorhandler(500)
def handle_500(e):
    logging.error("Error 500: %s", e)
    logging.error(traceback.format_exc())
    return render_template("index.html", created_id=None,
                           error="Ocurrió un error inesperado."), 500

# Nota: en Koyeb no necesitamos app.run(); Gunicorn lo arranca con Procfile.