from flask import Flask, jsonify

from rutas.endpoints import rutas

app = Flask(__name__)
app.register_blueprint(rutas, url_prefix="/api")


@app.route("/")
def home():
    return jsonify({
        "status": "Flask funcionando",
        "api": "/api",
    })


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
