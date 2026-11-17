from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone

from . import logic

Usuario = settings.AUTH_USER_MODEL


class Perfil(models.Model):
    """Solo los 6 datos necesarios para calcular la meta (minimización de datos)."""

    SEXO = [("f", "Femenino"), ("m", "Masculino")]
    ACTIVIDAD = [(k, f"{v[1]} · {v[2]}") for k, v in logic.ACTIVIDADES.items()]
    OBJETIVO = [(k, v[1]) for k, v in logic.OBJETIVOS.items()]

    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, related_name="perfil")
    peso = models.DecimalField(
        "Peso (kg)", max_digits=5, decimal_places=1,
        validators=[MinValueValidator(30, "Ingresa un peso entre 30 y 300 kg."),
                    MaxValueValidator(300, "Ingresa un peso entre 30 y 300 kg.")])
    altura = models.PositiveSmallIntegerField(
        "Altura (cm)",
        validators=[MinValueValidator(120, "Ingresa una altura entre 120 y 230 cm."),
                    MaxValueValidator(230, "Ingresa una altura entre 120 y 230 cm.")])
    edad = models.PositiveSmallIntegerField(
        "Edad",
        validators=[MinValueValidator(18, "MyFitnessPal es para personas de 18 a 100 años."),
                    MaxValueValidator(100, "MyFitnessPal es para personas de 18 a 100 años.")])
    sexo = models.CharField("Sexo biológico", max_length=1, choices=SEXO)
    actividad = models.CharField("Nivel de actividad", max_length=12, choices=ACTIVIDAD)
    objetivo = models.CharField("Objetivo", max_length=10, choices=OBJETIVO)
    bloqueado = models.BooleanField("Bloqueo temporal", default=False)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "perfiles"

    def __str__(self):
        return f"Perfil de {self.usuario}"

    @property
    def meta(self):
        return logic.meta_calorica(self.peso, self.altura, self.edad, self.sexo, self.actividad, self.objetivo)


class Consentimiento(models.Model):
    """Estado vigente de cada permiso. Todos parten apagados."""

    PERMISO = [(k, v["titulo"]) for k, v in logic.PERMISOS.items()]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="consentimientos")
    permiso = models.CharField(max_length=12, choices=PERMISO)
    activo = models.BooleanField(default=False)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["usuario", "permiso"], name="un_permiso_por_usuario")]

    def __str__(self):
        return f"{self.usuario} · {self.permiso}: {'sí' if self.activo else 'no'}"


class HistorialPermiso(models.Model):
    """Registro de cada decisión de consentimiento, con fecha (trazabilidad)."""

    PERMISO = Consentimiento.PERMISO + [("camara", "Cámara para escanear")]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="historial_permisos")
    permiso = models.CharField(max_length=12, choices=PERMISO)
    valor = models.BooleanField()
    fecha = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "decisión de permiso"
        verbose_name_plural = "historial de permisos"


class Alimento(models.Model):
    """Catálogo público de alimentos (no son datos personales)."""

    nombre = models.CharField(max_length=60, unique=True)
    porcion = models.CharField(max_length=30)
    kcal = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return f"{self.nombre} ({self.porcion}, {self.kcal} kcal)"


class RegistroComida(models.Model):
    COMIDA = [(c, c) for c in logic.COMIDAS]

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="comidas")
    fecha = models.DateField(default=timezone.localdate)
    comida = models.CharField(max_length=10, choices=COMIDA)
    nombre = models.CharField(max_length=60)
    porcion = models.CharField(max_length=30, blank=True)
    kcal = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(3000)])
    porciones = models.DecimalField(max_digits=4, decimal_places=1, default=1,
                                    validators=[MinValueValidator(0.5), MaxValueValidator(20)])
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["fecha", "creado"]
        verbose_name = "registro de comida"
        verbose_name_plural = "registros de comida"

    @property
    def total(self):
        return round(self.kcal * float(self.porciones))


class Peso(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="pesos")
    fecha = models.DateField(default=timezone.localdate)
    peso = models.DecimalField(max_digits=5, decimal_places=1,
                               validators=[MinValueValidator(30), MaxValueValidator(300)])

    class Meta:
        ordering = ["fecha"]
        constraints = [models.UniqueConstraint(fields=["usuario", "fecha"], name="un_peso_por_dia")]
