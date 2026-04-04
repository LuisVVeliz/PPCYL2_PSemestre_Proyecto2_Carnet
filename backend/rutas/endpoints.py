from collections import defaultdict
from pathlib import Path
import re
from statistics import mean
import unicodedata
import xml.etree.ElementTree as ET

from flask import Blueprint, jsonify, request
from storage import load_state, save_state

rutas = Blueprint("rutas", __name__)

ROLE_ALIASES = {
    "admin": "admin",
    "administrador": "admin",
    "tutor": "tutor",
    "docente": "tutor",
    "teacher": "tutor",
    "estudiante": "estudiante",
    "student": "estudiante",
    "alumno": "estudiante",
}

DAY_ALIASES = {
    "lunes": "lunes",
    "martes": "martes",
    "miercoles": "miercoles",
    "jueves": "jueves",
    "viernes": "viernes",
}

USER_KEYS = [
    "usuario",
    "username",
    "user",
    "login",
    "correo",
    "email",
    "carnet",
    "codigo",
    "registro_personal",
]
PASSWORD_KEYS = ["password", "contrasena", "contrasenia", "pass", "clave"]
NAME_KEYS = ["nombre", "name", "nombres"]
ROLE_KEYS = ["rol", "role", "tipo", "perfil"]
CAREER_KEYS = ["carrera", "programa", "facultad"]
COURSE_KEYS = ["curso", "materia", "clase", "codigo", "nombre"]
ACTIVITY_KEYS = ["actividad", "evaluacion", "tarea", "examen", "nombre"]
GRADE_KEYS = ["nota", "valor", "calificacion", "punteo", "score", "puntos"]
STUDENT_KEYS = ["estudiante", "alumno", "carnet", "usuario", "user", "codigo"]
ALLOWED_TUTOR_UPLOAD_EXTENSIONS = {".xml", ".txt"}
TIME_RANGE_RE = re.compile(
    r"HorarioI\s*:\s*([0-2]?\d:\d{2})\s*HorarioF\s*:\s*([0-2]?\d:\d{2})",
    re.IGNORECASE,
)


def _empty_state():
    return {
        "admin_xml": "",
        "admin_output": "",
        "users": [],
        "horarios": [],
        "notas": [],
        "notas_indexadas": {},
        "last_horario_file": "",
        "last_notas_file": "",
    }


STATE = load_state(_empty_state())


def _persist_state():
    save_state(STATE, _empty_state())


