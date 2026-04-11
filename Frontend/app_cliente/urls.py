from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('admin_dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('tutor_dashboard/', views.tutor_dashboard, name='tutor_dashboard'),
    path('estudiante_dashboard/', views.estudiante_dashboard, name='estudiante_dashboard'),
    
    # ========== TUS RUTAS DE REPORTES Y GRÁFICAS ==========
    path('promedios/', views.grafico_promedios, name='promedios'),
    path('top/', views.grafico_top, name='top'),
] 