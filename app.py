from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return "<h1>Bienvenido a SAV03 🚀</h1><p>Tu panel está activo.</p>"

@app.route("/admin")
def admin():
    return "<h2>Panel Admin de SAV03</h2><p>Funcionalidad próximamente.</p>"
