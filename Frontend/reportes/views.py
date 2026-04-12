

from django.shortcuts import render
from django.http import HttpResponse
import requests
import plotly.graph_objects as go
import plotly.offline as opy
import os
from django.conf import settings
from graphviz import Digraph
from weasyprint import HTML
from datetime import datetime

# ========== VALIDACIÓN DE NOTAS (0-100) ==========
def validar_nota(nota):
    """Valida que la nota esté entre 0 y 100"""
    try:
        return 0 <= float(nota) <= 100
    except (ValueError, TypeError):
        return False

# ========== GRÁFICA DE PROMEDIOS ==========
def grafico_promedios(request):
    # Obtener el curso seleccionado desde la URL (si no viene, usar '770')
    curso_seleccionado = request.GET.get('curso', '770')
    
    # Obtener datos reales de Flask para el curso seleccionado
    response = requests.post(
        'http://127.0.0.1:5000/api/reportes/promedio',
        json={'curso': curso_seleccionado}
    )
    
    if response.status_code != 200:
        return HttpResponse("Error al obtener datos del servidor")
    
    datos = response.json()
    
    if not datos.get('ok'):
        return HttpResponse(datos.get('message', 'Error en los datos'))
    
    # Extraer actividades y promedios
    actividades = [act['actividad'] for act in datos['actividades']]
    promedios = [act['promedio'] for act in datos['actividades']]
    
    # Filtrar promedios válidos (0-100)
    promedios_validos = [p for p in promedios if validar_nota(p)]
    
    # Crear gráfico de barras
    fig = go.Figure(data=[
        go.Bar(x=actividades, y=promedios_validos, marker_color='skyblue')
    ])
    
    fig.update_layout(
        title=f"Promedio de Notas - Curso {datos['curso']}",
        xaxis_title="Actividades",
        yaxis_title="Promedio",
        yaxis_range=[0, 100]
    )
    
    grafico_html = opy.plot(fig, output_type='div', include_plotlyjs='cdn')
    
    # Obtener lista de cursos para el selector
    response_cursos = requests.get('http://127.0.0.1:5000/api/catalogo')
    if response_cursos.status_code == 200:
        data_cursos = response_cursos.json()
        lista_cursos = data_cursos.get('cursos', [])
    else:
        lista_cursos = [curso_seleccionado]
    
    return render(request, 'reportes/promedios.html', {
    'grafico': grafico_html,
    'curso': datos['curso'],
    'cursos': lista_cursos,
    'datos_tabla': list(zip(actividades, promedios_validos)),  # ← AGREGAR ESTA LÍNEA
})

# ========== GRÁFICA TOP DE NOTAS ==========
def grafico_top(request):
    # Obtener parámetros de la URL (si no vienen, usar valores por defecto)
    curso_seleccionado = request.GET.get('curso', '770')
    actividad_seleccionada = request.GET.get('actividad', 'Tarea1')
    
    # Obtener lista de cursos para el selector
    response_cursos = requests.get('http://127.0.0.1:5000/api/catalogo')
    if response_cursos.status_code == 200:
        data_cursos = response_cursos.json()
        lista_cursos = data_cursos.get('cursos', [])
    else:
        lista_cursos = [curso_seleccionado]
    
    # Obtener lista de actividades para el curso seleccionado
    response_actividades = requests.post(
        'http://127.0.0.1:5000/api/reportes/promedio',
        json={'curso': curso_seleccionado}
    )
    
    if response_actividades.status_code == 200:
        data_act = response_actividades.json()
        if data_act.get('ok'):
            lista_actividades = [act['actividad'] for act in data_act['actividades']]
        else:
            lista_actividades = [actividad_seleccionada]
    else:
        lista_actividades = [actividad_seleccionada]
    
    # Obtener datos reales de Flask para el TOP
    response = requests.post(
        'http://127.0.0.1:5000/api/reportes/top-notas',
        json={'curso': curso_seleccionado, 'actividad': actividad_seleccionada}
    )
    
    if response.status_code != 200:
        return HttpResponse("Error al obtener datos")
    
    datos = response.json()
    
    if not datos.get('ok'):
        return HttpResponse(datos.get('message', 'Error'))
    
    top = datos['top']
    
    # Filtrar solo notas válidas (0-100)
    top_validas = [item for item in top if validar_nota(item['valor'])]
    
    estudiantes = [item['estudiante'] for item in top_validas]
    notas = [item['valor'] for item in top_validas]
    
    # Crear gráfico de barras horizontal
    fig = go.Figure(data=[
        go.Bar(x=notas, y=estudiantes, orientation='h', marker_color='coral')
    ])
    
    fig.update_layout(
        title=f"TOP Notas - {actividad_seleccionada} (Curso {curso_seleccionado})",
        xaxis_title="Nota",
        yaxis_title="Estudiante",
        xaxis_range=[0, 100]
    )
    
    grafico_html = opy.plot(fig, output_type='div', include_plotlyjs='cdn')
    
    return render(request, 'reportes/top.html', {
    'grafico': grafico_html,
    'curso': datos['curso'],
    'actividad': datos['actividad'],
    'cursos': lista_cursos,
    'actividades': lista_actividades,
    'top_validas': top_validas,  # ← AGREGAR ESTA LÍNEA
})

