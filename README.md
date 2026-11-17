# MyFitnessPal · App de nutrición con privacidad reforzada

App web para celular, hecha en Django, que calcula tu meta diaria de calorías y te ayuda a registrar tus comidas pidiendo lo mínimo y dándote control real sobre tus datos (Ley 21.719).

Proyecto del curso Métodos de Innovación Ágil (UDD). Caso: MyFitnessPal.

## Qué hace

| Historia (Jira) | Funcionalidad |
|---|---|
| SCRUM-12 Registro mínimo | Cuenta con correo y contraseña (cifrada). Perfil con solo 6 datos: peso, altura, edad, sexo, actividad y objetivo. Meta calórica con la fórmula Mifflin-St Jeor. |
| SCRUM-13 Consentimiento granular | Un interruptor por permiso, agrupados en *Necesario para tu plan* (salud), *Funciones opcionales* (wearables) y *Comercial · separado de tu salud* (publicidad, analítica). Los opcionales parten apagados. Se pide permiso **antes** de pedir los datos de salud. Cada decisión queda en un historial con fecha. |
| SCRUM-14 Uso diario | Diario con calorías restantes y comidas del día, buscador con 28 alimentos chilenos, ingreso manual, progreso de peso con gráfico de barras. Sin publicidad si no hay permiso. La cámara se pide en una hoja inferior solo al usarla. |
| SCRUM-15 Derechos ARSOPB | **A**cceso (ver todo), **R**ectificación (corregir y recalcular), **S**upresión (borrar cuenta y datos en cascada), **O**posición (apagar publicidad y analítica), **P**ortabilidad (descargar JSON y CSV), **B**loqueo temporal (pausa el registro). Interruptor de **modo privacidad reforzada** que apaga publicidad y analítica de una vez. |
| Navegación | Barra inferior con 5 pestañas: Diario, Progreso, Agregar, Privacidad y Menú (perfil, permisos, descargar datos, eliminar cuenta y cerrar sesión). |
| Seguridad | Cada usuario solo ve sus datos; intentar tocar datos de otro da error 404. |

## Diseño

La interfaz sigue el mockup de Figma *App nutrición con privacidad reforzada (Ley 21.719)*: fondo crema `#F4F0E7`, verde oscuro `#1C2E2B`, acento `#2F6A5F`, ocre `#8A5A12` para lo comercial y los derechos, tipografías **Inter** (texto) y **Source Serif 4** (títulos). Los colores están como variables al inicio de `nutricion/static/nutricion/app.css`. Solo tiene modo claro, igual que el mockup.

## Cómo se guardan los datos

Todo vive en una base de datos **SQLite** (`db.sqlite3`), manejada con el ORM de Django:

| Tabla | Qué guarda |
|---|---|
| `User` (Django) | Correo y contraseña **cifrada** (hash PBKDF2, nunca la contraseña real). |
| `Perfil` | Peso, altura, edad, sexo, actividad, objetivo y si el bloqueo temporal está activo. La meta calórica se calcula, no se guarda aparte. |
| `Consentimiento` | Estado actual de cada permiso. |
| `HistorialPermiso` | Cada cambio de permiso con fecha (incluye las decisiones sobre la cámara). |
| `RegistroComida` | Cada comida anotada: fecha, comida, alimento, porción, kcal y porciones. |
| `Peso` | Un registro de peso por día. |
| `Alimento` | Catálogo común de alimentos (no es dato personal). |

- Cada registro está ligado a su usuario y las vistas siempre filtran por él.
- Al eliminar la cuenta se borra todo en cascada: no queda copia.
- La portabilidad exporta directo desde estas tablas en JSON y CSV.
- Las sesiones de inicio de sesión también se guardan en la misma base.

## Probarlo en tu computador (10 minutos)

Necesitas Python 3.10 o superior.

```bash
cd myfitnesspal
python -m venv venv
# Windows:      venv\Scripts\activate
# Mac / Linux:  source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser      # para entrar al panel /admin
python manage.py runserver
```

Abre http://127.0.0.1:8000

**Desde tu celular en la misma red wifi:** ejecuta `python manage.py runserver 0.0.0.0:8000` y abre `http://IP-DE-TU-COMPUTADOR:8000` en el teléfono.

## Pruebas automáticas

```bash
python manage.py test -v 2
```

27 pruebas, una clase por historia de Jira: cálculo calórico, registro de usuario, consentimiento, diario, aislamiento entre usuarios y derechos ARSOPB. Muestren esta salida en la Sprint Review como evidencia de la Definición de Terminado.

