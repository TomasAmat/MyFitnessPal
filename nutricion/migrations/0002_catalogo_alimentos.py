"""Carga el catálogo inicial de alimentos (calorías aproximadas por porción)."""
from django.db import migrations

ALIMENTOS = [
    ("Marraqueta", "1 unidad", 270), ("Pan integral", "1 rebanada", 70), ("Palta", "1/4 unidad", 80),
    ("Huevo", "1 unidad", 75), ("Queso fresco", "1 lámina", 60), ("Jamón de pavo", "1 lámina", 30),
    ("Leche semidescremada", "1 taza", 110), ("Yogur natural", "1 unidad", 100), ("Avena", "1/2 taza", 150),
    ("Plátano", "1 unidad", 105), ("Manzana", "1 unidad", 95), ("Naranja", "1 unidad", 60),
    ("Arroz cocido", "1 taza", 205), ("Fideos cocidos", "1 taza", 220), ("Pechuga de pollo", "100 g", 165),
    ("Atún al agua", "1 lata", 120), ("Ensalada chilena", "1 plato", 90), ("Lentejas", "1 plato", 350),
    ("Porotos con riendas", "1 plato", 450), ("Cazuela de vacuno", "1 plato", 400),
    ("Pastel de choclo", "1 porción", 600), ("Empanada de pino", "1 unidad", 500),
    ("Completo italiano", "1 unidad", 550), ("Sopaipilla", "1 unidad", 200),
    ("Café o té sin azúcar", "1 taza", 2), ("Bebida cola", "350 ml", 140), ("Jugo de naranja", "1 vaso", 110),
    ("Galletas de agua", "4 unidades", 90),
]


def cargar(apps, schema_editor):
    Alimento = apps.get_model("nutricion", "Alimento")
    for nombre, porcion, kcal in ALIMENTOS:
        Alimento.objects.update_or_create(nombre=nombre, defaults={"porcion": porcion, "kcal": kcal})


def descargar(apps, schema_editor):
    apps.get_model("nutricion", "Alimento").objects.filter(nombre__in=[a[0] for a in ALIMENTOS]).delete()


class Migration(migrations.Migration):
    dependencies = [("nutricion", "0001_initial")]
    operations = [migrations.RunPython(cargar, descargar)]
