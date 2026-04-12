from pathlib import Path
import xml.etree.ElementTree as ET

from django.shortcuts import redirect, render

from .flask_api import api_request

ADMIN_USERNAME = "AdminPPCYL2"
ADMIN_PASSWORD = "AdminPPCYL2771"
ALLOWED_TUTOR_UPLOAD_EXTENSIONS = {".xml", ".txt"}


def _decode_uploaded_xml(uploaded_file):
    return uploaded_file.read().decode("utf-8", errors="replace")


def _preview_text(value, limit=100):
    return value[:limit].replace("\r", "\\r").replace("\n", "\\n")


def _prepare_tutor_xml_upload(uploaded_file, scope):
    if uploaded_file is None:
        return {
            "ok": False,
            "message": "Debes seleccionar un archivo .xml o .txt.",
        }

    filename = uploaded_file.name or ""
    extension = Path(filename).suffix.lower()
    raw_content = uploaded_file.read()
    decoded_content = raw_content.decode("utf-8", errors="replace")
    preview = _preview_text(decoded_content)

    print(
        f"[DJANGO UPLOAD][{scope}] "
        f"nombre={filename!r} "
        f"extension={extension!r} "
        f"bytes={len(raw_content)} "
        f"preview={preview!r}"
    )

    if not filename:
        return {
            "ok": False,
            "message": "El archivo seleccionado no tiene nombre.",
        }

    if extension not in ALLOWED_TUTOR_UPLOAD_EXTENSIONS:
        return {
            "ok": False,
            "message": "Solo se permiten archivos .xml o .txt para esta carga.",
        }

    xml_content = decoded_content.lstrip("\ufeff").strip()
    if not xml_content:
        return {
            "ok": False,
            "message": "El archivo esta vacio.",
        }

    try:
        ET.fromstring(xml_content)
    except ET.ParseError as exc:
        return {
            "ok": False,
            "message": f"El archivo {filename} no contiene XML valido: {exc}",
        }

    return {
        "ok": True,
        "filename": filename,
        "extension": extension,
        "xml_content": xml_content,
    }


def _require_role(request, role):
    if request.session.get("role") != role:
        return redirect("login")
    return None


def _catalogo():
    response = api_request("catalogo")
    if response.get("ok"):
        return response
    return {"cursos": [], "actividades_por_curso": {}, "message": response.get("message", "")}


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "").strip()

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            request.session["user"] = username
            request.session["role"] = "admin"
            return redirect("admin_panel")

        response = api_request(
            "login",
            method="POST",
            payload={"username": username, "password": password},
        )
        if response.get("ok"):
            user = response.get("user", {})
            request.session["user"] = user.get("username", username)
            request.session["role"] = user.get("role", "")
            request.session["nombre"] = user.get("nombre", user.get("username", username))
            request.session["carnet"] = user.get("carnet", user.get("username", username))

            print(
                "[DJANGO LOGIN] "
                f"usuario_autenticado={request.session.get('user', '')!r} "
                f"rol={request.session.get('role', '')!r} "
                f"carnet_sesion={request.session.get('carnet', '')!r}"
            )

            if user.get("role") == "admin":
                return redirect("admin_panel")
            if user.get("role") == "tutor":
                return redirect("tutor_horarios")
            if user.get("role") == "estudiante":
                return redirect("estudiante_notas")

        return render(request, "login/login.html", {
            "error": response.get("message", "Usuario o contrasena incorrectos."),
        })

    return render(request, "login/login.html")


def logout_view(request):
    request.session.flush()
    return redirect("login")


def admin_panel(request):
    guard = _require_role(request, "admin")
    if guard:
        return guard
    return render(request, "login/admin/admin.html")


