"""Pruebas de aceptación de MyFitnessPal. Ejecutar con:  python manage.py test

Cada clase corresponde a una historia del Sprint Backlog en Jira.
"""
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from . import logic
from .models import Consentimiento, HistorialPermiso, Perfil, Peso, RegistroComida

User = get_user_model()
CLAVE = "Planeta-Verde-2026"
PERFIL = {"peso": "80", "altura": "180", "edad": "30", "sexo": "m", "actividad": "sedentario", "objetivo": "mantener"}


def crear_usuario_listo(email="ana@ejemplo.cl", **extra):
    """Usuario con permiso de salud y perfil completo."""
    u = User.objects.create_user(username=email, email=email, password=CLAVE)
    Consentimiento.objects.create(usuario=u, permiso="salud", activo=True)
    datos = {"peso": 80, "altura": 180, "edad": 30, "sexo": "m", "actividad": "sedentario", "objetivo": "mantener"}
    datos.update(extra)
    Perfil.objects.create(usuario=u, **datos)
    return u


class CalculoCaloricoTests(TestCase):
    """SCRUM-12 · La meta coincide con el cálculo manual (Mifflin-St Jeor)."""

    def test_hombre_sedentario(self):
        # 10*80 + 6,25*180 - 5*30 + 5 = 1780 ; x1,2 = 2136
        self.assertEqual(logic.meta_calorica(80, 180, 30, "m", "sedentario", "mantener"), 2136)

    def test_mujer_moderada(self):
        # 10*60 + 6,25*165 - 5*25 - 161 = 1345,25 ; x1,55 = 2085,1
        self.assertEqual(logic.meta_calorica(60, 165, 25, "f", "moderado", "mantener"), 2085)

    def test_bajar_de_peso_resta_500(self):
        self.assertEqual(logic.meta_calorica(80, 180, 30, "m", "sedentario", "bajar"), 1636)

    def test_piso_de_seguridad(self):
        # Una meta muy baja nunca baja de 1200 kcal en mujeres
        self.assertEqual(logic.meta_calorica(40, 150, 90, "f", "sedentario", "bajar"), 1200)


class RegistroDeUsuarioTests(TestCase):
    """SCRUM-12 · Registro con datos mínimos."""

    def test_crear_cuenta_guarda_usuario_y_pide_permisos(self):
        r = self.client.post(reverse("crear_cuenta"), {"email": "Nuevo@Ejemplo.cl", "password1": CLAVE, "password2": CLAVE})
        self.assertRedirects(r, reverse("permisos"))
        self.assertTrue(User.objects.filter(username="nuevo@ejemplo.cl").exists())

    def test_contrasena_se_guarda_cifrada(self):
        self.client.post(reverse("crear_cuenta"), {"email": "a@b.cl", "password1": CLAVE, "password2": CLAVE})
        u = User.objects.get(username="a@b.cl")
        self.assertNotEqual(u.password, CLAVE)
        self.assertTrue(u.check_password(CLAVE))

    def test_correo_repetido_no_se_registra(self):
        crear_usuario_listo("ana@ejemplo.cl")
        r = self.client.post(reverse("crear_cuenta"), {"email": "ana@ejemplo.cl", "password1": CLAVE, "password2": CLAVE})
        self.assertContains(r, "ya tiene una cuenta")
        self.assertEqual(User.objects.count(), 1)

    def test_iniciar_sesion(self):
        crear_usuario_listo("ana@ejemplo.cl")
        r = self.client.post(reverse("entrar"), {"username": "ANA@ejemplo.cl", "password": CLAVE})
        self.assertRedirects(r, reverse("diario"))

    def test_rechaza_menor_de_18(self):
        u = User.objects.create_user(username="x@y.cl", password=CLAVE)
        Consentimiento.objects.create(usuario=u, permiso="salud", activo=True)
        self.client.force_login(u)
        r = self.client.post(reverse("datos"), {**PERFIL, "edad": "15"})
        self.assertContains(r, "18 a 100 años")
        self.assertFalse(Perfil.objects.exists())

    def test_perfil_valido_guarda_solo_datos_minimos(self):
        u = User.objects.create_user(username="x@y.cl", password=CLAVE)
        Consentimiento.objects.create(usuario=u, permiso="salud", activo=True)
        self.client.force_login(u)
        r = self.client.post(reverse("datos"), PERFIL)
        self.assertRedirects(r, reverse("diario"))
        self.assertEqual(Perfil.objects.get(usuario=u).meta, 2136)
        campos = {f.name for f in Perfil._meta.get_fields()} - {"id", "usuario", "bloqueado", "creado", "actualizado"}
        self.assertEqual(campos, {"peso", "altura", "edad", "sexo", "actividad", "objetivo"})