## Publicarlo gratis en PythonAnywhere

Queda en `https://TU-USUARIO.pythonanywhere.com` y se abre desde cualquier celular.

1. Crea una cuenta **Beginner (gratis)** en https://www.pythonanywhere.com
2. Sube el código. Elige una opción:
   - **Con GitHub (recomendado):** abre *Consoles → Bash* y ejecuta `git clone https://github.com/USUARIO/myfitnesspal.git`
   - **Sin GitHub:** en *Files*, sube `myfitnesspal.zip` y en *Consoles → Bash* ejecuta `unzip myfitnesspal.zip`
3. En la misma consola Bash:
   ```bash
   cd myfitnesspal
   python3.11 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py collectstatic --noinput
   python manage.py createsuperuser
   python -c "import secrets; print(secrets.token_urlsafe(50))"   # copia esta clave secreta
   ```
4. Ve a la pestaña **Web → Add a new web app → Next → Manual configuration → Python 3.11**.
5. En la sección **Virtualenv** escribe: `/home/TU-USUARIO/myfitnesspal/venv`
6. En **Code**, abre el *WSGI configuration file*, borra todo y pega esto (cambia TU-USUARIO y la clave):
   ```python
   import os, sys
   ruta = "/home/TU-USUARIO/myfitnesspal"
   if ruta not in sys.path:
       sys.path.insert(0, ruta)
   os.environ["DJANGO_SETTINGS_MODULE"] = "config.settings"
   os.environ["DJANGO_DEBUG"] = "0"
   os.environ["DJANGO_ALLOWED_HOSTS"] = "TU-USUARIO.pythonanywhere.com"
   os.environ["DJANGO_SECRET_KEY"] = "PEGA-AQUI-LA-CLAVE-SECRETA"
   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
7. En **Static files** agrega: URL `/static/` → Directory `/home/TU-USUARIO/myfitnesspal/staticfiles`
8. En **Security** activa *Force HTTPS*.
9. Presiona el botón verde **Reload** y abre `https://TU-USUARIO.pythonanywhere.com`

**Para actualizar después de un cambio:** en Bash, `cd myfitnesspal && git pull && source venv/bin/activate && python manage.py migrate && python manage.py collectstatic --noinput`, y luego **Reload** en la pestaña Web.

El plan gratis pide entrar una vez cada 3 meses y presionar *Run until 3 months from today* para que la app siga activa.

## Instalarla como app en el teléfono

Abre el link en el celular y elige **Agregar a pantalla de inicio** (Safari: botón Compartir; Chrome: menú ⋮). Queda con ícono propio y se abre a pantalla completa.

## Panel de administración

En `/admin` (con el superusuario) se ve que los usuarios y sus registros se guardan en la base de datos. Por diseño (Privacy by Design), los datos personales se muestran **solo en lectura**: ni un administrador puede editar el perfil o la dieta de otra persona.

## Estructura

```
config/            configuración de Django (settings, urls)
nutricion/
  logic.py         reglas de negocio puras (fórmula, permisos, barras de peso)
  models.py        Perfil, Consentimiento, HistorialPermiso, Alimento, RegistroComida, Peso
  forms.py         registro, inicio de sesión, perfil, permisos, comidas, peso, borrado
  views.py         pantallas, menú, modo reforzado y derechos ARSOPB
  tests.py         27 pruebas de aceptación
  templates/       pantallas (HTML); los archivos con _ son piezas reutilizables
  templatetags/    filtro "miles" para mostrar 1.530 en vez de 1530
  static/          estilos (tokens del mockup), ícono y manifiesto para instalar en el teléfono
  migrations/      estructura de la base de datos + catálogo de alimentos
```

## Limitaciones conocidas (para decirlas en la Review)

- El código de barras y la foto del plato registran el permiso de cámara, pero aún no leen imágenes.
- Retos con amigos aparecen en el Menú como "Pronto": no están implementados. La conexión con relojes deportivos tampoco.
- Diferencias con el mockup: no se muestran macronutrientes ni ejercicio (la app no los registra), y el borrado es inmediato en vez de esperar 30 días.
- Las calorías del catálogo son aproximadas.
- No hay recuperación de contraseña por correo (requiere configurar un servidor de correo).
- Base de datos SQLite **sin cifrar en disco**: quien acceda al archivo puede leer los datos de salud (solo la contraseña está protegida). Suficiente para la demo y un curso; para producción real se usaría PostgreSQL con cifrado en reposo.
