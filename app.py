import os
import requests
from flask import (
    Flask, render_template, request, redirect, url_for, session, flash
)

# -------------------- Configuración básica --------------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "cambia-esta-clave-super-segura")

API_URL = "https://peakerr.com/api/v2"
API_KEY = os.environ.get("PEAKERR_API_KEY", "")

ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "admin12345")


# -------------------- Helper para llamar a la API --------------------
def smm_post(payload: dict):
    """
    Llama a la API de Peakerr y devuelve (data, error).
    Si hay error, data será None y error contendrá el mensaje.
    """
    if not API_KEY:
        return None, "Falta PEAKERR_API_KEY en variables de entorno."

    data = {"key": API_KEY}
    data.update(payload)

    try:
        r = requests.post(API_URL, data=data, timeout=20)
        r.raise_for_status()
        return r.json(), None
    except Exception as e:
        return None, f"Error llamando a la API: {e}"


# ==================== Rutas públicas ====================

@app.route("/", methods=["GET", "POST"])
def index():
    """
    Página principal: crear pedido.
    La plantilla puede mostrar 'created_id' o 'error' si existen.
    """
    created_id = None
    error = None

    if request.method == "POST":
        service_id = (request.form.get("service_id") or "").strip()
        link = (request.form.get("link") or "").strip()
        quantity = (request.form.get("quantity") or "").strip()

        # Validación mínima
        if not service_id or not link or not quantity:
            error = "Por favor completa todos los campos."
        else:
            payload = {
                "action": "add",
                "service": service_id,
                "link": link,
                "quantity": quantity
            }
            data, err = smm_post(payload)
            if err:
                error = err
            else:
                # La API suele devolver: {"order": 1234567, ...}
                created_id = data.get("order") or data.get("order_id")

                if not created_id:
                    # Algo inesperado en la respuesta
                    error = f"Respuesta de API inesperada: {data}"

    return render_template("index.html", created_id=created_id, error=error)


@app.route("/services")
def services():
    """
    Lista de servicios (si tu plantilla lo usa).
    """
    data, err = smm_post({"action": "services"})
    if err:
        flash(err, "error")
        services_list = []
    else:
        # La API devuelve lista o dict con 'data'
        services_list = data if isinstance(data, list) else data.get("data", [])
    return render_template("services.html", services=services_list)


@app.route("/status", methods=["GET"])
def status():
    """
    Consulta de estado por order_id (vía querystring ?order_id=XXXX).
    La plantilla puede leer 'order_id' y 'result'.
    """
    order_id = (request.args.get("order_id") or "").strip()
    result = None
    error = None

    if order_id:
        data, err = smm_post({"action": "status", "order": order_id})
        if err:
            error = err
        else:
            result = data

    return render_template("status.html", order_id=order_id, result=result, error=error)


@app.route("/balance")
def balance():
    """
    Muestra el balance de tu cuenta Peakerr.
    """
    data, err = smm_post({"action": "balance"})
    if err:
        flash(err, "error")
        bal, curr = None, None
    else:
        bal = data.get("balance")
        curr = data.get("currency")
    return render_template("balance.html", balance=bal, currency=curr)


# ==================== Admin (login + panel) ====================
# IMPORTANTE: endpoint="admin" para que tus plantillas con url_for('admin') NO fallen
@app.route("/admin", methods=["GET", "POST"], endpoint="admin")
def admin_login():
    """
    Login de administrador.
    Si es correcto, guarda session['admin']=True y redirige al panel.
    """
    error = None
    if request.method == "POST":
        user = (request.form.get("username") or "").strip()
        pwd = (request.form.get("password") or "").strip()
        if user == ADMIN_USER and pwd == ADMIN_PASS:
            session["admin"] = True
            return redirect(url_for("admin_panel"))
        else:
            error = "Usuario o contraseña incorrectos."

    return render_template("admin_login.html", error=error)


@app.route("/admin/panel", endpoint="admin_panel")
def admin_panel():
    """
    Panel sencillo de admin (protegido).
    """
    if not session.get("admin"):
        return redirect(url_for("admin"))
    return render_template("admin.html")


@app.route("/logout")
def logout():
    session.pop("admin", None)
    return redirect(url_for("admin"))


# -------------------- Healthcheck --------------------
@app.route("/healthz")
def healthz():
    return "OK", 200


# -------------------- Local dev --------------------
if __name__ == "__main__":
    # Para correr localmente (en Koyeb/Render se usa Gunicorn desde Procfile)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))