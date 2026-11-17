import csv
import json
from datetime import date
from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from . import logic
from .forms import (BorrarCuentaForm, ComidaManualForm, EntrarForm, PerfilForm, PermisosForm, PesoForm,
                    RegistroForm)
from .models import Alimento, Consentimiento, HistorialPermiso, Perfil, Peso, RegistroComida


# ---------------------------------------------------------------- utilidades

def permisos_de(usuario):
    """Diccionario {permiso: activo} con todos los permisos; los que no existen cuentan como apagados."""
    actuales = {k: False for k in logic.PERMISOS}
    actuales.update(dict(usuario.consentimientos.values_list("permiso", "activo")))
    return actuales


def fijar_permiso(usuario, permiso, valor):
    """Guarda el permiso y deja registro en el historial solo si la decisión cambió."""
    obj, creado = Consentimiento.objects.get_or_create(usuario=usuario, permiso=permiso, defaults={"activo": valor})
    if creado or obj.activo != valor:
        if not creado:
            obj.activo = valor
            obj.save()
        HistorialPermiso.objects.create(usuario=usuario, permiso=permiso, valor=valor)
        return True
    return False


def perfil_de(usuario):
    return Perfil.objects.filter(usuario=usuario).first()


def puede_registrar(usuario):
    perfil = perfil_de(usuario)
    return bool(perfil and not perfil.bloqueado and permisos_de(usuario)["salud"])


def app_lista(vista):
    """Exige sesión, permiso de salud y perfil completo; si falta algo, lleva al paso que corresponde."""
    @login_required
    @wraps(vista)
    def envoltura(request, *args, **kwargs):
        if not permisos_de(request.user)["salud"]:
            return redirect("permisos")
        if not perfil_de(request.user):
            return redirect("datos")
        return vista(request, *args, **kwargs)
    return envoltura


# ---------------------------------------------------------------- cuenta

def bienvenida(request):
    if request.user.is_authenticated:
        return redirect("diario")
    return render(request, "nutricion/bienvenida.html")


def crear_cuenta(request):
    if request.user.is_authenticated:
        return redirect("diario")
    form = RegistroForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(request, "Cuenta creada. Ahora decide qué permisos das.")
        return redirect("permisos")
    return render(request, "nutricion/crear_cuenta.html", {"form": form})


class Entrar(LoginView):
    template_name = "nutricion/entrar.html"
    authentication_form = EntrarForm
    redirect_authenticated_user = True


# ---------------------------------------------------------------- registro guiado

@login_required
def permisos(request):
    actuales = permisos_de(request.user)
    form = PermisosForm(request.POST if request.method == "POST" else None, actuales=actuales)
    if request.method == "POST" and form.is_valid():
        for clave in logic.PERMISOS:
            fijar_permiso(request.user, clave, form.cleaned_data[clave])
        if not perfil_de(request.user):
            return redirect("datos")
        messages.success(request, "Permisos guardados.")
        return redirect("diario")
    pausada = perfil_de(request.user) is not None and not actuales["salud"]
    return render(request, "nutricion/permisos.html", {"form": form, "pausada": pausada,
                                                       "onboarding": perfil_de(request.user) is None})


@login_required
def datos(request):
    if not permisos_de(request.user)["salud"]:
        return redirect("permisos")
    if perfil_de(request.user):
        return redirect("diario")
    form = PerfilForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        perfil = form.save(commit=False)
        perfil.usuario = request.user
        perfil.save()
        Peso.objects.update_or_create(usuario=request.user, fecha=timezone.localdate(), defaults={"peso": perfil.peso})
        messages.success(request, f"Listo. Tu meta diaria es {perfil.meta:,} kcal.".replace(",", "."))
        return redirect("diario")
    return render(request, "nutricion/datos.html", {"form": form})


# ---------------------------------------------------------------- uso diario

