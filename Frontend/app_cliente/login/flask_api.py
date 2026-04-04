import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


def api_request(path, method="GET", payload=None, query=None):
    base_url = settings.FLASK_API_URL.rstrip("/")
    resource = path.lstrip("/")
    url = f"{base_url}/{resource}"

    if query:
        params = {
            key: value
            for key, value in query.items()
            if value not in (None, "")
        }
        if params:
            url = f"{url}?{urlencode(params)}"

    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = Request(url, data=data, headers=headers, method=method.upper())

    try:
        with urlopen(request, timeout=settings.FLASK_API_TIMEOUT) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {"ok": True}
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            payload = {}
        return {
            "ok": False,
            "status_code": exc.code,
            "message": payload.get("message") or f"Flask respondio con error {exc.code}.",
        }
    except URLError:
        return {
            "ok": False,
            "message": (
                "No se pudo conectar con la API Flask. "
                "Verifica que el backend este corriendo en http://127.0.0.1:5000."
            ),
        }
    except Exception as exc:  # pragma: no cover - fallback defensivo
        return {
            "ok": False,
            "message": f"Ocurrio un error inesperado al llamar a Flask: {exc}",
        }