def _normalize_key(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = text.encode("ascii", "ignore").decode("ascii")
    return "".join(char.lower() if char.isalnum() else "_" for char in text).strip("_")


def _normalize_role(value):
    return ROLE_ALIASES.get(_normalize_key(value), "")


def _local_tag(tag):
    return _normalize_key(str(tag).split("}", 1)[-1])


def _first_value(mapping, keys, default=""):
    for key in keys:
        value = mapping.get(_normalize_key(key), "")
        if value:
            return value
    return default


def _parse_xml(xml_content):
    content = (xml_content or "").strip()
    if not content:
        raise ValueError("No se recibio contenido XML.")
    try:
        root = ET.fromstring(content)
        print(f"[XML DEBUG] raiz detectada: {_local_tag(root.tag)}")
        return root
    except ET.ParseError as exc:
        raise ValueError(f"El XML es invalido: {exc}") from exc


def _preview_text(value, limit=100):
    return value[:limit].replace("\r", "\\r").replace("\n", "\\n")


def _compact_text(value):
    return " ".join(str(value or "").split())


def _log_tutor_upload(scope, filename, xml_content):
    extension = Path(str(filename or "")).suffix.lower()
    preview = _preview_text(str(xml_content or ""))
    size = len(str(xml_content or "").encode("utf-8"))
    print(
        f"[FLASK UPLOAD][{scope}] "
        f"nombre={filename!r} "
        f"extension={extension!r} "
        f"bytes={size} "
        f"preview={preview!r}"
    )
    return extension


def _parse_tutor_upload(filename, xml_content, scope):
    extension = _log_tutor_upload(scope, filename, xml_content)

    if not filename:
        raise ValueError("No se recibio el nombre del archivo.")

    if extension not in ALLOWED_TUTOR_UPLOAD_EXTENSIONS:
        raise ValueError("Solo se permiten archivos .xml o .txt.")

    if not str(xml_content or "").strip():
        raise ValueError("El archivo recibido esta vacio.")

    return _parse_xml(xml_content)


def _debug_tag_counts(root):
    counts = defaultdict(int)
    for element in root.iter():
        counts[_local_tag(element.tag)] += 1
    print(f"[XML DEBUG] nodos encontrados: {dict(sorted(counts.items()))}")


def _collect_values(element):
    values = {}

    def visit(node):
        tag = _local_tag(node.tag)
        text = (node.text or "").strip()
        if tag and text and tag not in values:
            values[tag] = text

        for raw_key, raw_value in node.attrib.items():
            key = _normalize_key(raw_key)
            value = str(raw_value).strip()
            if key and value and key not in values:
                values[key] = value
            if tag and key and value:
                prefixed = f"{tag}_{key}"
                if prefixed not in values:
                    values[prefixed] = value

        for child in node:
            visit(child)

    visit(element)
    return values


def _parse_number(value):
    text = str(value or "").strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _display_number(value):
    if value is None:
        return ""
    if float(value).is_integer():
        return int(value)
    return round(value, 2)


def _candidate_role(tag, values, username):
    role = _normalize_role(tag)
    if role:
        return role

    role = _normalize_role(_first_value(values, ROLE_KEYS))
    if role:
        return role

    lowered_username = str(username or "").lower()
    if lowered_username.startswith("tutor"):
        return "tutor"
    if lowered_username.startswith("estudiante"):
        return "estudiante"
    return ""


def _has_user_shape(element):
    tag = _local_tag(element.tag)
    if tag in ROLE_ALIASES or tag in {"usuario", "user", "persona"}:
        return True

    attribute_keys = {_normalize_key(key) for key in element.attrib}
    if attribute_keys.intersection(set(USER_KEYS + PASSWORD_KEYS + ROLE_KEYS)):
        return True

    child_tags = {_local_tag(child.tag) for child in element}
    return bool(child_tags.intersection(set(USER_KEYS + PASSWORD_KEYS + ROLE_KEYS)))


def _extract_users(root):
    users = []
    seen = set()

    for element in root.iter():
        if not _has_user_shape(element):
            continue

        values = _collect_values(element)
        username = _first_value(values, USER_KEYS)
        password = _first_value(values, PASSWORD_KEYS)
        role = _candidate_role(_local_tag(element.tag), values, username)

        if not username and role == "estudiante":
            username = _first_value(values, ["carnet", "registro", "codigo"])

        if not username and role == "tutor":
            username = _first_value(values, ["correo", "email", "nombre"])

        if not username or not password or not role:
            continue

        name = _first_value(values, NAME_KEYS) or values.get(_local_tag(element.tag), "")

        key = (role, username)
        if key in seen:
            continue
        seen.add(key)

        users.append({
            "id": _first_value(values, ["id", "carnet", "registro", "registro_personal", "codigo"]) or str(len(users) + 1),
            "usuario": username,
            "password": password,
            "role": role,
            "nombre": name or username,
            "carnet": _first_value(values, ["carnet", "registro", "registro_personal", "codigo"]),
            "carrera": _first_value(values, CAREER_KEYS),
        })

    print(f"[XML DEBUG] usuarios extraidos: {len(users)}")
    return users


def _extract_configuration_courses(root):
    courses = []

    for course in root.findall(".//cursos/curso"):
        code = str(course.attrib.get("codigo", "")).strip()
        name = (course.text or "").strip()
        if not code and not name:
            continue
        courses.append({
            "codigo": code,
            "nombre": name or f"Curso {code}" if code else "Curso",
        })

    return courses


def _extract_configuration_assignments(root):
    tutor_assignments = defaultdict(list)
    student_assignments = defaultdict(list)

    for item in root.findall(".//asignaciones/c_tutores/tutor_curso"):
        code = str(item.attrib.get("codigo", "")).strip()
        tutor_id = (item.text or "").strip()
        if code and tutor_id:
            tutor_assignments[code].append(tutor_id)

    for item in root.findall(".//asignaciones/c_estudiante/estudiante_curso"):
        code = str(item.attrib.get("codigo", "")).strip()
        student_id = (item.text or "").strip()
        if code and student_id:
            student_assignments[code].append(student_id)

    return tutor_assignments, student_assignments


def _extract_configuration_horarios(root):
    courses = _extract_configuration_courses(root)
    if not courses:
        return []

    tutor_names = {}
    student_names = {}

    for tutor in root.findall(".//tutores/tutor"):
        tutor_id = str(tutor.attrib.get("registro_personal", "")).strip()
        tutor_name = (tutor.text or "").strip()
        if tutor_id:
            tutor_names[tutor_id] = tutor_name

    for student in root.findall(".//estudiantes/estudiante"):
        student_id = str(student.attrib.get("carnet", "")).strip()
        student_name = (student.text or "").strip()
        if student_id:
            student_names[student_id] = student_name

    tutor_assignments, student_assignments = _extract_configuration_assignments(root)
    horarios = []

    for course in courses:
        code = course["codigo"]
        tutor_labels = [
            f"{tutor_id} - {tutor_names.get(tutor_id, '').strip()}".strip(" -")
            for tutor_id in tutor_assignments.get(code, [])
        ]
        student_labels = [
            f"{student_id} - {student_names.get(student_id, '').strip()}".strip(" -")
            for student_id in student_assignments.get(code, [])
        ]

        horarios.append({
            "nombre": f"{code} - {course['nombre']}".strip(" -"),
            "lunes": ", ".join(tutor_labels) or "Sin tutor asignado",
            "martes": f"{len(student_labels)} estudiante(s)",
            "miercoles": ", ".join(student_labels[:3]) or "Sin estudiantes",
            "jueves": "",
            "viernes": "",
        })

    print(
        "[XML DEBUG] configuraciones detectadas: "
        f"cursos={len(courses)}, "
        f"asignaciones_tutor={sum(len(items) for items in tutor_assignments.values())}, "
        f"asignaciones_estudiante={sum(len(items) for items in student_assignments.values())}"
    )
    return horarios


def _extract_text_only_horarios(root):
    cursos = root.findall("./curso")
    horarios = []

    print(f"[XML DEBUG] cursos encontrados en <horarios>: {len(cursos)}")

    for index, curso in enumerate(cursos, start=1):
        codigo = str(curso.attrib.get("codigo", "")).strip()
        raw_text = _compact_text(curso.text)
        match = TIME_RANGE_RE.search(raw_text)

        if match:
            horario_texto = f"{match.group(1)} - {match.group(2)}"
        else:
            horario_texto = raw_text

        row = {
            "nombre": codigo or f"Curso {index}",
            "lunes": horario_texto,
            "martes": horario_texto,
            "miercoles": horario_texto,
            "jueves": horario_texto,
            "viernes": horario_texto,
        }
        print(
            "[XML DEBUG] curso horario libre: "
            f"codigo={codigo!r} texto={raw_text!r} fila={row}"
        )
        horarios.append(row)

    print(f"[XML DEBUG] horarios/texto libre extraidos: {len(horarios)}")
    return horarios


def _has_schedule_shape(element):
    attribute_keys = {_normalize_key(key) for key in element.attrib}
    if any(key in DAY_ALIASES for key in attribute_keys):
        return True

    for child in element:
        child_tag = _local_tag(child.tag)
        if child_tag in DAY_ALIASES or child_tag == "dia":
            return True
    return False


def _extract_schedule_row(element, index):
    row = {
        "nombre": "",
        "lunes": "",
        "martes": "",
        "miercoles": "",
        "jueves": "",
        "viernes": "",
    }
    values = _collect_values(element)
    row["nombre"] = _first_value(values, COURSE_KEYS) or f"Curso {index}"

    for day, normalized_day in DAY_ALIASES.items():
        value = values.get(day, "")
        if value:
            row[normalized_day] = value

    for child in element:
        child_tag = _local_tag(child.tag)
        if child_tag in DAY_ALIASES:
            row[DAY_ALIASES[child_tag]] = (child.text or "").strip()
            continue

        if child_tag == "dia":
            day_name = _normalize_key(
                child.attrib.get("nombre")
                or child.attrib.get("name")
                or child.attrib.get("dia")
                or ""
            )
            mapped_day = DAY_ALIASES.get(day_name)
            if mapped_day:
                row[mapped_day] = (child.text or "").strip()

    return row


def _extract_horarios(root):
    if _local_tag(root.tag) == "configuraciones":
        horarios = _extract_configuration_horarios(root)
        print(f"[XML DEBUG] horarios/configuraciones extraidos: {len(horarios)}")
        return horarios

    horarios = []
    seen = set()

    for element in root.iter():
        if not _has_schedule_shape(element):
            continue

        row = _extract_schedule_row(element, len(horarios) + 1)
        key = (
            row["nombre"],
            row["lunes"],
            row["martes"],
            row["miercoles"],
            row["jueves"],
            row["viernes"],
        )
        if key in seen:
            continue
        seen.add(key)
        horarios.append(row)

    print(f"[XML DEBUG] horarios clasicos extraidos: {len(horarios)}")
    if horarios:
        return horarios

    if _local_tag(root.tag) == "horarios":
        return _extract_text_only_horarios(root)

    return horarios


def _has_grade_shape(element):
    attribute_keys = {_normalize_key(key) for key in element.attrib}
    if any(key in GRADE_KEYS for key in attribute_keys):
        return True

    child_tags = {_local_tag(child.tag) for child in element}
    return any(tag in GRADE_KEYS for tag in child_tags)


def _extract_datos_notas(root):
    course_node = root.find("./curso")
    course_code = ""
    course_name = ""

    if course_node is not None:
        course_code = str(course_node.attrib.get("codigo", "")).strip()
        course_name = _compact_text(course_node.text)

    print(
        "[XML DEBUG] curso encontrado en <datos>: "
        f"codigo={course_code!r} nombre={course_name!r}"
    )

    activities = root.findall("./notas/actividad")
    print(f"[XML DEBUG] actividades encontradas en <datos>/<notas>: {len(activities)}")

    course_label = course_code or course_name or "General"
    notas = []
    seen = set()

    for index, activity in enumerate(activities, start=1):
        activity_name = str(activity.attrib.get("nombre", "")).strip() or f"Actividad {index}"
        student = str(activity.attrib.get("carnet", "")).strip()
        raw_score = _compact_text(activity.text)
        score = _parse_number(raw_score)

        print(
            "[XML DEBUG] actividad detectada: "
            f"nombre={activity_name!r} carnet={student!r} nota={raw_score!r}"
        )

        if score is None:
            continue

        record = {
            "curso": course_label,
            "actividad": activity_name,
            "valor": _display_number(score),
            "valor_numerico": score,
            "estudiante": student,
        }
        key = (
            record["curso"],
            record["actividad"],
            record["estudiante"],
            record["valor_numerico"],
        )
        if key in seen:
            continue
        seen.add(key)
        notas.append(record)

    _log_unmatched_note_students(notas)
    print(f"[XML DEBUG] notas/<datos> extraidas: {len(notas)}")
    return notas


def _log_unmatched_note_students(notas):
    known_students = {
        _normalize_key(user.get("carnet") or user.get("usuario"))
        for user in STATE["users"]
        if user.get("role") == "estudiante"
    }
    if known_students:
        unmatched = sorted({
            note["estudiante"]
            for note in notas
            if _normalize_key(note.get("estudiante")) not in known_students
        })
        print(f"[XML DEBUG] carnets de notas sin estudiante registrado: {unmatched}")


def _extract_notas_tutor(root):
    tutor_id = str(root.attrib.get("registro_personal", "")).strip()
    print(f"[XML DEBUG] tutor detectado en <notas_tutor>: {tutor_id!r}")

    notas = []
    seen = set()
    current_course_code = ""
    current_course_name = ""
    course_count = 0
    notes_block_count = 0

    for child in list(root):
        child_tag = _local_tag(child.tag)

        if child_tag == "curso":
            course_count += 1
            current_course_code = str(child.attrib.get("codigo", "")).strip()
            current_course_name = _compact_text(child.text)
            print(
                "[XML DEBUG] curso detectado en <notas_tutor>: "
                f"codigo={current_course_code!r} nombre={current_course_name!r}"
            )
            continue

        if child_tag != "notas":
            continue

        notes_block_count += 1
        activities = child.findall("./actividad")
        print(
            "[XML DEBUG] bloque <notas> detectado: "
            f"curso_actual={current_course_code!r} "
            f"actividades={len(activities)}"
        )

        for index, activity in enumerate(activities, start=1):
            activity_name = str(activity.attrib.get("nombre", "")).strip() or f"Actividad {index}"
            student = str(activity.attrib.get("carnet", "")).strip()
            raw_score = _compact_text(activity.text)
            score = _parse_number(raw_score)

            print(
                "[XML DEBUG] actividad por curso: "
                f"curso={current_course_code!r} "
                f"nombre={activity_name!r} "
                f"carnet={student!r} "
                f"nota={raw_score!r}"
            )

            if score is None or not current_course_code:
                continue

            record = {
                "tutor": tutor_id,
                "curso": current_course_code,
                "curso_nombre": current_course_name,
                "actividad": activity_name,
                "valor": _display_number(score),
                "valor_numerico": score,
                "estudiante": student,
            }
            key = (
                record["tutor"],
                record["curso"],
                record["actividad"],
                record["estudiante"],
                record["valor_numerico"],
            )
            if key in seen:
                continue
            seen.add(key)
            notas.append(record)

    print(
        "[XML DEBUG] resumen <notas_tutor>: "
        f"tutor={tutor_id!r} "
        f"cursos_encontrados={course_count} "
        f"bloques_notas={notes_block_count}"
    )
    _log_unmatched_note_students(notas)
    print(f"[XML DEBUG] notas/<notas_tutor> extraidas: {len(notas)}")
    return notas


def _extract_notas(root):
    if _local_tag(root.tag) == "notas_tutor":
        return _extract_notas_tutor(root)

    if _local_tag(root.tag) == "datos" and root.findall("./notas/actividad"):
        return _extract_datos_notas(root)

    notas = []
    seen = set()

    for element in root.iter():
        if not _has_grade_shape(element):
            continue

        values = _collect_values(element)
        score = _parse_number(_first_value(values, GRADE_KEYS))
        if score is None:
            continue

        activity = _first_value(values, ACTIVITY_KEYS)
        tag_name = _local_tag(element.tag)
        if not activity and tag_name in {"actividad", "tarea", "examen", "nota", "calificacion"}:
            activity = tag_name.title()

        course = _first_value(values, COURSE_KEYS) or "General"
        student = _first_value(values, STUDENT_KEYS)

        record = {
            "curso": course,
            "actividad": activity or f"Actividad {len(notas) + 1}",
            "valor": _display_number(score),
            "valor_numerico": score,
            "estudiante": student,
        }
        key = (
            record["curso"],
            record["actividad"],
            record["estudiante"],
            record["valor_numerico"],
        )
        if key in seen:
            continue
        seen.add(key)
        notas.append(record)

    print(f"[XML DEBUG] notas extraidas: {len(notas)}")
    return notas


def _course_storage_key(value):
    text = str(value or "").strip()
    if not text:
        return ""
    if "-" in text:
        left, _right = text.split("-", 1)
        if left.strip():
            return _normalize_key(left.strip())
    return _normalize_key(text)


def _build_note_index(notas):
    index = {}

    for note in notas:
        student_key = _normalize_key(note.get("estudiante"))
        course_key = _course_storage_key(note.get("curso"))
        if not student_key or not course_key:
            continue

        index.setdefault(student_key, {}).setdefault(course_key, []).append({
            "tutor": note.get("tutor", ""),
            "curso": note.get("curso", ""),
            "curso_nombre": note.get("curso_nombre", ""),
            "actividad": note.get("actividad", ""),
            "valor": note.get("valor"),
            "valor_numerico": note.get("valor_numerico"),
            "estudiante": note.get("estudiante", ""),
        })

    print(f"[FLASK NOTAS] estructura_indexada={index}")
    return index


def _sync_note_storage():
    STATE["notas_indexadas"] = _build_note_index(STATE["notas"])


_sync_note_storage()


def _course_catalog():
    courses = {item["curso"] for item in STATE["notas"] if item.get("curso")}
    courses.update(item["nombre"] for item in STATE["horarios"] if item.get("nombre"))
    return sorted(courses)


def _activities_by_course():
    grouped = defaultdict(set)
    for nota in STATE["notas"]:
        grouped[nota["curso"]].add(nota["actividad"])
    return {
        curso: sorted(actividades)
        for curso, actividades in sorted(grouped.items())
    }


def _find_user(username):
    target = str(username or "").strip()
    for user in STATE["users"]:
        if user["usuario"] == target or str(user.get("carnet", "")).strip() == target:
            return user
    return None


def _student_aliases(username, carnet=""):
    user = _find_user(carnet) or _find_user(username)
    aliases = {_normalize_key(username), _normalize_key(carnet)}
    if user:
        aliases.add(_normalize_key(user.get("usuario")))
        aliases.add(_normalize_key(user.get("carnet")))
        aliases.add(_normalize_key(user.get("nombre")))
    aliases.discard("")
    return aliases


def _course_aliases(value):
    text = str(value or "").strip()
    aliases = {_normalize_key(text)}
    if text and "-" in text:
        left, right = text.split("-", 1)
        aliases.add(_normalize_key(left.strip()))
        aliases.add(_normalize_key(right.strip()))
    aliases.discard("")
    return aliases


def _student_available_courses(username="", carnet=""):
    aliases = _student_aliases(username, carnet)
    index = STATE.get("notas_indexadas", {})
    ordered_courses = []
    seen = set()

    for student_alias in sorted(aliases):
        student_bucket = index.get(student_alias, {})
        print(
            "[FLASK ESTUDIANTE] cursos_disponibles_bucket "
            f"alias={student_alias!r} datos={student_bucket}"
        )
        for notes in student_bucket.values():
            for note in notes:
                course_label = str(note.get("curso", "")).strip()
                course_key = _course_storage_key(course_label)
                if not course_label or course_key in seen:
                    continue
                seen.add(course_key)
                ordered_courses.append(course_label)

    print(
        "[FLASK ESTUDIANTE] cursos_disponibles "
        f"usuario={username!r} carnet={carnet!r} cursos={ordered_courses}"
    )
    return ordered_courses


def _filtered_student_notes(username, carnet="", curso=""):
    selected_course = str(curso or "").strip()
    aliases = _student_aliases(username, carnet)
    selected_course_aliases = _course_aliases(selected_course)
    index = STATE.get("notas_indexadas", {})
    filtered = []
    seen = set()

    for student_alias in sorted(aliases):
        student_bucket = index.get(student_alias, {})
        print(f"[FLASK ESTUDIANTE] bucket_estudiante alias={student_alias!r} datos={student_bucket}")

        if selected_course_aliases:
            course_candidates = sorted(selected_course_aliases)
        else:
            course_candidates = sorted(student_bucket.keys())

        for course_alias in course_candidates:
            notes = student_bucket.get(course_alias, [])
            if notes:
                print(
                    "[FLASK ESTUDIANTE] bucket_curso "
                    f"alias_estudiante={student_alias!r} "
                    f"alias_curso={course_alias!r} "
                    f"notas={notes}"
                )
            for note in notes:
                key = (
                    note.get("estudiante", ""),
                    note.get("curso", ""),
                    note.get("actividad", ""),
                    note.get("valor_numerico"),
                )
                if key in seen:
                    continue
                seen.add(key)
                filtered.append(note)

    print(
        "[FLASK ESTUDIANTE] filtro_notas "
        f"usuario={username!r} "
        f"carnet={carnet!r} "
        f"curso={selected_course!r} "
        f"aliases_estudiante={sorted(aliases)} "
        f"aliases_curso={sorted(selected_course_aliases)} "
        f"notas_encontradas={len(filtered)}"
    )
    return filtered


def _reset_state():
    STATE.clear()
    STATE.update(_empty_state())


@rutas.route("/test", methods=["GET"])
def test():
    return jsonify({"ok": True, "mensaje": "API funcionando"})


@rutas.route("/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    password = str(payload.get("password", "")).strip()

    if not username or not password:
        return jsonify({
            "ok": False,
            "message": "Debes enviar usuario y contrasena.",
        }), 400

    user = next(
        (
            item for item in STATE["users"]
            if item["usuario"] == username and item["password"] == password
        ),
        None,
    )
    if not user:
        return jsonify({
            "ok": False,
            "message": "Usuario o contrasena incorrectos en Flask.",
        }), 401

    return jsonify({
        "ok": True,
        "user": {
            "id": user["id"],
            "username": user["usuario"],
            "role": user["role"],
            "nombre": user["nombre"],
            "carnet": user["carnet"],
            "carrera": user["carrera"],
        },
    })


@rutas.route("/admin/cargar-xml", methods=["GET", "POST"])
def admin_cargar_xml():
    if request.method == "GET":
        return jsonify({
            "ok": True,
            "xml_input": STATE["admin_xml"],
            "xml_output": STATE["admin_output"],
        })

    payload = request.get_json(silent=True) or {}
    action = str(payload.get("action", "")).strip().lower()
    xml_content = payload.get("xml_content", "")

    if action == "clear":
        _reset_state()
        _persist_state()
        return jsonify({
            "ok": True,
            "xml_input": "",
            "xml_output": "",
            "message": "Los datos cargados fueron limpiados.",
        })

    try:
        root = _parse_xml(xml_content)
    except ValueError as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400

    _debug_tag_counts(root)

    STATE["admin_xml"] = xml_content

    if action == "upload":
        STATE["admin_output"] = "Archivo XML cargado. Presiona 'Procesar Datos' para aplicar los cambios."
        _persist_state()
        return jsonify({
            "ok": True,
            "xml_input": STATE["admin_xml"],
            "xml_output": STATE["admin_output"],
            "message": "Archivo XML cargado correctamente.",
        })

    users = _extract_users(root)
    horarios = _extract_horarios(root)
    notas = _extract_notas(root)
    courses = _extract_configuration_courses(root) if _local_tag(root.tag) == "configuraciones" else []

    if users:
        STATE["users"] = users
    if horarios:
        STATE["horarios"] = horarios
    if notas:
        print(f"[FLASK NOTAS] notas_cargadas_admin={notas}")
        STATE["notas"] = notas
        _sync_note_storage()

    summary = [
        "XML procesado correctamente.",
        f"Usuarios detectados: {len(users)}",
        f"Horarios detectados: {len(horarios)}",
        f"Cursos detectados: {len(courses)}",
        f"Notas detectadas: {len(notas)}",
    ]
    STATE["admin_output"] = "\n".join(summary)
    _persist_state()

    return jsonify({
        "ok": True,
        "xml_input": STATE["admin_xml"],
        "xml_output": STATE["admin_output"],
        "usuarios": len(STATE["users"]),
    })


@rutas.route("/admin/usuarios", methods=["GET"])
def admin_usuarios():
    return jsonify({
        "ok": True,
        "usuarios": STATE["users"],
    })


@rutas.route("/catalogo", methods=["GET"])
def catalogo():
    return jsonify({
        "ok": True,
        "cursos": _course_catalog(),
        "actividades_por_curso": _activities_by_course(),
    })


@rutas.route("/tutor/horarios", methods=["GET", "POST"])
def tutor_horarios():
    if request.method == "GET":
        return jsonify({
            "ok": True,
            "horarios": STATE["horarios"],
            "filename": STATE["last_horario_file"],
        })

    payload = request.get_json(silent=True) or {}
    xml_content = payload.get("xml_content", "")
    filename = str(payload.get("filename", "")).strip()

    try:
        root = _parse_tutor_upload(filename, xml_content, "tutor_horarios")
    except ValueError as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400

    horarios = _extract_horarios(root)
    if not horarios:
        return jsonify({
            "ok": False,
            "message": "No se encontraron horarios validos en el XML.",
        }), 400

    STATE["horarios"] = horarios
    STATE["last_horario_file"] = filename
    _persist_state()
    return jsonify({
        "ok": True,
        "horarios": horarios,
        "filename": filename,
        "message": "Horarios cargados correctamente.",
    })


@rutas.route("/tutor/notas", methods=["POST"])
def tutor_notas():
    payload = request.get_json(silent=True) or {}
    xml_content = payload.get("xml_content", "")
    filename = str(payload.get("filename", "")).strip()

    try:
        root = _parse_tutor_upload(filename, xml_content, "tutor_notas")
    except ValueError as exc:
        return jsonify({"ok": False, "message": str(exc)}), 400

    notas = _extract_notas(root)
    if not notas:
        return jsonify({
            "ok": False,
            "message": "No se encontraron notas validas en el XML.",
        }), 400

    STATE["notas"] = notas
    print(f"[FLASK NOTAS] notas_cargadas_tutor={notas}")
    _sync_note_storage()
    STATE["last_notas_file"] = filename
    _persist_state()
    unmatched_students = sorted({
        note["estudiante"]
        for note in notas
        if not _find_user(note.get("estudiante"))
    })
    warning = ""
    if unmatched_students:
        warning = (
            " Los siguientes carnets no existen entre los estudiantes cargados: "
            + ", ".join(unmatched_students)
            + "."
        )
    return jsonify({
        "ok": True,
        "filename": filename,
        "message": f"Se cargaron {len(notas)} notas correctamente.{warning}",
        "cursos": _course_catalog(),
    })


@rutas.route("/reportes/promedio", methods=["POST"])
def reporte_promedio():
    payload = request.get_json(silent=True) or {}
    curso = str(payload.get("curso", "")).strip()

    if not curso:
        return jsonify({
            "ok": False,
            "message": "Debes seleccionar un curso.",
        }), 400

    registros = [
        nota for nota in STATE["notas"]
        if nota.get("curso", "").lower() == curso.lower()
    ]
    if not registros:
        return jsonify({
            "ok": False,
            "message": "No hay notas cargadas para ese curso.",
        }), 404

    grouped = defaultdict(list)
    for nota in registros:
        grouped[nota["actividad"]].append(nota["valor_numerico"])

    actividades = [
        {
            "actividad": actividad,
            "promedio": _display_number(mean(valores)),
        }
        for actividad, valores in sorted(grouped.items())
    ]

    return jsonify({
        "ok": True,
        "curso": curso,
        "promedio": _display_number(mean(nota["valor_numerico"] for nota in registros)),
        "total_registros": len(registros),
        "actividades": actividades,
    })


@rutas.route("/reportes/top-notas", methods=["POST"])
def reporte_top_notas():
    payload = request.get_json(silent=True) or {}
    curso = str(payload.get("curso", "")).strip()
    actividad = str(payload.get("actividad", "")).strip()

    if not curso or not actividad:
        return jsonify({
            "ok": False,
            "message": "Debes seleccionar curso y actividad.",
        }), 400

    registros = [
        nota for nota in STATE["notas"]
        if nota.get("curso", "").lower() == curso.lower()
        and nota.get("actividad", "").lower() == actividad.lower()
    ]
    if not registros:
        return jsonify({
            "ok": False,
            "message": "No hay notas para ese curso y actividad.",
        }), 404

    ordered = sorted(
        registros,
        key=lambda item: item["valor_numerico"],
        reverse=True,
    )[:5]

    return jsonify({
        "ok": True,
        "curso": curso,
        "actividad": actividad,
        "top": [
            {
                "estudiante": item["estudiante"] or "Sin estudiante",
                "valor": item["valor"],
            }
            for item in ordered
        ],
    })


@rutas.route("/estudiante/notas", methods=["POST"])
def estudiante_notas():
    payload = request.get_json(silent=True) or {}
    username = str(payload.get("username", "")).strip()
    carnet = str(payload.get("carnet", "")).strip()
    curso = str(payload.get("curso", "")).strip()
    cursos_disponibles = _student_available_courses(username, carnet)

    print(
        "[FLASK ESTUDIANTE] solicitud_notas "
        f"username={username!r} "
        f"carnet={carnet!r} "
        f"curso={curso!r}"
    )

    if not username and not carnet:
        return jsonify({
            "ok": False,
            "message": "Debes enviar el usuario o carnet del estudiante.",
        }), 400

    notas = _filtered_student_notes(username, carnet, curso)
    message = ""
    if not notas:
        student_label = carnet or username
        if curso:
            message = f"No hay notas para el estudiante {student_label} en el curso {curso}."
        else:
            message = f"No hay notas para el estudiante {student_label}."

    print(f"[FLASK ESTUDIANTE] notas_devueltas={notas}")
    return jsonify({
        "ok": True,
        "curso": curso,
        "cursos_disponibles": cursos_disponibles,
        "message": message,
        "notas": [
            {
                "actividad": note["actividad"],
                "valor": note["valor"],
            }
            for note in notas
        ],
    })
