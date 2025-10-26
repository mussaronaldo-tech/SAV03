import os
import requests
from flask import (
    Flask, render_template, request, redirect, url_for, session, flash
)

# ---------- Configuración ----------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esta-clave-super-segura")

API_URL = "https://peakerr.com/api/v2"
API_KEY = os.environ.get("PEAKERR_API_KEY", "").strip()

ADMIN_USER = os.environ.get("ADMIN_USER", "admin").strip()
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin12345").strip()


# ---------- Helper API ----------
def smm_post(payload: dict):
    """Llama a la API de Peakerr y devuelve (data, error)."""
    if not API_KEY:
        return None, "Falta PEAKERR_API_KEY en variables de entorno."

    data = {"key": API_KEY}
    data.update(payload)

    try:
        r = requests.post(API_URL, data=data, timeout=25)
        r.raise_for_status()
        # La API suele devolver JSON
        return r.json(), None
    except Exception as e:
        return None, f"Error llamando a la API: {e}"


# ---------- Rutas públicas ----------
@app.route("/", methods=["GET", "POST"])
def index():
    """Home: crear pedido usando index.html"""
    created_id = None
    error = None

    if request.method == "POST":
        # Admitimos ambos nombres por si el formulario usa uno u otro
        service_id = (request.form.get("service_id") or request.form.get("service") or "").strip()
        link       = (request.form.get("link") or "").strip()
        quantity   = (request.form.get("quantity") or "").strip()

        if not service_id or not link or not quantity:
            error = "Por favor completa todos los campos."
        else:
            payload = {"action": "add", "service": service_id, "link": link, "quantity": quantity}
            data, err = smm_post(payload)
            if err:
                error = err
            else:
                created_id = data.get("order") or data.get("order_id")
                if not created_id:
                    error = f"Respuesta inesperada de la API: {data}"

    return render_template("index.html", created_id=created_id, error=error)


@app.route("/services")
def services():
    """Listado de servicios -> services.html"""
    services_list = []
    error = None

    data, err = smm_post({"action": "services"})
    if err:
        error = err
    else:
        if isinstance(data, list):
            services_list = data
        elif isinstance(data, dict):
            # Por si alguna vez viene envuelto
            services_list = data.get("services") or data.get("data") or []

    return render_template("services.html", services=services_list, error=error)


@app.route("/status")
def status():
    """Estado de pedido -> status.html (usa ?order_id=XXXX)"""
    order_id = (request.args.get("order_id") or "").strip()
    result = None
    error = None

    if order_id:
        data, err = smm_post({"action": "status", "order": order_id})
        if err:
            error = err
        else:
            result = data

    # Pasamos 'result' y también 'data' por compatibilidad con plantillas antiguas
    return render_template("status.html", order_id=order_id, result=result, data=result, error=error)


@app.route("/balance")
def balance():
    """Balance -> balance.html"""
    balance_value, currency, error = None, None, None
    data, err = smm_post({"action": "balance"})
    if err:
        error = err
    else:
        if isinstance(data, dict):
            balance_value = data.get("balance")
            currency = data.get("currency")

    # Pasamos 'balance' y 'currency' y también 'data' por compatibilidad
    return render_template("balance.html", balance=balance_value, currency=currency, data=data if not err else None, error=error)


# ---------- Admin (login + panel) ----------
# Importante: endpoint="admin" para que url_for('admin') en tus plantillas funcione
@app.route("/admin", methods=["GET", "POST"], endpoint="admin")
def admin_login():
    error = None
    if request.method == "POST":
        user = (request.form.get("username") or request.form.get("user") or "").strip()
        pwd  = (request.form.get("password") or "").strip()
        if user == ADMIN_USER and pwd == ADMIN_PASS:
            session["admin"] = True
            session["admin_name"] = user
            return redirect(url_for("admin_panel"))
        error = "Usuario o contraseña incorrectos."
    return render_template("admin_login.html", error=error)

@app.route("/admin/panel", endpoint="admin_panel")
def admin_panel():
    if not session.get("admin"):
        return redirect(url_for("admin"))
    return render_template("admin.html")

@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin"))


# ---------- Aliases en español (por si tus menús enlazan así) ----------
@app.route("/pedido", methods=["GET", "POST"])
def pedido():
    # reutiliza la misma lógica/plantilla del index
    return index()

@app.route("/servicios")
def servicios():
    return redirect(url_for("services"))

@app.route("/estado")
def estado():
    return redirect(url_for("status"))

@app.route("/saldo")
def saldo():
    return redirect(url_for("balance"))


# ---------- Healthcheck ----------
@app.route("/healthz")
def healthz():
    return "OK", 200


# ---------- Local (no usado en Koyeb) ----------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)