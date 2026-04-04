from django.shortcuts import render

def login_view(request):
    return render(request, 'app_cliente/login.html')

def admin_dashboard(request):
    return render(request, 'app_cliente/admin_dashboard.html')

def tutor_dashboard(request):
    return render(request, 'app_cliente/tutor_dashboard.html')

def estudiante_dashboard(request):
    return render(request, 'app_cliente/estudiante_dashboard.html')