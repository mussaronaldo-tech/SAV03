import os
import requests
from flask import (
    Flask, render_template, request,
    redirect, url_for, session, flash
)

# =========================
# Configuración de la app
# =========================
app = Flask(__name__)

# Clave de sesión (usa FLASK_SECRET o SECRET_KEY)
app.secret_key = (
    os.environ.get("FLASK_SECRET")
    or os.environ.get("SECRET_KEY")
    or "change-me"
)

# PeakerR API
API_URL = "https://peakerr.com/api/v2"
API_KEY = os.environ.get("PEAKERR_API_KEY", "")

# Credenciales de admin (puedes fijarlas por variables de entorno)
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASSWORD", "admin123")


# =========================
# Helpers
# =========================
def smm_post(payload: dict):
    """Llama a la API de PeakerR y devuelve (ok, data|mensaje_error)."""
    if not API_KEY:
        return False, "Falta la variable de entorno PEAKERR_API_KEY."
    data = {"key": API_KEY}
    data.update(payload)
    try:
        r = requests.post(API_URL, data=data, timeout=20)
        r.raise_for_status()
        # A veces la API devuelve texto simple; intentamos json con fallback
        try:
            return True, r.json()
        except Exception:
            return True, {"raw": r.text}
    except Exception as e:
        return False, f"Error llamando a la API: {e}"


def require_admin():
    if not session.get("is_admin"):
        return redirect(url_for("admin_login"))
    return None


# =========================
# Rutas públicas
# =========================
@app.route("/", methods=["GET", "POST"])
def index():
    """Crear pedido."""
    created_id = None
    error = None

    if request.method == "POST":
        service_id = (request.form.get("service_id") or "").strip()
        link = (request.form.get("link") or "").strip()
        quantity = (request.form.get("quantity") or "").strip()

        if not service_id or not link or not quantity:
            error = "Completa todos los campos."
        else:
            ok, data = smm_post({
                "action": "add",
                "service": service_id,
                "link": link,
                "quantity": quantity,
            })
            if ok:
                created_id = (data.get("order")
                              or data.get("order_id")
                              or data.get("raw")
                              or "?")
            else:
                error = data

    return render_template("index.html", created_id=created_id, error=error)


@app.get("/services")
def services():
    """Lista de servicios desde la API."""
    q = (request.args.get("q") or "").strip().lower()
    ok, data = smm_post({"action": "services"})
    items = []
    if ok and isinstance(data, list):
        items = data
    elif ok and isinstance(data, dict) and "raw" in data:
        # Algunas APIs devuelven string; no lo parseamos aquí
        flash("La API devolvió un formato no estándar.", "warning")
    else:
        flash(str(data), "danger")

    # Filtro rápido por nombre si el template lo usa
    if q:
        def _match(s):
            name = str(s.get("name", "")).lower()
            return q in name
        items = [s for s in items if _match(s)]

    return render_template("services.html", services=items, q=q)


@app.get("/status")
def status_view():
    """Consulta de estado por order_id."""
    order_id = (request.args.get("order_id") or "").strip()
    result = None
    error = None

    if order_id:
        ok, data = smm_post({"action": "status", "order": order_id})
        if ok:
            result = data
        else:
            error = data

    return render_template("status.html", result=result, error=error, order_id=order_id)


@app.get("/balance")
def balance_view():
    """Muestra balance de la cuenta en PeakerR."""
    ok, data = smm_post({"action": "balance"})
    if ok:
        balance = data.get("balance")
        currency = data.get("currency", "")
        return render_template("balance.html", balance=balance, currency=currency)
    flash(str(data), "danger")
    return render_template("balance.html", balance=None, currency=None)


# =========================
# Admin
# =========================
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    error = None
    if request.method == "POST":
        u = (request.form.get("username") or "").strip()
        p = (request.form.get("password") or "").strip()
        if u == ADMIN_USER and p == ADMIN_PASS:
            session["is_admin"] = True
            return redirect(url_for("admin"))  # endpoint admin definido abajo
        error = "Usuario o contraseña incorrectos."
    return render_template("admin_login.html", error=error)


@app.get("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))


# Forzamos el endpoint a llamarse 'admin' para que url_for('admin') funcione en las plantillas
@app.route("/admin", endpoint="admin")
def admin_panel():
    maybe_redirect = require_admin()
    if maybe_redirect:
        return maybe_redirect
    # Aquí en el futuro puedes pasar datos (últimos pedidos, métricas, etc.)
    return render_template("admin.html")


# =========================
# Healthcheck (¡una sola vez!)
# =========================
@app.get("/healthz")
def healthcheck():
    return "ok", 200


# =========================
# Arranque local (opcional)
# =========================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)