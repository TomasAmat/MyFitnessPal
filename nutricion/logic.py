"""Reglas de negocio de MyFitnessPal, sin dependencias de Django para poder probarlas solas."""

ACTIVIDADES = {
    "sedentario": (1.2, "Sedentario", "Poco o nada de ejercicio"),
    "ligero": (1.375, "Ligero", "Ejercicio 1 a 3 días por semana"),
    "moderado": (1.55, "Moderado", "Ejercicio 3 a 5 días por semana"),
    "intenso": (1.725, "Intenso", "Ejercicio 6 a 7 días por semana"),
}

OBJETIVOS = {
    "bajar": (-500, "Bajar de peso"),
    "mantener": (0, "Mantener mi peso"),
    "subir": (300, "Subir de peso"),
}

# Piso de seguridad: la app nunca recomienda menos que esto
PISO_KCAL = {"f": 1200, "m": 1500}

PERMISOS = {
    "salud": {
        "titulo": "Datos de salud para calcular tu plan",
        "detalle": "Peso, altura, edad, sexo y comidas. Solo para calorías y progreso.",
        "requerido": True,
    },
    "wearables": {
        "titulo": "Reloj o pulsera deportiva",
        "detalle": "Importa pasos y ejercicio. Te lo preguntamos de nuevo al conectarlo.",
        "requerido": False,
    },
    "publicidad": {
        "titulo": "Publicidad personalizada",
        "detalle": "Anuncios según tus intereses. Apagado, tu dieta nunca se usa para publicidad.",
        "requerido": False,
    },
    "analitica": {
        "titulo": "Analítica de terceros",
        "detalle": "Estadísticas de uso para empresas externas. Apagado, nada sale de MyFitnessPal.",
        "requerido": False,
    },
}

COMIDAS = ["Desayuno", "Almuerzo", "Once", "Cena", "Colación"]


def tmb(peso, altura, edad, sexo):
    """Tasa metabólica basal, fórmula Mifflin-St Jeor (kcal/día)."""
    return 10 * float(peso) + 6.25 * float(altura) - 5 * int(edad) + (5 if sexo == "m" else -161)


def meta_calorica(peso, altura, edad, sexo, actividad, objetivo):
    """Meta diaria = TMB x factor de actividad + ajuste por objetivo, con piso de seguridad."""
    base = tmb(peso, altura, edad, sexo) * ACTIVIDADES[actividad][0] + OBJETIVOS[objetivo][0]
    return round(max(base, PISO_KCAL[sexo]))


def anillo(consumido, meta, radio=44):
    """Datos para dibujar el anillo de progreso del diario."""
    import math
    circ = 2 * math.pi * radio
    pct = min(consumido / meta, 1) if meta else 0
    return {"circ": round(circ, 2), "largo": round(circ * pct, 2), "pct": round(pct * 100), "excedido": consumido > meta}


def barras_pesos(pesos, n=8, alto_min=40, alto_max=132):
    """Convierte los últimos n [(fecha, peso), ...] en barras con alto en px. None si hay menos de 2."""
    pesos = list(pesos)[-n:]
    if len(pesos) < 2:
        return None
    valores = [float(p) for _, p in pesos]
    mn, mx = min(valores), max(valores)
    rango = (mx - mn) or 1
    return [{"etiqueta": f.strftime("%d/%m"), "peso": v,
             "alto": round(alto_min + (alto_max - alto_min) * (v - mn) / rango)}
            for (f, _), v in zip(pesos, valores)]