# ========== MATRIZ DISPERSA CON GRAPHVIZ ==========
# ========== MATRIZ DISPERSA (TABLA HTML MEJORADA) ==========
def grafico_matriz(request):
    curso_seleccionado = request.GET.get('curso', '770')
    
    # Obtener lista de cursos
    response_cursos = requests.get('http://127.0.0.1:5000/api/catalogo')
    if response_cursos.status_code == 200:
        data_cursos = response_cursos.json()
        lista_cursos = data_cursos.get('cursos', [])
    else:
        lista_cursos = [curso_seleccionado]
    
    # Obtener actividades del curso
    response_prom = requests.post(
        'http://127.0.0.1:5000/api/reportes/promedio',
        json={'curso': curso_seleccionado}
    )
    
    if response_prom.status_code != 200:
        return render(request, 'reportes/matriz.html', {
            'error': f'Curso {curso_seleccionado} sin datos',
            'cursos': lista_cursos,
            'curso_seleccionado': curso_seleccionado,
        })
    
    datos_prom = response_prom.json()
    
    if not datos_prom.get('ok'):
        return render(request, 'reportes/matriz.html', {
            'error': datos_prom.get('message'),
            'cursos': lista_cursos,
            'curso_seleccionado': curso_seleccionado,
        })
    
    actividades = datos_prom.get('actividades', [])
    
    # Recolectar todos los estudiantes y sus notas
    estudiantes = {}
    todas_notas = []
    
    for actividad in actividades:
        nombre_actividad = actividad['actividad']
        response_notas = requests.post(
            'http://127.0.0.1:5000/api/reportes/top-notas',
            json={'curso': curso_seleccionado, 'actividad': nombre_actividad}
        )
        
        if response_notas.status_code == 200:
            datos_notas = response_notas.json()
            if datos_notas.get('ok'):
                for nota_item in datos_notas.get('top', []):
                    estudiante_id = nota_item['estudiante']
                    nota_valor = nota_item['valor']
                    
                    if validar_nota(nota_valor):
                        if estudiante_id not in estudiantes:
                            estudiantes[estudiante_id] = {}
                        estudiantes[estudiante_id][nombre_actividad] = nota_valor
                        todas_notas.append(nota_valor)
    
    # Si no hay estudiantes, mostrar mensaje
    if not estudiantes:
        return render(request, 'reportes/matriz.html', {
            'error': f'No hay notas cargadas para el curso {curso_seleccionado}',
            'cursos': lista_cursos,
            'curso_seleccionado': curso_seleccionado,
        })
    
    # Crear tabla HTML
    html_table = '<table border="1" style="border-collapse: collapse; width: 100%; margin-top: 20px;">'
    html_table += '<tr style="background-color: #4CAF50; color: white;">'
    html_table += '<th style="padding: 10px;">Estudiante</th>'
    
    for actividad in actividades:
        nombre = actividad['actividad']
        html_table += f'<th style="padding: 10px;">{nombre}</th>'
    
    html_table += '<th style="padding: 10px;">Promedio</th>'
    html_table += '</tr>'
    
    # Filas por estudiante
    for estudiante_id, notas in estudiantes.items():
        html_table += '<tr>'
        html_table += f'<td style="padding: 10px; font-weight: bold;">{estudiante_id}</td>'
        
        suma_notas = 0
        cantidad = 0
        
        for actividad in actividades:
            nombre_actividad = actividad['actividad']
            nota = notas.get(nombre_actividad, '-')
            
            if nota != '-':
                suma_notas += float(nota)
                cantidad += 1
                if nota >= 90:
                    color = '#d4edda'
                elif nota >= 70:
                    color = '#fff3cd'
                else:
                    color = '#f8d7da'
                html_table += f'<td style="padding: 10px; background-color: {color}; text-align: center;">{nota}</td>'
            else:
                html_table += f'<td style="padding: 10px; background-color: #f0f0f0; text-align: center;">-</td>'
        
        promedio = round(suma_notas / cantidad, 2) if cantidad > 0 else '-'
        html_table += f'<td style="padding: 10px; font-weight: bold; text-align: center;">{promedio}</td>'
        html_table += '</tr>'
    
    html_table += '</table>'
    
    # Estadísticas
    promedio_general = round(sum(todas_notas) / len(todas_notas), 2) if todas_notas else 0
    nota_max = max(todas_notas) if todas_notas else 0
    nota_min = min(todas_notas) if todas_notas else 0
    
    html_stats = f'''
    <div style="margin-top: 20px; padding: 15px; background-color: #e9ecef; border-radius: 5px;">
        <h3>📊 Estadísticas del Curso {curso_seleccionado}</h3>
        <ul style="list-style: none; padding-left: 0;">
            <li>📈 <strong>Promedio general:</strong> {promedio_general}</li>
            <li>🏆 <strong>Nota más alta:</strong> {nota_max}</li>
            <li>📉 <strong>Nota más baja:</strong> {nota_min}</li>
            <li>👨‍🎓 <strong>Total estudiantes:</strong> {len(estudiantes)}</li>
            <li>📚 <strong>Total actividades:</strong> {len(actividades)}</li>
        </ul>
    </div>
    '''
    
    return render(request, 'reportes/matriz.html', {
        'cursos': lista_cursos,
        'curso_seleccionado': curso_seleccionado,
        'matriz_html': html_table,
        'estadisticas_html': html_stats,
        'error': None,
    })

