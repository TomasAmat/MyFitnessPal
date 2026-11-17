from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

urlpatterns = [
    path("", views.bienvenida, name="bienvenida"),
    path("cuenta/crear/", views.crear_cuenta, name="crear_cuenta"),
    path("cuenta/entrar/", views.Entrar.as_view(), name="entrar"),
    path("cuenta/salir/", LogoutView.as_view(), name="salir"),
    path("permisos/", views.permisos, name="permisos"),
    path("datos/", views.datos, name="datos"),
    path("diario/", views.diario, name="diario"),
    path("agregar/", views.agregar, name="agregar"),
    path("comida/<int:pk>/quitar/", views.quitar, name="quitar"),
    path("escanear/", views.escanear, name="escanear"),
    path("progreso/", views.progreso, name="progreso"),
    path("menu/", views.menu, name="menu"),
    path("privacidad/", views.privacidad, name="privacidad"),
    path("privacidad/reforzado/", views.modo_reforzado, name="modo_reforzado"),
    path("privacidad/permiso/<str:permiso>/", views.cambiar_permiso, name="cambiar_permiso"),
    path("privacidad/acceso/", views.acceso, name="acceso"),
    path("privacidad/rectificar/", views.rectificar, name="rectificar"),
    path("privacidad/exportar.json", views.exportar_json, name="exportar_json"),
    path("privacidad/exportar.csv", views.exportar_csv, name="exportar_csv"),
    path("privacidad/bloqueo/", views.bloqueo, name="bloqueo"),
    path("privacidad/borrar/", views.borrar_cuenta, name="borrar"),
]
