# Remedi Bot 🤖

Automatizador de creación de incidencias en la plataforma **Remedi**, usando **Playwright** + **PyQt5**.

---

## 📁 Estructura del proyecto

```
remedi_bot/
├── main.py                  # Punto de entrada
├── requirements.txt
├── core/
│   ├── browser.py           # Lógica de automatización (Playwright)
│   └── config.py            # ⚙️ CONFIGURACIÓN — editar antes de usar
└── ui/
    └── main_window.py       # Ventana gráfica PyQt5
```

---

## ⚙️ Configuración (OBLIGATORIO antes de ejecutar)

Edita el archivo **`core/config.py`** con los datos reales:

| Variable | Descripción | Ejemplo |
|---|---|---|
| `REMEDI_URL` | URL principal de Remedi | `https://remedi.tuempresa.com` |
| `REMEDI_DOMAIN` | Dominio base (para SSO) | `remedi.tuempresa.com` |
| `NUEVA_INCIDENCIA_URL` | URL directa (opcional) | `https://remedi.tuempresa.com/new-incident` |
| `BROWSER_CHANNEL` | `"msedge"` o `"chrome"` | `"msedge"` |

> También puedes usar variables de entorno con los mismos nombres (ej: `REMEDI_URL=...`).

---

## 🚀 Instalación y ejecución

### 1. Crear entorno virtual
```bash
python -m venv venv
venv\Scripts\activate        # Windows
```

### 2. Instalar dependencias
```bash
pip install -r requirements.txt
playwright install msedge     # o: playwright install chromium
```

### 3. Ejecutar
```bash
python main.py
```

---

## 🔐 SSO de Microsoft

El bot usa un **contexto persistente** de Playwright (`launch_persistent_context`).  
Esto significa que la primera vez puede aparecer la pantalla de login de Microsoft — inicia sesión manualmente una vez y el bot recordará la sesión en ejecuciones posteriores.

La sesión se guarda en: `C:\Users\TU_USUARIO\remedi_bot_session\`

---

## 🔧 Ajuste de selectores

Si el bot no encuentra el menú automáticamente, inspecciona el DOM de Remedi (F12) y actualiza los selectores en `core/config.py`:

```python
SELECTOR_MENU_GESTION = "Gestión de Incidencias"   # Texto del menú
SELECTOR_MENU_NUEVA   = "Nueva incidencia"          # Texto del submenú
```

---

## 📌 Próximos pasos sugeridos

- [ ] Agregar formulario en la UI para rellenar campos de la incidencia
- [ ] Capturar el ID de incidencia generado automáticamente
- [ ] Exportar el ID a un archivo CSV o notificación