class ConsentimientoTests(TestCase):
    """SCRUM-13 · Consentimiento granular."""

    def setUp(self):
        self.u = User.objects.create_user(username="c@d.cl", password=CLAVE)
        self.client.force_login(self.u)

    def test_sin_permiso_de_salud_no_se_piden_datos(self):
        self.assertRedirects(self.client.get(reverse("datos")), reverse("permisos"))
        self.assertRedirects(self.client.get(reverse("diario")), reverse("permisos"))

    def test_no_se_puede_continuar_sin_permiso_de_salud(self):
        r = self.client.post(reverse("permisos"), {})
        self.assertContains(r, "necesitamos el primer permiso")

    def test_activar_salud_no_activa_publicidad(self):
        self.client.post(reverse("permisos"), {"salud": "on"})
        activos = dict(Consentimiento.objects.filter(usuario=self.u).values_list("permiso", "activo"))
        self.assertTrue(activos["salud"])
        self.assertFalse(activos["publicidad"])
        self.assertFalse(activos["analitica"])
        self.assertFalse(activos["wearables"])

    def test_cada_cambio_queda_en_el_historial(self):
        self.client.post(reverse("permisos"), {"salud": "on"})
        self.client.post(reverse("cambiar_permiso", args=["publicidad"]))
        self.client.post(reverse("cambiar_permiso", args=["publicidad"]))
        decisiones = list(HistorialPermiso.objects.filter(usuario=self.u, permiso="publicidad").values_list("valor", flat=True))
        self.assertEqual(decisiones, [False, True, False])  # más reciente primero


class DiarioTests(TestCase):
    """SCRUM-14 · Uso diario con privacidad reforzada."""

    def setUp(self):
        self.u = crear_usuario_listo()
        self.client.force_login(self.u)

    def test_agregar_comida_se_guarda_en_la_base_de_datos(self):
        from .models import Alimento
        marraqueta = Alimento.objects.get(nombre="Marraqueta")
        self.client.post(reverse("agregar"), {"alimento": marraqueta.pk, "comida": "Once"})
        self.client.post(reverse("agregar"), {"comida": "Once", "nombre": "Té con leche", "kcal": "60", "porciones": "1.5"})
        self.assertEqual(sum(r.total for r in RegistroComida.objects.filter(usuario=self.u)), 360)
        r = self.client.get(reverse("diario"))
        self.assertContains(r, "Marraqueta")
        self.assertEqual(r.context["total"], 360)

    def test_sin_permiso_publicidad_no_hay_anuncio(self):
        self.assertContains(self.client.get(reverse("diario")), "Sin anuncio")

    def test_con_permiso_publicidad_aparece_anuncio(self):
        Consentimiento.objects.create(usuario=self.u, permiso="publicidad", activo=True)
        self.assertContains(self.client.get(reverse("diario")), "publicitario personalizado")

    def test_permiso_de_camara_se_registra_al_usarla(self):
        self.client.post(reverse("escanear"), {"permitir": "1"})
        self.assertTrue(HistorialPermiso.objects.filter(usuario=self.u, permiso="camara", valor=True).exists())


