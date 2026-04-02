from django.shortcuts import render, redirect


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        # ✅ ADMINISTRADOR OBLIGATORIO (NO SE TOCA)
        if username == 'AdminPPCYL2' and password == 'AdminPPCYL2771':
            request.session['user'] = username
            request.session['role'] = 'admin'
            return redirect('admin_panel')

        # ✅ TUTOR (SIMULACIÓN DE FLASK)
        elif username.startswith('tutor') and password == 'tutor':
            request.session['user'] = username
            request.session['role'] = 'tutor'
            return redirect('tutor_horarios')

        # ✅ ESTUDIANTE (SIMULACIÓN)
        elif username.startswith('estudiante') and password == 'estudiante':
            request.session['user'] = username
            request.session['role'] = 'estudiante'
            return redirect('estudiante_notas')

        # ❌ CUALQUIER OTRO CASO
        else:
            return render(request, 'login/login.html', {
                'error': 'Usuario o contraseña incorrectos'
            })

    return render(request, 'login/login.html')


def admin_panel(request):
    if request.session.get('role') != 'admin':
        return redirect('login')
    return render(request, 'login/admin/admin.html')



def cargar_xml(request):
    if request.session.get('role') != 'admin':
        return redirect('login')

    xml_entrada = ''
    xml_salida = ''

    if request.method == 'POST':
        if 'archivo_xml' in request.FILES:
            archivo = request.FILES['archivo_xml']
            xml_entrada = archivo.read().decode('utf-8')

        if 'limpiar' in request.POST:
            xml_entrada = ''
            xml_salida = ''

        if 'procesar' in request.POST:
            xml_entrada = request.POST.get('xml_entrada', '')
            xml_salida = '<resultado></resultado>'

    return render(request, 'login/admin/cargar_xml.html', {
        'xml_entrada': xml_entrada,
        'xml_salida': xml_salida
    })


def ver_usuarios(request):
    if request.session.get('role') != 'admin':
        return redirect('login')

    usuarios = []

    return render(request, 'login/admin/ver_usuarios.html', {
        'usuarios': usuarios
    })
def informacion(request):
    if request.session.get('role') != 'admin':
        return redirect('login')

    return render(request, 'login/admin/informacion.html')
def tutor_horarios(request):
    if request.session.get('role') != 'tutor':
        return redirect('login')

    # Simulación: Flask aún no devuelve datos
    horarios = []
    archivo = ""

    if request.method == 'POST':
        if 'archivo_xml' in request.FILES:
            archivo = request.FILES['archivo_xml'].name
            # Aquí, en el futuro, se enviará el archivo a Flask

    return render(request, 'login/tutor/tutor_horarios.html', {
        'horarios': horarios,
        'archivo': archivo
    })
def tutor_notas(request):
    if request.session.get('role') != 'tutor':
        return redirect('login')

    archivo = ""
    mensaje = ""

    if request.method == 'POST':
        if 'archivo_xml' in request.FILES:
            archivo = request.FILES['archivo_xml'].name
            # En el futuro: enviar este archivo XML a Flask
            mensaje = "Archivo de notas cargado correctamente. Pendiente de procesamiento."

    return render(request, 'login/tutor/tutor_notas.html', {
        'archivo': archivo,
        'mensaje': mensaje
    })
def tutor_reporte_promedio(request):
    if request.session.get('role') != 'tutor':
        return redirect('login')

    mostrar = False

    if request.method == 'POST':
        # Aquí luego se hará la petición a Flask para generar el reporte
        # Por ahora solo simulamos que el reporte existe
        mostrar = True

    return render(request, 'login/tutor/tutor_reporte_promedio.html', {
        'mostrar': mostrar
    })

def tutor_top_notas(request):
    if request.session.get('role') != 'tutor':
        return redirect('login')

    mostrar = False

    if request.method == 'POST':
        # Aquí luego se llamará a Flask para generar el reporte
        mostrar = True

    return render(request, 'login/tutor/tutor_top_notas.html', {
        'mostrar': mostrar
    })
def estudiante_notas(request):
    if request.session.get('role') != 'estudiante':
        return redirect('login')

    notas = []

    if request.method == 'POST':
        # Simulación de respuesta de Flask
        notas = [
            {'actividad': 'Tarea 1', 'valor': 100},
            {'actividad': 'Tarea 2', 'valor': 70},
            {'actividad': 'Tarea 3', 'valor': 100},
            {'actividad': 'Tarea 4', 'valor': 100},
        ]

    return render(request, 'login/estudiante/estudiante_notas.html', {
        'notas': notas
    })  
    