def cargar_xml(request):
    guard = _require_role(request, "admin")
    if guard:
        return guard

    context = {
        "xml_entrada": "",
        "xml_salida": "",
        "mensaje": "",
        "error": "",
    }

    if request.method == "GET":
        response = api_request("admin/cargar-xml")
    elif "limpiar" in request.POST:
        response = api_request("admin/cargar-xml", method="POST", payload={"action": "clear"})
    elif "procesar" in request.POST:
        response = api_request(
            "admin/cargar-xml",
            method="POST",
            payload={
                "action": "process",
                "xml_content": request.POST.get("xml_entrada", ""),
            },
        )
    elif "archivo_xml" in request.FILES:
        uploaded_file = request.FILES["archivo_xml"]
        response = api_request(
            "admin/cargar-xml",
            method="POST",
            payload={
                "action": "upload",
                "filename": uploaded_file.name,
                "xml_content": _decode_uploaded_xml(uploaded_file),
            },
        )
    else:
        response = {
            "ok": False,
            "message": "Debes seleccionar un archivo XML o escribir contenido para procesar.",
        }

    context["xml_entrada"] = response.get("xml_input", "")
    context["xml_salida"] = response.get("xml_output", "")
    if response.get("ok"):
        context["mensaje"] = response.get("message", "")
    else:
        context["error"] = response.get("message", "")

    return render(request, "login/admin/cargar_xml.html", context)


def ver_usuarios(request):
    guard = _require_role(request, "admin")
    if guard:
        return guard

    response = api_request("admin/usuarios")
    return render(request, "login/admin/ver_usuarios.html", {
        "usuarios": response.get("usuarios", []),
        "error": "" if response.get("ok") else response.get("message", ""),
    })


def informacion(request):
    guard = _require_role(request, "admin")
    if guard:
        return guard

    return render(request, "login/admin/informacion.html", {
        "nombre_completo": "Proyecto PPCYL2",
        "carnet": request.session.get("user", ""),
        "documentacion_url": "Repositorio local",
    })


def tutor_horarios(request):
    guard = _require_role(request, "tutor")
    if guard:
        return guard

    if request.method == "POST":
        uploaded_file = request.FILES.get("archivo_xml")
        upload_data = _prepare_tutor_xml_upload(uploaded_file, "tutor_horarios")
        if upload_data.get("ok"):
            response = api_request(
                "tutor/horarios",
                method="POST",
                payload={
                    "filename": upload_data["filename"],
                    "xml_content": upload_data["xml_content"],
                },
            )
        else:
            response = {
                "ok": False,
                "message": upload_data["message"],
                "filename": uploaded_file.name if uploaded_file else "",
            }
    else:
        response = api_request("tutor/horarios")

    print(f"[DJANGO HORARIOS] estructura final al template: {response.get('horarios', [])}")

    return render(request, "login/tutor/tutor_horarios.html", {
        "horarios": response.get("horarios", []),
        "archivo": response.get("filename", ""),
        "mensaje": response.get("message", "") if response.get("ok") else "",
        "error": response.get("message", "") if not response.get("ok") else "",
    })


def tutor_notas(request):
    guard = _require_role(request, "tutor")
    if guard:
        return guard

    response = {"ok": True, "filename": "", "message": ""}
    if request.method == "POST":
        uploaded_file = request.FILES.get("archivo_xml")
        upload_data = _prepare_tutor_xml_upload(uploaded_file, "tutor_notas")
        if upload_data.get("ok"):
            response = api_request(
                "tutor/notas",
                method="POST",
                payload={
                    "filename": upload_data["filename"],
                    "xml_content": upload_data["xml_content"],
                },
            )
        else:
            response = {
                "ok": False,
                "message": upload_data["message"],
                "filename": uploaded_file.name if uploaded_file else "",
            }

    return render(request, "login/tutor/tutor_notas.html", {
        "archivo": response.get("filename", ""),
        "mensaje": response.get("message", "") if response.get("ok") else "",
        "error": response.get("message", "") if not response.get("ok") else "",
    })