@app_lista
def diario(request):
    perfil = perfil_de(request.user)
    hoy = timezone.localdate()
    registros = list(RegistroComida.objects.filter(usuario=request.user, fecha=hoy))
    total = sum(r.total for r in registros)
    meta = perfil.meta
    comidas = [{"nombre": c, "items": [r for r in registros if r.comida == c]} for c in logic.COMIDAS]
    for c in comidas:
        c["total"] = sum(r.total for r in c["items"])
    permisos_actuales = permisos_de(request.user)
    return render(request, "nutricion/diario.html", {
        "tabs": "diario", "perfil": perfil, "hoy": hoy, "meta": meta, "total": total, "restante": meta - total, "exceso": total - meta,
        "anillo": logic.anillo(total, meta), "comidas": comidas,
        "publicidad": permisos_actuales["publicidad"],
        "reforzada": not permisos_actuales["publicidad"] and not permisos_actuales["analitica"],
        "objetivo": logic.OBJETIVOS[perfil.objetivo][1].lower(),
        "actividad": logic.ACTIVIDADES[perfil.actividad][1].lower(),
    })


@app_lista
def agregar(request):
    comida = request.GET.get("comida") or request.POST.get("comida") or "Desayuno"
    if comida not in logic.COMIDAS:
        comida = "Desayuno"
    q = (request.GET.get("q") or "").strip()
    bloqueado = perfil_de(request.user).bloqueado
    manual = ComidaManualForm(initial={"comida": comida})

    if request.method == "POST":
        if not puede_registrar(request.user):
            messages.error(request, "Tus datos están bloqueados. Desbloquéalos en Privacidad para registrar.")
            return redirect("agregar")
        if "alimento" in request.POST:
            alimento = get_object_or_404(Alimento, pk=request.POST["alimento"])
            RegistroComida.objects.create(usuario=request.user, comida=comida, nombre=alimento.nombre,
                                          porcion=alimento.porcion, kcal=alimento.kcal, porciones=1)
            messages.success(request, f"{alimento.nombre} agregado a {comida.lower()}.")
            return redirect(f"{request.path}?{urlencode({'comida': comida, 'q': q})}")
        manual = ComidaManualForm(request.POST)
        if manual.is_valid():
            d = manual.cleaned_data
            RegistroComida.objects.create(usuario=request.user, comida=d["comida"], nombre=d["nombre"].strip(),
                                          porcion="porción", kcal=d["kcal"], porciones=d["porciones"])
            messages.success(request, f"{d['nombre']} agregado a {d['comida'].lower()}.")
            return redirect(f"{request.path}?{urlencode({'comida': d['comida']})}")

    alimentos = Alimento.objects.filter(nombre__icontains=q) if q else Alimento.objects.all()
    return render(request, "nutricion/agregar.html", {
        "tabs": "agregar", "comida": comida, "comidas": logic.COMIDAS, "q": q,
        "alimentos": alimentos[:15], "manual": manual, "bloqueado": bloqueado,
        "camara": request.GET.get("camara") == "1"})


@require_POST
@app_lista
def quitar(request, pk):
    if not puede_registrar(request.user):
        messages.error(request, "Tus datos están bloqueados.")
        return redirect("diario")
    registro = get_object_or_404(RegistroComida, pk=pk, usuario=request.user)  # 404 si es de otra persona
    registro.delete()
    messages.success(request, f"{registro.nombre} quitado.")
    return redirect("diario")


@require_POST
@app_lista
def escanear(request):
    permitir = request.POST.get("permitir") == "1"
    HistorialPermiso.objects.create(usuario=request.user, permiso="camara", valor=permitir)
    if permitir:
        messages.info(request, "Permiso registrado solo para esta vez. El escáner llega en el próximo sprint; por ahora busca el alimento.")
    else:
        messages.info(request, "No usaremos la cámara.")
    return redirect("agregar")


