from django.shortcuts import render

def login_view(request):
    return render(request, 'app_cliente/login.html')

def admin_dashboard(request):
    return render(request, 'app_cliente/admin_dashboard.html')

def tutor_dashboard(request):
    return render(request, 'app_cliente/tutor_dashboard.html')

def estudiante_dashboard(request):
    return render(request, 'app_cliente/estudiante_dashboard.html')

from django.shortcuts import render
import requests
import plotly.graph_objects as go
import plotly.offline as opy
from django.http import HttpResponse

def login_view(request):
    return render(request, 'app_cliente/login.html')

def admin_dashboard(request):
    return render(request, 'app_cliente/admin_dashboard.html')

def tutor_dashboard(request):
    return render(request, 'app_cliente/tutor_dashboard.html') 

def estudiante_dashboard(request):
    return render(request, 'app_cliente/estudiante_dashboard.html')

# ========== TUS FUNCIONES DE REPORTES Y GRÁFICAS ==========

def grafico_promedios(request):
    response = requests.post(
        'http://127.0.0.1:5000/api/reportes/promedio',
        json={'curso': '770'}
    )
    
    if response.status_code != 200:
        return HttpResponse("Error al obtener datos del servidor")
    
    datos = response.json()
    
    if not datos.get('ok'):
        return HttpResponse(datos.get('message', 'Error en los datos'))
    
    actividades = [act['actividad'] for act in datos['actividades']]
    promedios = [act['promedio'] for act in datos['actividades']]
    
    fig = go.Figure(data=[
        go.Bar(x=actividades, y=promedios, marker_color='skyblue')
    ])
    
    fig.update_layout(
        title=f"Promedio de Notas - Curso {datos['curso']}",
        xaxis_title="Actividades",
        yaxis_title="Promedio",
        yaxis_range=[0, 100]
    )
    
    grafico_html = opy.plot(fig, output_type='div', include_plotlyjs='cdn')
    
    return render(request, 'reportes/promedios.html', {
        'grafico': grafico_html,
        'curso': datos['curso']
    })

def grafico_top(request):
    response = requests.post(
        'http://127.0.0.1:5000/api/reportes/top-notas',
        json={'curso': '770', 'actividad': 'Tarea1'}
    )
    
    if response.status_code != 200:
        return HttpResponse("Error al obtener datos")
    
    datos = response.json()
    
    if not datos.get('ok'):
        return HttpResponse(datos.get('message', 'Error'))
    
    top = datos['top']
    estudiantes = [item['estudiante'] for item in top]
    notas = [item['valor'] for item in top]
    
    fig = go.Figure(data=[
        go.Bar(x=notas, y=estudiantes, orientation='h', marker_color='coral')
    ])
    
    fig.update_layout(
        title=f"TOP Notas - {datos['actividad']}",
        xaxis_title="Nota",
        yaxis_title="Estudiante",
        xaxis_range=[0, 100]
    )
    
    grafico_html = opy.plot(fig, output_type='div', include_plotlyjs='cdn')
    
    return render(request, 'reportes/top.html', {
        'grafico': grafico_html,
        'curso': datos['curso'],
        'actividad': datos['actividad']
    })