# ========== PRUEBA DE GRAPHVIZ ==========
def prueba_graphviz(request):
    static_dir = os.path.join(settings.BASE_DIR, 'static')
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    
    dot = Digraph()
    dot.node('A', 'Nodo A')
    dot.node('B', 'Nodo B')
    dot.edge('A', 'B')
    
    image_path = os.path.join(static_dir, 'prueba')
    dot.render(image_path, format='png', cleanup=True)
    
    return HttpResponse("Imagen de prueba generada en static/prueba.png")

# ========== EXPORTAR PROMEDIOS A PDF ==========
def exportar_pdf_promedios(request):
    import base64
    import io
    
    curso_seleccionado = request.GET.get('curso', '770')
    
    # Obtener datos de Flask
    response = requests.post(
        'http://127.0.0.1:5000/api/reportes/promedio',
        json={'curso': curso_seleccionado}
    )
    
    if response.status_code != 200:
        return HttpResponse("Error al obtener datos del servidor")
    
    datos = response.json()
    
    if not datos.get('ok'):
        return HttpResponse(datos.get('message', 'Error en los datos'))
    
    # Extraer actividades y promedios
    actividades = [act['actividad'] for act in datos['actividades']]
    promedios = [act['promedio'] for act in datos['actividades']]
    
    # Filtrar promedios válidos
    promedios_validos = [p for p in promedios if validar_nota(p)]
    
    # Crear gráfico con Plotly
    fig = go.Figure(data=[
        go.Bar(x=actividades, y=promedios_validos, marker_color='skyblue')
    ])
    
    fig.update_layout(
        title=f"Promedio de Notas - Curso {datos['curso']}",
        xaxis_title="Actividades",
        yaxis_title="Promedio",
        yaxis_range=[0, 100],
        width=800,
        height=500,
        template='plotly_white'
    )
    
    # Exportar gráfico como imagen PNG en base64
    img_bytes = fig.to_image(format="png")
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    
    # Crear tabla de datos (como respaldo)
    tabla_html = '<table border="1" style="border-collapse: collapse; width: 100%; margin-top: 20px;">'
    tabla_html += '<tr style="background-color: #4CAF50; color: white;">'
    tabla_html += '<th style="padding: 8px;">Actividad</th>'
    tabla_html += '<th style="padding: 8px;">Promedio</th>'
    tabla_html += '</tr>'
    
    for act, prom in zip(actividades, promedios_validos):
        tabla_html += f'<tr><td style="padding: 8px;">{act}</td><td style="padding: 8px; text-align: center;">{prom}</td></tr>'
    
    tabla_html += '</table>'
    
    # Crear el HTML para el PDF
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Reporte de Promedios - AcadNet</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                background-color: white;
            }}
            h1 {{
                color: #2c3e50;
                text-align: center;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }}
            .info {{
                text-align: center;
                margin-bottom: 20px;
                color: #555;
            }}
            .curso {{
                font-size: 18px;
                font-weight: bold;
                color: #2980b9;
            }}
            .fecha {{
                text-align: center;
                margin-top: 30px;
                color: #888;
                font-size: 12px;
            }}
            .grafico {{
                text-align: center;
                margin: 20px 0;
            }}
            img {{
                max-width: 100%;
                height: auto;
                border: 1px solid #ddd;
                border-radius: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th {{
                background-color: #4CAF50;
                color: white;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
            tr:hover {{
                background-color: #f5f5f5;
            }}
        </style>
    </head>
    <body>
        <h1>📊 Reporte de Promedios</h1>
        <div class="info">
            <span class="curso">Curso: {datos['curso']}</span><br>
            Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        </div>
        
        <div class="grafico">
            <img src="data:image/png;base64,{img_base64}" alt="Gráfico de Promedios">
        </div>
        
        <h3>📋 Datos numéricos</h3>
        {tabla_html}
        
        <div class="fecha">
            Reporte generado por AcadNet - Plataforma de Gestión Académica
        </div>
    </body>
    </html>
    """
    
    # Crear la respuesta PDF
    response_pdf = HttpResponse(content_type='application/pdf')
    response_pdf['Content-Disposition'] = f'attachment; filename="reporte_promedios_{datos["curso"]}.pdf"'
    
    # Generar el PDF
    HTML(string=html_content).write_pdf(response_pdf)
    
    return response_pdf
# ========== EXPORTAR TOP NOTAS A PDF ==========
def exportar_pdf_top(request):
    import base64
    
    curso_seleccionado = request.GET.get('curso', '770')
    actividad_seleccionada = request.GET.get('actividad', 'Tarea1')
    
    # Obtener datos de Flask para el TOP
    response = requests.post(
        'http://127.0.0.1:5000/api/reportes/top-notas',
        json={'curso': curso_seleccionado, 'actividad': actividad_seleccionada}
    )
    
    if response.status_code != 200:
        return HttpResponse("Error al obtener datos")
    
    datos = response.json()
    
    if not datos.get('ok'):
        return HttpResponse(datos.get('message', 'Error'))
    
    top = datos['top']
    
    # Filtrar solo notas válidas (0-100)
    top_validas = [item for item in top if validar_nota(item['valor'])]
    
    estudiantes = [item['estudiante'] for item in top_validas]
    notas = [item['valor'] for item in top_validas]
    
    # Crear gráfico horizontal con Plotly
    fig = go.Figure(data=[
        go.Bar(x=notas, y=estudiantes, orientation='h', marker_color='coral')
    ])
    
    fig.update_layout(
        title=f"TOP Notas - {actividad_seleccionada} (Curso {curso_seleccionado})",
        xaxis_title="Nota",
        yaxis_title="Estudiante",
        xaxis_range=[0, 100],
        width=800,
        height=500,
        template='plotly_white'
    )
    
    # Exportar gráfico como imagen PNG en base64
    img_bytes = fig.to_image(format="png")
    img_base64 = base64.b64encode(img_bytes).decode('utf-8')
    
    # Crear tabla de datos
    tabla_html = '<table border="1" style="border-collapse: collapse; width: 100%; margin-top: 20px;">'
    tabla_html += '<tr style="background-color: #FF5722; color: white;">'
    tabla_html += '<th style="padding: 8px;">Posición</th>'
    tabla_html += '<th style="padding: 8px;">Estudiante</th>'
    tabla_html += '<th style="padding: 8px;">Nota</th>'
    tabla_html += '</tr>'
    
    for i, (est, nota) in enumerate(zip(estudiantes, notas), 1):
        # Color según posición
        if i == 1:
            color = '#FFD700'  # Oro
        elif i == 2:
            color = '#C0C0C0'  # Plata
        elif i == 3:
            color = '#CD7F32'  # Bronce
        else:
            color = '#f5f5f5'
        
        tabla_html += f'<tr style="background-color: {color};">'
        tabla_html += f'<td style="padding: 8px; text-align: center;"><strong>#{i}</strong></td>'
        tabla_html += f'<td style="padding: 8px;">{est}</td>'
        tabla_html += f'<td style="padding: 8px; text-align: center;"><strong>{nota}</strong></td>'
        tabla_html += '</tr>'
    
    tabla_html += '</table>'
    
    # Crear el HTML para el PDF
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Reporte TOP Notas - AcadNet</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                background-color: white;
            }}
            h1 {{
                color: #2c3e50;
                text-align: center;
                border-bottom: 2px solid #FF5722;
                padding-bottom: 10px;
            }}
            .info {{
                text-align: center;
                margin-bottom: 20px;
                color: #555;
            }}
            .curso {{
                font-size: 18px;
                font-weight: bold;
                color: #FF5722;
            }}
            .actividad {{
                font-size: 16px;
                color: #2980b9;
            }}
            .fecha {{
                text-align: center;
                margin-top: 30px;
                color: #888;
                font-size: 12px;
            }}
            .grafico {{
                text-align: center;
                margin: 20px 0;
            }}
            img {{
                max-width: 100%;
                height: auto;
                border: 1px solid #ddd;
                border-radius: 5px;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }}
            th {{
                background-color: #FF5722;
                color: white;
            }}
            th, td {{
                border: 1px solid #ddd;
                padding: 8px;
                text-align: left;
            }}
        </style>
    </head>
    <body>
        <h1>🏆 Reporte TOP Notas</h1>
        <div class="info">
            <span class="curso">Curso: {curso_seleccionado}</span><br>
            <span class="actividad">Actividad: {actividad_seleccionada}</span><br>
            Fecha de generación: {datetime.now().strftime('%d/%m/%Y %H:%M')}
        </div>
        
        <div class="grafico">
            <img src="data:image/png;base64,{img_base64}" alt="Gráfico TOP Notas">
        </div>
        
        <h3>📋 Ranking de Notas</h3>
        {tabla_html}
        
        <div class="fecha">
            Reporte generado por AcadNet - Plataforma de Gestión Académica
        </div>
    </body>
    </html>
    """
    
    # Crear la respuesta PDF
    response_pdf = HttpResponse(content_type='application/pdf')
    response_pdf['Content-Disposition'] = f'attachment; filename="reporte_top_{curso_seleccionado}_{actividad_seleccionada}.pdf"'
    
    # Generar el PDF
    HTML(string=html_content).write_pdf(response_pdf)
    
    return response_pdf