class AislamientoEntreUsuariosTests(TestCase):
    """SCRUM-15 · Nadie puede ver ni borrar los datos de otra persona."""

    def test_otro_usuario_no_ve_ni_borra_mis_comidas(self):
        ana = crear_usuario_listo("ana@ejemplo.cl")
        beto = crear_usuario_listo("beto@ejemplo.cl")
        comida = RegistroComida.objects.create(usuario=ana, comida="Almuerzo", nombre="Cazuela secreta", kcal=400)
        self.client.force_login(beto)
        self.assertNotContains(self.client.get(reverse("diario")), "Cazuela secreta")
        self.assertNotContains(self.client.get(reverse("acceso")), "Cazuela secreta")
        self.assertEqual(self.client.post(reverse("quitar", args=[comida.pk])).status_code, 404)
        self.assertTrue(RegistroComida.objects.filter(pk=comida.pk).exists())

    def test_sin_sesion_no_hay_acceso(self):
        r = self.client.get(reverse("diario"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("entrar"), r["Location"])


class DerechosArsopbTests(TestCase):
    """SCRUM-15 · Derechos ARSOPB."""

    def setUp(self):
        self.u = crear_usuario_listo()
        self.client.force_login(self.u)
        RegistroComida.objects.create(usuario=self.u, comida="Desayuno", nombre="Avena", kcal=150)

    def test_acceso_muestra_mis_datos(self):
        r = self.client.get(reverse("acceso"))
        self.assertContains(r, "ana@ejemplo.cl")
        self.assertContains(r, "Avena")

    def test_rectificar_recalcula_la_meta(self):
        self.client.post(reverse("rectificar"), {**PERFIL, "peso": "70"})
        self.assertEqual(Perfil.objects.get(usuario=self.u).meta, 2016)

    def test_oposicion_desactiva_publicidad(self):
        self.client.post(reverse("cambiar_permiso", args=["publicidad"]))
        self.client.post(reverse("cambiar_permiso", args=["publicidad"]))
        self.assertFalse(Consentimiento.objects.get(usuario=self.u, permiso="publicidad").activo)

    def test_portabilidad_json_y_csv(self):
        r = self.client.get(reverse("exportar_json"))
        self.assertIn("attachment", r["Content-Disposition"])
        datos = json.loads(r.content)
        for clave in ("cuenta", "perfil", "permisos", "historial_permisos", "comidas", "pesos"):
            self.assertIn(clave, datos)
        self.assertEqual(datos["comidas"][0]["alimento"], "Avena")
        csv = self.client.get(reverse("exportar_csv")).content.decode("utf-8-sig").strip().splitlines()
        self.assertEqual(len(csv), 2)

    def test_bloqueo_impide_registrar(self):
        self.client.post(reverse("bloqueo"))
        self.client.post(reverse("agregar"), {"comida": "Once", "nombre": "Pan", "kcal": "100", "porciones": "1"})
        self.assertFalse(RegistroComida.objects.filter(nombre="Pan").exists())
        self.client.post(reverse("progreso"), {"peso": "79"})
        self.assertFalse(Peso.objects.filter(usuario=self.u).exists())

    def test_supresion_exige_confirmacion(self):
        self.client.post(reverse("borrar"), {"confirmacion": "no"})
        self.assertTrue(User.objects.filter(pk=self.u.pk).exists())

    def test_supresion_borra_todo(self):
        self.client.post(reverse("cambiar_permiso", args=["publicidad"]))
        r = self.client.post(reverse("borrar"), {"confirmacion": "borrar"})
        self.assertRedirects(r, reverse("bienvenida"))
        self.assertFalse(User.objects.filter(pk=self.u.pk).exists())
        for modelo in (Perfil, Consentimiento, HistorialPermiso, RegistroComida, Peso):
            self.assertEqual(modelo.objects.count(), 0, modelo.__name__)