@app_lista
def progreso(request):
    perfil = perfil_de(request.user)
    form = PesoForm(request.POST if request.method == "POST" else None, initial={"peso": perfil.peso})
    if request.method == "POST":
        if not puede_registrar(request.user):
            messages.error(request, "Tus datos están bloqueados.")
            return redirect("progreso")
        if form.is_valid():
            antes = perfil.meta
            nuevo = form.cleaned_data["peso"]
            Peso.objects.update_or_create(usuario=request.user, fecha=timezone.localdate(), defaults={"peso": nuevo})
            perfil.peso = nuevo
            perfil.save()
            messages.success(request, f"Peso guardado. Tu meta pasó de {antes} a {perfil.meta} kcal.")
            return redirect("progreso")
    pesos = list(Peso.objects.filter(usuario=request.user).order_by("fecha").values_list("fecha", "peso"))
    cambio = float(pesos[-1][1] - pesos[0][1]) if len(pesos) > 1 else None
    dias = list(RegistroComida.objects.filter(usuario=request.user).values_list("fecha", flat=True).distinct())
    ultimos = sorted(set(dias))[-7:]
    promedio = 0
    if ultimos:
        regs = RegistroComida.objects.filter(usuario=request.user, fecha__in=ultimos)
        promedio = round(sum(r.total for r in regs) / len(ultimos))
    return render(request, "nutricion/progreso.html", {
        "tabs": "progreso", "perfil": perfil, "form": form, "barras": logic.barras_pesos(pesos), "cambio": cambio,
        "dias": len(set(dias)), "promedio": promedio, "bloqueado": perfil.bloqueado})


# ---------------------------------------------------------------- centro de privacidad (ARSOPB)

@login_required
def privacidad(request):
    actuales = permisos_de(request.user)
    filas = [{"clave": k, "activo": actuales[k], **v} for k, v in logic.PERMISOS.items()]
    perfil = perfil_de(request.user)
    return render(request, "nutricion/privacidad.html", {
        "tabs": "privacidad" if perfil and actuales["salud"] else None,
        "perfil": perfil, "filas": filas, "activos": sum(actuales.values()), "total_permisos": len(actuales),
        "reforzada": not actuales["publicidad"] and not actuales["analitica"],
        "ultima": request.user.historial_permisos.first()})


@require_POST
@login_required
def modo_reforzado(request):
    actuales = permisos_de(request.user)
    if actuales["publicidad"] or actuales["analitica"]:
        fijar_permiso(request.user, "publicidad", False)
        fijar_permiso(request.user, "analitica", False)
        messages.success(request, "Modo privacidad reforzada activado: sin publicidad ni analítica de terceros.")
        return redirect("privacidad")
    messages.info(request, "Para salir del modo reforzado, activa publicidad o analítica en Mis permisos.")
    return redirect("permisos")


@login_required
def menu(request):
    perfil = perfil_de(request.user)
    actuales = permisos_de(request.user)
    return render(request, "nutricion/menu.html", {
        "tabs": "menu" if perfil and actuales["salud"] else None, "perfil": perfil,
        "nombre": request.user.email.split("@")[0],
        "objetivo": logic.OBJETIVOS[perfil.objetivo][1] if perfil else None,
        "activos": sum(actuales.values()), "total_permisos": len(actuales),
        "reforzada": not actuales["publicidad"] and not actuales["analitica"],
        "wearables": actuales["wearables"]})


@require_POST
@login_required
def cambiar_permiso(request, permiso):
    if permiso not in logic.PERMISOS:
        return redirect("privacidad")
    nuevo = not permisos_de(request.user)[permiso]
    fijar_permiso(request.user, permiso, nuevo)
    titulo = logic.PERMISOS[permiso]["titulo"]
    messages.success(request, f"{titulo}: {'activado' if nuevo else 'desactivado'}.")
    if permiso == "salud" and not nuevo:
        messages.warning(request, "MyFitnessPal queda en pausa: sin este permiso no usamos tus datos de salud.")
    return redirect("privacidad")


