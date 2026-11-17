"""Panel de administración.

Privacy by Design: los datos personales se muestran solo en modo lectura y con lo
mínimo para comprobar que el sistema guarda la información. Nadie puede editar el
perfil, la dieta o los permisos de otra persona desde aquí.
"""
from django.contrib import admin

from .models import Alimento, Consentimiento, HistorialPermiso, Perfil, Peso, RegistroComida


class SoloLectura(admin.ModelAdmin):
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Alimento)
class AlimentoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "porcion", "kcal")
    search_fields = ("nombre",)


@admin.register(Perfil)
class PerfilAdmin(SoloLectura):
    list_display = ("usuario", "objetivo", "bloqueado", "creado")
    list_filter = ("objetivo", "bloqueado")


@admin.register(Consentimiento)
class ConsentimientoAdmin(SoloLectura):
    list_display = ("usuario", "permiso", "activo", "actualizado")
    list_filter = ("permiso", "activo")


@admin.register(HistorialPermiso)
class HistorialPermisoAdmin(SoloLectura):
    list_display = ("usuario", "permiso", "valor", "fecha")
    list_filter = ("permiso", "valor")


@admin.register(RegistroComida)
class RegistroComidaAdmin(SoloLectura):
    list_display = ("usuario", "fecha", "comida", "nombre", "total")
    list_filter = ("fecha", "comida")


@admin.register(Peso)
class PesoAdmin(SoloLectura):
    list_display = ("usuario", "fecha", "peso")
