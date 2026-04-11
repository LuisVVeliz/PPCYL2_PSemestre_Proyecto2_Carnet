from django.urls import path
from . import views

urlpatterns = [
    path('promedios/', views.grafico_promedios, name='promedios'),
    path('top/', views.grafico_top, name='top'),
    path('matriz/', views.grafico_matriz, name='matriz'), 
    path('prueba/', views.prueba_graphviz, name='prueba'),
    path('exportar_promedios/', views.exportar_pdf_promedios, name='exportar_promedios'),
    path('exportar_top/', views.exportar_pdf_top, name='exportar_top'), 
]