# 🌍 CSV/Excel → KMZ Converter

Convierte archivos CSV o Excel a KMZ para visualizar en Google Earth, con soporte para folders anidados, iconos personalizados, colores y tamaños.

## Funcionalidades

- **Subir CSV o Excel** (.csv, .xlsx, .xls)
- **Auto-detección** de columnas Latitud/Longitud
- **Organización por folders** jerárquicos (ej: Estado → Ciudad → Zona)
- **Iconos de Google Earth** (190+ iconos disponibles)
- **Colores personalizados** por punto o globales
- **Tamaño de icono** configurable
- **Descripción popup** con las columnas que elijas

## Columnas opcionales en tu archivo

| Columna | Descripción | Ejemplo |
|---------|-------------|---------|
| Icon | Número del icono de Google Earth (1-200) | 161 |
| IconColor | Color del icono | red, blue, #FF5500 |
| IconSize | Escala del icono (decimal) | 0.8, 1.0, 1.5 |
| Folder | Carpeta/subcarpeta (separar con /) | Estado/Ciudad |

## Deploy en Streamlit Community Cloud

1. Crea un repo en GitHub con estos archivos
2. Ve a [share.streamlit.io](https://share.streamlit.io)
3. Conecta tu repo → Deploy

## Ejecución local

```bash
pip install streamlit pandas openpyxl
streamlit run app.py
```

---
Flō Networks — Herramientas GIS
