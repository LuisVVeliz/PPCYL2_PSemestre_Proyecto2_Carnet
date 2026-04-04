@app.route("/")
def home():
    return jsonify({
        "estado": "Flask API funcionando"
    })


from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/login", methods=["GET"])
def login():
    return jsonify({
        "mensaje": "Endpoint de login funcionando"
    })

@app.route("/admin", methods=["GET"])
def admin():
    return jsonify({
        "rol": "admin",
        "mensaje": "Datos del dashboard de administrador"
    })

@app.route("/tutor", methods=["GET"])
def tutor():
    return jsonify({
        "rol": "tutor",
        "mensaje": "Datos del dashboard de tutor"
    })

@app.route("/estudiante", methods=["GET"])
def estudiante():
    return jsonify({
        "rol": "estudiante",
        "mensaje": "Datos del dashboard de estudiante"
    })

if __name__ == "__main__":
    app.run(debug=True)