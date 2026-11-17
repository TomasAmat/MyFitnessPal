from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm

from . import logic
from .models import Perfil

User = get_user_model()


class RegistroForm(forms.Form):
    email = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "inputmode": "email", "placeholder": "nombre@correo.cl"}))
    password1 = forms.CharField(
        label="Contraseña", help_text="Mínimo 8 caracteres, que no sean solo números.",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(
        label="Repite la contraseña", widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("Ese correo ya tiene una cuenta. Inicia sesión.")
        return email

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get("password1"), datos.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        if p1:
            try:
                password_validation.validate_password(p1, User(username=datos.get("email", ""), email=datos.get("email", "")))
            except forms.ValidationError as e:
                self.add_error("password1", e)
        return datos

    def save(self):
        email = self.cleaned_data["email"]
        return User.objects.create_user(username=email, email=email, password=self.cleaned_data["password1"])


class EntrarForm(AuthenticationForm):
    username = forms.EmailField(label="Correo electrónico", widget=forms.EmailInput(
        attrs={"autocomplete": "email", "autofocus": True, "placeholder": "nombre@correo.cl"}))
    error_messages = {
        "invalid_login": "Correo o contraseña incorrectos.",
        "inactive": "Esta cuenta está desactivada.",
    }

    def clean_username(self):
        return self.cleaned_data["username"].strip().lower()


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ["peso", "altura", "edad", "sexo", "actividad", "objetivo"]
        widgets = {
            "peso": forms.NumberInput(attrs={"step": "0.1", "inputmode": "decimal", "placeholder": "72"}),
            "altura": forms.NumberInput(attrs={"inputmode": "numeric", "placeholder": "170"}),
            "edad": forms.NumberInput(attrs={"inputmode": "numeric", "placeholder": "29"}),
            "sexo": forms.RadioSelect(attrs={"class": "sr"}),
        }
        labels = {"peso": "Peso (kg)", "altura": "Altura (cm)", "edad": "Edad", "sexo": "Sexo",
                  "actividad": "Actividad física", "objetivo": "Objetivo"}
        help_texts = {
            "peso": "Gasto calórico y progreso",
            "altura": "Metabolismo basal",
            "edad": "Ajusta la fórmula",
            "sexo": "Fórmula metabólica",
            "actividad": "Ajusta la meta a cuánto te mueves",
            "objetivo": "Suma o resta calorías a tu meta",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["sexo"].choices = Perfil.SEXO  # sin la opción vacía "---------"
        self.fields["actividad"].choices = [("", "Elige tu nivel de actividad")] + Perfil.ACTIVIDAD
        self.fields["objetivo"].choices = [("", "Elige tu objetivo")] + Perfil.OBJETIVO


class PermisosForm(forms.Form):
    """Un interruptor por permiso, sin opción de aceptar todo."""

    def __init__(self, *args, actuales=None, **kwargs):
        super().__init__(*args, **kwargs)
        actuales = actuales or {}
        for clave, info in logic.PERMISOS.items():
            self.fields[clave] = forms.BooleanField(
                required=False, label=info["titulo"], help_text=info["detalle"], initial=actuales.get(clave, False))

    def clean(self):
        datos = super().clean()
        if not datos.get("salud"):
            raise forms.ValidationError(
                "Para usar MyFitnessPal necesitamos el primer permiso: sin tus datos de salud no podemos calcular tus calorías.")
        return datos


class ComidaManualForm(forms.Form):
    comida = forms.ChoiceField(choices=[(c, c) for c in logic.COMIDAS])
    nombre = forms.CharField(label="Alimento", max_length=60)
    kcal = forms.IntegerField(label="Kcal por porción", min_value=1, max_value=3000)
    porciones = forms.DecimalField(label="Porciones", min_value=0.5, max_value=20, decimal_places=1, initial=1)


class PesoForm(forms.Form):
    peso = forms.DecimalField(label="Peso (kg)", min_value=30, max_value=300, decimal_places=1,
                              widget=forms.NumberInput(attrs={"step": "0.1", "inputmode": "decimal"}))


class BorrarCuentaForm(forms.Form):
    confirmacion = forms.CharField(label="Escribe BORRAR para confirmar", max_length=10)

    def clean_confirmacion(self):
        valor = self.cleaned_data["confirmacion"].strip().upper()
        if valor != "BORRAR":
            raise forms.ValidationError("Escribe BORRAR, en mayúsculas o minúsculas, para confirmar.")
        return valor