@login_required
def acceso(request):
    u = request.user
    return render(request, "nutricion/acceso.html", {
        "perfil": perfil_de(u), "permisos": permisos_de(u), "titulos": {k: v["titulo"] for k, v in logic.PERMISOS.items()},
        "historial": u.historial_permisos.all()[:30], "n_comidas": u.comidas.count(), "n_pesos": u.pesos.count(),
        "comidas": u.comidas.order_by("-fecha", "-creado")[:20]})


@login_required
def rectificar(request):
    perfil = perfil_de(request.user)
    if not perfil:
        return redirect("datos")
    antes = perfil.meta
    form = PerfilForm(request.POST if request.method == "POST" else None, instance=perfil)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"Datos corregidos. Tu meta pasó de {antes} a {perfil.meta} kcal.")
        return redirect("privacidad")
    return render(request, "nutricion/rectificar.html", {"form": form})


def _exportacion(usuario):
    perfil = perfil_de(usuario)
    return {
        "formato": "MyFitnessPal · exportación de datos personales (derecho de portabilidad)",
        "exportado": timezone.now().isoformat(),
        "cuenta": {"correo": usuario.email, "creada": usuario.date_joined.isoformat()},
        "perfil": None if not perfil else {
            "peso_kg": float(perfil.peso), "altura_cm": perfil.altura, "edad": perfil.edad, "sexo": perfil.sexo,
            "actividad": perfil.actividad, "objetivo": perfil.objetivo, "meta_kcal": perfil.meta,
            "bloqueo_temporal": perfil.bloqueado},
        "permisos": permisos_de(usuario),
        "historial_permisos": [{"permiso": h.permiso, "valor": h.valor, "fecha": h.fecha.isoformat()}
                               for h in usuario.historial_permisos.all()],
        "comidas": [{"fecha": r.fecha.isoformat(), "comida": r.comida, "alimento": r.nombre, "porcion": r.porcion,
                     "kcal": r.kcal, "porciones": float(r.porciones), "total_kcal": r.total}
                    for r in usuario.comidas.all()],
        "pesos": [{"fecha": p.fecha.isoformat(), "peso_kg": float(p.peso)} for p in usuario.pesos.all()],
    }


@login_required
def exportar_json(request):
    datos = json.dumps(_exportacion(request.user), ensure_ascii=False, indent=2)
    resp = HttpResponse(datos, content_type="application/json; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="myfitnesspal-mis-datos-{date.today()}.json"'
    return resp


@login_required
def exportar_csv(request):
    resp = HttpResponse(content_type="text/csv; charset=utf-8")
    resp["Content-Disposition"] = f'attachment; filename="myfitnesspal-mi-diario-{date.today()}.csv"'
    resp.write("﻿")  # para que Excel muestre bien las tildes
    w = csv.writer(resp)
    w.writerow(["fecha", "comida", "alimento", "porcion", "porciones", "kcal_total"])
    for r in request.user.comidas.all():
        w.writerow([r.fecha, r.comida, r.nombre, r.porcion, r.porciones, r.total])
    return resp


@require_POST
@login_required
def bloqueo(request):
    perfil = perfil_de(request.user)
    if perfil:
        perfil.bloqueado = not perfil.bloqueado
        perfil.save()
        messages.success(request, "Uso de tus datos bloqueado." if perfil.bloqueado else "Uso de tus datos reanudado.")
    return redirect("privacidad")


@login_required
def borrar_cuenta(request):
    u = request.user
    form = BorrarCuentaForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        u.delete()  # en cascada: perfil, permisos, historial, comidas y pesos
        logout(request)
        messages.success(request, "Tu cuenta y todos tus datos fueron borrados de forma permanente.")
        return redirect("bienvenida")
    return render(request, "nutricion/borrar.html", {
        "form": form, "n_comidas": u.comidas.count(), "n_pesos": u.pesos.count(),
        "n_historial": u.historial_permisos.count()})