def tutor_reporte_promedio(request):
    guard = _require_role(request, "tutor")
    if guard:
        return guard

    import plotly.graph_objects as go
    import plotly.offline as opy

    catalogo = _catalogo()
    curso = request.POST.get("curso", "").strip()
    response = {"ok": False}
    grafico_html = None

    if request.method == "POST" and curso:
        response = api_request(
            "reportes/promedio",
            method="POST",
            payload={"curso": curso},
        )

        # Si hay datos, generar el gráfico
        if response.get("ok"):
            actividades = response.get("actividades", [])
            if actividades:
                # Extraer nombres y promedios
                nombres = [act['actividad'] for act in actividades]
                promedios = [act['promedio'] for act in actividades]

                # Crear gráfico de barras
                fig = go.Figure(data=[
                    go.Bar(
                        x=nombres,
                        y=promedios,
                        marker_color='skyblue',
                        text=promedios,
                        textposition='auto'
                    )
                ])

                fig.update_layout(
                    title=f"Promedio de Notas - Curso {curso}",
                    xaxis_title="Actividades",
                    yaxis_title="Promedio",
                    yaxis_range=[0, 100],
                    template='plotly_white',
                    height=450
                )

                grafico_html = opy.plot(fig, output_type='div', include_plotlyjs='cdn')

    return render(request, "login/tutor/tutor_reporte_promedio.html", {
        "cursos": catalogo.get("cursos", []),
        "curso_seleccionado": curso,
        "mostrar": response.get("ok", False),
        "reporte": response if response.get("ok") else {},
        "grafico": grafico_html,  # ← Nueva variable para el gráfico
        "error": response.get("message", "") if request.method == "POST" and not response.get("ok") else catalogo.get("message", ""),
    })


def tutor_top_notas(request):
    guard = _require_role(request, "tutor")
    if guard:
        return guard

    import plotly.graph_objects as go
    import plotly.offline as opy

    catalogo = _catalogo()
    curso = request.POST.get("curso", "").strip()
    actividad = request.POST.get("actividad", "").strip()
    actividades_por_curso = catalogo.get("actividades_por_curso", {})
    actividades = actividades_por_curso.get(curso, [])
    response = {"ok": False}
    grafico_html = None

    if request.method == "POST" and curso and actividad:
        response = api_request(
            "reportes/top-notas",
            method="POST",
            payload={"curso": curso, "actividad": actividad},
        )

        # Si hay datos, generar el gráfico
        if response.get("ok"):
            top = response.get("top", [])
            if top:
                # Extraer estudiantes y notas
                estudiantes = [item['estudiante'] for item in top]
                notas = [item['valor'] for item in top]

                # Crear gráfico de barras horizontal
                fig = go.Figure(data=[
                    go.Bar(
                        x=notas,
                        y=estudiantes,
                        orientation='h',
                        marker_color='coral',
                        text=notas,
                        textposition='outside'
                    )
                ])

                fig.update_layout(
                    title=f"TOP Notas - {actividad} (Curso {curso})",
                    xaxis_title="Nota",
                    yaxis_title="Estudiante",
                    xaxis_range=[0, 100],
                    template='plotly_white',
                    height=400
                )

                grafico_html = opy.plot(fig, output_type='div', include_plotlyjs='cdn')

    return render(request, "login/tutor/tutor_top_notas.html", {
        "cursos": catalogo.get("cursos", []),
        "actividades": actividades,
        "curso_seleccionado": curso,
        "actividad_seleccionada": actividad,
        "mostrar": response.get("ok", False),
        "reporte": response if response.get("ok") else {},
        "grafico": grafico_html,  # ← Nueva variable para el gráfico
        "error": response.get("message", "") if request.method == "POST" and not response.get("ok") else catalogo.get("message", ""),
    })

def estudiante_notas(request):
    guard = _require_role(request, "estudiante")
    if guard:
        return guard

    student_username = request.session.get("user", "")
    student_carnet = request.session.get("carnet", "")
    curso = request.POST.get("curso", "").strip()
    response = api_request(
        "estudiante/notas",
        method="POST",
        payload={
            "username": student_username,
            "carnet": student_carnet,
            "curso": curso,
        },
    )
    cursos = response.get("cursos_disponibles", [])
    notas = []
    error = ""

    print(
        "[DJANGO ESTUDIANTE] "
        f"usuario={student_username!r} "
        f"carnet={student_carnet!r} "
        f"curso_seleccionado={curso!r}"
    )
    print(f"[DJANGO ESTUDIANTE] respuesta_flask={response}")

    if response.get("ok"):
        notas = response.get("notas", []) if request.method == "POST" else []
        if request.method == "POST" and not notas:
            error = response.get("message", "")
        elif request.method == "GET" and not cursos:
            error = "No hay cursos con notas disponibles para este estudiante."
    else:
        error = response.get("message", "")

    return render(request, "login/estudiante/estudiante_notas.html", {
        "notas": notas,
        "cursos": cursos,
        "curso_seleccionado": curso,
        "error": error,
    })
