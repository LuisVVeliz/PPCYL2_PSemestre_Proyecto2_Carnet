from django.urls import path
from .views import (
    landing_view,
    login_view,
    logout_view,
    admin_panel,
    cargar_xml,
    ver_usuarios,
    informacion,
    tutor_home,
    tutor_horarios,
    tutor_notas,
    tutor_reporte_promedio,
    tutor_top_notas,
    estudiante_home,
    estudiante_notas,
)

urlpatterns = [
    path('', landing_view, name='landing'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('admin-dashboard/', admin_panel, name='admin_dashboard'),
    path('admin-panel/', admin_panel, name='admin_panel'),
    path('cargar-xml/', cargar_xml, name='cargar_xml'),
    path('ver-usuarios/', ver_usuarios, name='ver_usuarios'),
    path('informacion/', informacion, name='informacion'),

    path('tutor/', tutor_home, name='tutor_home'),
    path('tutor-horarios/', tutor_horarios, name='tutor_horarios'),
    path('tutor-notas/', tutor_notas, name='tutor_notas'),
    path('tutor-reporte-promedio/', tutor_reporte_promedio, name='tutor_reporte_promedio'),
    path('tutor-top-notas/', tutor_top_notas, name='tutor_top_notas'),
    path('estudiante/', estudiante_home, name='estudiante_home'),
    path('estudiante-notas/', estudiante_notas, name='estudiante_notas'),

]
