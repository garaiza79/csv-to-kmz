"""
CSV/Excel → KMZ Converter
==========================
Convierte archivos CSV o Excel a KMZ para Google Earth.
Soporta: folders anidados, iconos de Google Earth, colores, tamaños.

Deploy: Streamlit Community Cloud
"""

import streamlit as st
import pandas as pd
import zipfile
import io
import os
import re
from xml.etree import ElementTree as ET
from xml.dom import minidom

# ─── Configuración de página ───
st.set_page_config(
    page_title="CSV/Excel → KMZ Converter",
    page_icon="🌍",
    layout="wide"
)

# ─── CSS ───
st.markdown("""
<style>
    .main-header { text-align: center; padding: 0.5rem 0 1rem 0; }
    .main-header h1 { color: #1a1a2e; font-size: 2rem; margin-bottom: 0.3rem; }
    .main-header p { color: #666; font-size: 1rem; }
    .step-header { 
        background: linear-gradient(90deg, #0066cc 0%, #0066cc22 100%);
        color: white; padding: 0.5rem 1rem; border-radius: 6px;
        font-weight: 600; margin: 1rem 0 0.5rem 0;
    }
    .icon-grid {
        display: grid; grid-template-columns: repeat(10, 1fr);
        gap: 2px; max-height: 300px; overflow-y: auto;
        border: 1px solid #ddd; border-radius: 8px; padding: 4px;
        background: white;
    }
    .icon-item {
        text-align: center; padding: 3px; font-size: 0.7rem;
        border-radius: 4px; cursor: pointer;
    }
    .icon-item:hover { background: #e3f2fd; }
    .result-card {
        background: #f0f7f0; border-left: 4px solid #28a745;
        padding: 1rem; border-radius: 0 8px 8px 0; margin: 1rem 0;
    }
    .info-box {
        background: #e8f4fd; border-left: 4px solid #0066cc;
        padding: 0.8rem; border-radius: 0 8px 8px 0; margin: 0.5rem 0;
        font-size: 0.9rem;
    }
    .footer {
        text-align: center; color: #999; font-size: 0.85rem;
        margin-top: 2rem; padding-top: 1rem; border-top: 1px solid #eee;
    }
</style>
""", unsafe_allow_html=True)

# ─── Google Earth Icon URLs ───
# Los iconos 1-190 de Google Earth (paddle icons + shapes)
ICON_BASE_URLS = {
    # Numbered circles (1-10)
    1: "https://earth.google.com/earth/rpc/cc/icon?color=1976d2&id=2000&scale=4",
    # Default paddle icons
    "default": "https://maps.google.com/mapfiles/kml/paddle/{}.png",
    # Pushpin icons
    "pushpin": "https://maps.google.com/mapfiles/kml/pushpin/{}.png",
    # Shapes
    "shapes": "https://maps.google.com/mapfiles/kml/shapes/{}.png",
}

# Mapeo de número de icono a URL de Google Earth
def get_icon_url(icon_number, icon_color=None):
    """Retorna la URL del icono de Google Earth según el número."""
    icon_number = int(icon_number) if icon_number else 161

    # Paddle icons con números (1-10)
    paddle_numbered = {
        1: "1", 2: "2", 3: "3", 4: "4", 5: "5",
        6: "6", 7: "7", 8: "8", 9: "9", 10: "10"
    }

    # Paddle icons con letras (11-30) 
    paddle_letters = {
        11: "A", 12: "B", 13: "C", 14: "D", 15: "E",
        16: "F", 17: "G", 18: "H", 19: "I", 20: "J",
        21: "K", 22: "L", 23: "M", 24: "N", 25: "O",
        26: "P", 27: "Q", 28: "R", 29: "S", 30: "T",
        31: "U", 32: "V", 33: "W", 34: "X", 35: "Y",
        36: "Z"
    }

    # Shapes icons (37-70)
    shapes_map = {
        37: "arrow-reverse", 38: "arrow", 39: "donut",
        40: "forbidden", 41: "info-i", 42: "polygon",
        43: "open-diamond", 44: "square", 45: "star",
        46: "target", 47: "triangle", 48: "cross-hairs",
        49: "placemark_square", 50: "placemark_circle",
        51: "homegardenbusiness", 52: "home", 53: "home",
        54: "tree", 55: "fire", 56: "campfire",
        57: "ranger_station", 58: "hospitals", 59: "lodging",
        60: "phone", 61: "dollar", 62: "atm",
        63: "bus", 64: "cabs", 65: "caution",
        66: "earthquake", 67: "falling_rocks", 68: "post_office",
        69: "police", 70: "sunny",
        71: "mountains", 72: "travel_and_tourism",
        73: "nuclear", 74: "cross-hairs_highlight",
        75: "volcano", 76: "camera", 77: "webcam",
        78: "sun", 79: "gear", 80: "firedept",
    }

    # Pushpin icons (161-170) 
    pushpin_map = {
        161: "blue-pushpin", 162: "grn-pushpin",
        163: "ltblu-pushpin", 164: "pink-pushpin",
        165: "purple-pushpin", 166: "red-pushpin",
        167: "wht-pushpin", 168: "ylw-pushpin",
    }

    # Paddle colored icons (171-190)
    paddle_colored = {
        171: "blu-blank", 172: "blu-diamond", 173: "blu-circle",
        174: "blu-square", 175: "blu-stars",
        176: "grn-blank", 177: "grn-diamond", 178: "grn-circle",
        179: "grn-square", 180: "grn-stars",
        181: "ltblu-blank", 182: "ltblu-diamond",
        183: "pink-blank", 184: "pink-diamond",
        185: "purple-blank", 186: "purple-diamond",
        187: "red-blank", 188: "red-diamond", 189: "red-circle",
        190: "red-square",
        191: "wht-blank", 192: "wht-diamond",
        193: "ylw-blank", 194: "ylw-diamond", 195: "ylw-circle",
        196: "ylw-square", 197: "ylw-stars",
        198: "orange-blank", 199: "orange-diamond",
        200: "orange-circle",
    }

    if icon_number in paddle_numbered:
        color_suffix = "-lv" if not icon_color else f"-{icon_color}"
        return f"https://maps.google.com/mapfiles/kml/paddle/{paddle_numbered[icon_number]}{color_suffix}.png"
    elif icon_number in paddle_letters:
        return f"https://maps.google.com/mapfiles/kml/paddle/{paddle_letters[icon_number]}.png"
    elif icon_number in shapes_map:
        return f"https://maps.google.com/mapfiles/kml/shapes/{shapes_map[icon_number]}.png"
    elif icon_number in pushpin_map:
        return f"https://maps.google.com/mapfiles/kml/pushpin/{pushpin_map[icon_number]}.png"
    elif icon_number in paddle_colored:
        return f"https://maps.google.com/mapfiles/kml/paddle/{paddle_colored[icon_number]}.png"
    else:
        # Default red paddle
        return "https://maps.google.com/mapfiles/kml/paddle/red-circle.png"


def color_name_to_kml(color_name):
    """Convierte nombre de color a formato KML (aabbggrr)."""
    colors = {
        "red": "ff0000ff",
        "blue": "ffff0000",
        "green": "ff00ff00",
        "yellow": "ff00ffff",
        "orange": "ff0080ff",
        "purple": "ff800080",
        "pink": "ffcbc0ff",
        "white": "ffffffff",
        "black": "ff000000",
        "cyan": "ffffff00",
    }
    if color_name and color_name.lower() in colors:
        return colors[color_name.lower()]
    # Si es un hex color (#RRGGBB), convertir a KML (aabbggrr)
    if color_name and color_name.startswith('#') and len(color_name) == 7:
        r = color_name[1:3]
        g = color_name[3:5]
        b = color_name[5:7]
        return f"ff{b}{g}{r}"
    return None


def detect_lat_lon_columns(df):
    """Detecta automáticamente las columnas de latitud y longitud."""
    lat_patterns = ['latitude', 'lat', 'latitud', 'y', 'coord_y', 'lat_y']
    lon_patterns = ['longitude', 'lon', 'lng', 'longitud', 'long', 'x', 'coord_x', 'lon_x']

    lat_col = None
    lon_col = None

    cols_lower = {c.lower().strip(): c for c in df.columns}

    for pattern in lat_patterns:
        if pattern in cols_lower:
            lat_col = cols_lower[pattern]
            break

    for pattern in lon_patterns:
        if pattern in cols_lower:
            lon_col = cols_lower[pattern]
            break

    return lat_col, lon_col


def build_kml(df, lat_col, lon_col, name_col, folder_cols, desc_cols,
              icon_col, icon_color_col, icon_size_col,
              default_icon, default_color, default_size,
              doc_name):
    """Construye el contenido KML a partir del DataFrame."""

    # Namespace KML
    ns = "http://www.opengis.net/kml/2.2"
    ET.register_namespace('', ns)

    kml = ET.Element(f'{{{ns}}}kml')
    document = ET.SubElement(kml, f'{{{ns}}}Document')
    ET.SubElement(document, f'{{{ns}}}name').text = doc_name

    # Contador de estilos para evitar duplicados
    styles_cache = {}

    def get_or_create_style(icon_num, color, size):
        """Crea estilo KML si no existe y retorna el styleId."""
        key = f"{icon_num}_{color}_{size}"
        if key not in styles_cache:
            style_id = f"style_{len(styles_cache)}"
            style = ET.SubElement(document, f'{{{ns}}}Style')
            style.set('id', style_id)

            icon_style = ET.SubElement(style, f'{{{ns}}}IconStyle')

            # Tamaño
            if size:
                ET.SubElement(icon_style, f'{{{ns}}}scale').text = str(size)

            # Color
            kml_color = color_name_to_kml(color) if color else None
            if kml_color:
                ET.SubElement(icon_style, f'{{{ns}}}color').text = kml_color

            # Icono
            icon_el = ET.SubElement(icon_style, f'{{{ns}}}Icon')
            ET.SubElement(icon_el, f'{{{ns}}}href').text = get_icon_url(icon_num, color)

            styles_cache[key] = style_id
        return styles_cache[key]

    # Organizar datos por folders
    def get_folder_path(row):
        """Construye la ruta de folders para un registro."""
        parts = []
        for col in folder_cols:
            val = str(row.get(col, '')).strip()
            if val and val.lower() != 'nan':
                parts.append(val)
        return parts

    # Crear estructura de folders anidados
    folder_tree = {}  # path_tuple -> ET.Element

    def get_or_create_folder(path_parts, parent):
        """Crea folders anidados si no existen."""
        if not path_parts:
            return parent

        for i in range(len(path_parts)):
            key = tuple(path_parts[:i + 1])
            if key not in folder_tree:
                folder = ET.SubElement(
                    folder_tree.get(tuple(path_parts[:i]), parent),
                    f'{{{ns}}}Folder'
                )
                ET.SubElement(folder, f'{{{ns}}}name').text = path_parts[i]
                folder_tree[key] = folder

        return folder_tree[tuple(path_parts)]

    # Procesar cada fila
    placemarks_created = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            # Obtener coordenadas
            lat = row[lat_col]
            lon = row[lon_col]

            # Validar coordenadas
            if pd.isna(lat) or pd.isna(lon):
                continue

            lat = float(lat)
            lon = float(lon)

            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                errors.append(f"Fila {idx + 2}: Coordenadas fuera de rango ({lat}, {lon})")
                continue

            # Nombre del placemark
            name_val = str(row.get(name_col, f'Point_{idx + 1}')).strip()
            if name_val.lower() == 'nan':
                name_val = f'Point_{idx + 1}'

            # Obtener folder
            path_parts = get_folder_path(row)
            parent = get_or_create_folder(path_parts, document)

            # Crear placemark
            placemark = ET.SubElement(parent, f'{{{ns}}}Placemark')
            ET.SubElement(placemark, f'{{{ns}}}name').text = name_val

            # Descripción con campos seleccionados
            if desc_cols:
                desc_parts = []
                for col in desc_cols:
                    val = str(row.get(col, '')).strip()
                    if val and val.lower() != 'nan':
                        desc_parts.append(f"<b>{col}:</b> {val}")
                if desc_parts:
                    desc = ET.SubElement(placemark, f'{{{ns}}}description')
                    desc.text = "<![CDATA[" + "<br>".join(desc_parts) + "]]>"

            # Estilo (icono, color, tamaño)
            icon_num = default_icon
            color = default_color
            size = default_size

            if icon_col and icon_col in row.index:
                val = row[icon_col]
                if not pd.isna(val):
                    try:
                        icon_num = int(float(val))
                    except (ValueError, TypeError):
                        pass

            if icon_color_col and icon_color_col in row.index:
                val = row[icon_color_col]
                if not pd.isna(val) and str(val).strip().lower() != 'nan':
                    color = str(val).strip()

            if icon_size_col and icon_size_col in row.index:
                val = row[icon_size_col]
                if not pd.isna(val):
                    try:
                        size = float(val)
                    except (ValueError, TypeError):
                        pass

            style_id = get_or_create_style(icon_num, color, size)
            ET.SubElement(placemark, f'{{{ns}}}styleUrl').text = f"#{style_id}"

            # Punto geográfico
            point = ET.SubElement(placemark, f'{{{ns}}}Point')
            ET.SubElement(point, f'{{{ns}}}coordinates').text = f"{lon},{lat},0"

            placemarks_created += 1

        except Exception as e:
            errors.append(f"Fila {idx + 2}: {str(e)}")

    return kml, placemarks_created, errors, len(folder_tree)


def kml_to_kmz(kml_element):
    """Convierte un elemento KML a bytes KMZ."""
    # Serializar KML
    xml_str = ET.tostring(kml_element, encoding='unicode', xml_declaration=False)
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

    # Intentar pretty print
    try:
        xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")
        # Remover la declaración duplicada
        lines = xml_str.split('\n')
        if lines[0].startswith('<?xml'):
            xml_str = '\n'.join(lines[1:])
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
    except Exception:
        pass

    # Crear KMZ (ZIP con doc.kml dentro)
    kmz_buffer = io.BytesIO()
    with zipfile.ZipFile(kmz_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('doc.kml', xml_str.encode('utf-8'))

    return kmz_buffer.getvalue()


# ═══════════════════════════════════════════════════
#  INTERFAZ DE USUARIO
# ═══════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
    <h1>🌍 CSV/Excel → KMZ Converter</h1>
    <p>Convierte tus datos a archivos KMZ para Google Earth<br>
    con folders, iconos personalizados, colores y tamaños.</p>
</div>
""", unsafe_allow_html=True)

# ─── PASO 1: Subir archivo ───
st.markdown('<div class="step-header">📁 Paso 1: Sube tu archivo</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Archivo CSV o Excel",
    type=["csv", "xlsx", "xls"],
    help="Debe contener columnas de Latitud y Longitud"
)

if uploaded_file is not None:
    # Leer archivo
    try:
        file_name = uploaded_file.name
        if file_name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            # Para Excel, mostrar selector de hoja
            xls = pd.ExcelFile(uploaded_file)
            if len(xls.sheet_names) > 1:
                sheet = st.selectbox("Selecciona la hoja:", xls.sheet_names)
            else:
                sheet = xls.sheet_names[0]
            df = pd.read_excel(uploaded_file, sheet_name=sheet)

        st.success(f"✅ **{file_name}** — {len(df):,} filas × {len(df.columns)} columnas")

        # Preview
        with st.expander("👀 Vista previa de datos", expanded=False):
            st.dataframe(df.head(20), use_container_width=True, height=300)

    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        st.stop()

    # ─── PASO 2: Coordenadas ───
    st.markdown('<div class="step-header">📍 Paso 2: Columnas de coordenadas</div>', unsafe_allow_html=True)

    auto_lat, auto_lon = detect_lat_lon_columns(df)
    all_cols = list(df.columns)

    col1, col2 = st.columns(2)
    with col1:
        lat_col = st.selectbox(
            "Columna de Latitud",
            all_cols,
            index=all_cols.index(auto_lat) if auto_lat else 0
        )
    with col2:
        lon_col = st.selectbox(
            "Columna de Longitud",
            all_cols,
            index=all_cols.index(auto_lon) if auto_lon else min(1, len(all_cols) - 1)
        )

    # ─── PASO 3: Nombre y descripción ───
    st.markdown('<div class="step-header">🏷️ Paso 3: Nombre y descripción</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        name_col = st.selectbox(
            "Columna para nombre del punto",
            ["(auto-generar)"] + all_cols,
            help="Se muestra como título del punto en Google Earth"
        )
        if name_col == "(auto-generar)":
            name_col = None

    with col2:
        doc_name = st.text_input(
            "Nombre del documento KMZ",
            value=os.path.splitext(file_name)[0],
            help="Título que aparece en Google Earth"
        )

    desc_cols = st.multiselect(
        "Columnas para la descripción (popup)",
        all_cols,
        help="Estas columnas se mostrarán al hacer clic en un punto"
    )

    # ─── PASO 4: Organización por folders ───
    st.markdown('<div class="step-header">📂 Paso 4: Organización por folders</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
        Selecciona columnas para organizar tus datos en folders dentro de Google Earth. 
        El <strong>orden importa</strong>: la primera columna será el folder principal, 
        la segunda el subfolder, etc.
    </div>
    """, unsafe_allow_html=True)

    folder_cols = st.multiselect(
        "Columnas para folders (en orden jerárquico)",
        all_cols,
        help="Ej: Estado → Ciudad → Zona crea folders anidados"
    )

    if folder_cols:
        # Mostrar preview de la estructura
        sample = df[folder_cols].drop_duplicates().head(10)
        with st.expander("👀 Preview de estructura de folders"):
            for _, row in sample.iterrows():
                parts = [str(row[c]) for c in folder_cols if str(row[c]) != 'nan']
                if parts:
                    indent = ""
                    for i, part in enumerate(parts):
                        st.text(f"{indent}📁 {part}")
                        indent += "    "

    # ─── PASO 5: Iconos ───
    st.markdown('<div class="step-header">🎯 Paso 5: Iconos de Google Earth</div>', unsafe_allow_html=True)

    # Guía de iconos
    with st.expander("📖 Guía de iconos de Google Earth", expanded=False):
        st.markdown("""
        **Números de iconos disponibles:**
        
        | Rango | Tipo | Descripción |
        |-------|------|-------------|
        | 1-10 | Números | Círculos numerados del 1 al 10 |
        | 11-36 | Letras | Círculos con letras A-Z |
        | 37-80 | Formas | Flechas, estrellas, casas, árboles, etc. |
        | 161-168 | Pushpins | Chinchetas de colores |
        | 171-200 | Paddles | Marcadores de colores variados |
        
        **Columnas opcionales en tu archivo:**
        - **Icon**: Número del icono (1-200)
        - **IconColor**: Color del icono (red, blue, green, yellow, orange, purple, pink, white, black, o #RRGGBB)
        - **IconSize**: Escala decimal (0.5 = mitad, 1.0 = normal, 2.0 = doble)
        """)
        # Mostrar imagen de referencia si existe
        icon_ref_path = os.path.join(os.path.dirname(__file__), "google_earth_icons.png")
        if os.path.exists(icon_ref_path):
            st.image(icon_ref_path, caption="Referencia de iconos de Google Earth",
                     use_container_width=True)
        else:
            st.markdown("""
            *Para ver la referencia visual de iconos, agrega el archivo 
            `google_earth_icons.png` al repositorio.*
            
            También puedes consultar la referencia completa en 
            [Google Earth Icons](https://kml4earth.appspot.com/icons.html)
            """)

    # Configuración de iconos
    tab_default, tab_column = st.tabs(["🎯 Icono por defecto", "📊 Icono desde columna"])

    with tab_default:
        col1, col2, col3 = st.columns(3)
        with col1:
            default_icon = st.number_input(
                "Número de icono",
                min_value=1, max_value=200, value=161,
                help="Ver guía de iconos arriba"
            )
        with col2:
            default_color = st.selectbox(
                "Color del icono",
                ["(ninguno)", "red", "blue", "green", "yellow",
                 "orange", "purple", "pink", "white", "black", "cyan"],
            )
            if default_color == "(ninguno)":
                default_color = None
        with col3:
            default_size = st.number_input(
                "Tamaño del icono",
                min_value=0.1, max_value=5.0, value=1.0, step=0.1,
                help="1.0 = tamaño normal"
            )

    with tab_column:
        st.markdown("""
        <div class="info-box">
            Si tu archivo tiene columnas <strong>Icon</strong>, <strong>IconColor</strong> o 
            <strong>IconSize</strong>, selecciónalas aquí para que cada punto tenga su propio estilo.
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            icon_col = st.selectbox(
                "Columna Icon (número)",
                ["(no usar)"] + all_cols
            )
            icon_col = None if icon_col == "(no usar)" else icon_col

        with col2:
            icon_color_col = st.selectbox(
                "Columna IconColor",
                ["(no usar)"] + all_cols
            )
            icon_color_col = None if icon_color_col == "(no usar)" else icon_color_col

        with col3:
            icon_size_col = st.selectbox(
                "Columna IconSize",
                ["(no usar)"] + all_cols
            )
            icon_size_col = None if icon_size_col == "(no usar)" else icon_size_col

    # ─── PASO 6: Generar KMZ ───
    st.markdown('<div class="step-header">🚀 Paso 6: Generar KMZ</div>', unsafe_allow_html=True)

    output_name = st.text_input(
        "Nombre del archivo de salida",
        value=os.path.splitext(file_name)[0] + ".kmz"
    )

    if st.button("🌍 Generar KMZ", type="primary", use_container_width=True):
        with st.spinner("Generando archivo KMZ..."):
            try:
                kml_element, placemarks, errors, num_folders = build_kml(
                    df=df,
                    lat_col=lat_col,
                    lon_col=lon_col,
                    name_col=name_col,
                    folder_cols=folder_cols,
                    desc_cols=desc_cols,
                    icon_col=icon_col,
                    icon_color_col=icon_color_col,
                    icon_size_col=icon_size_col,
                    default_icon=default_icon,
                    default_color=default_color,
                    default_size=default_size,
                    doc_name=doc_name
                )

                kmz_bytes = kml_to_kmz(kml_element)
                kmz_size_kb = len(kmz_bytes) / 1024

                # Resultados
                st.markdown(f"""
                <div class="result-card">
                    <strong>✅ KMZ generado exitosamente</strong><br>
                    📍 <strong>{placemarks:,}</strong> puntos creados<br>
                    📁 <strong>{num_folders}</strong> folders<br>
                    💾 Tamaño: <strong>{kmz_size_kb:.1f} KB</strong>
                </div>
                """, unsafe_allow_html=True)

                if errors:
                    with st.expander(f"⚠️ {len(errors)} advertencias"):
                        for err in errors[:50]:
                            st.text(err)
                        if len(errors) > 50:
                            st.text(f"... y {len(errors) - 50} más")

                st.download_button(
                    label=f"⬇️ Descargar {output_name}",
                    data=kmz_bytes,
                    file_name=output_name,
                    mime="application/vnd.google-earth.kmz",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"Error al generar el KMZ: {e}")
                import traceback
                st.code(traceback.format_exc())

else:
    # Mensaje cuando no hay archivo
    st.markdown("""
    <div class="info-box">
        <strong>📋 Tu archivo debe contener al mínimo:</strong><br>
        • Una columna de <strong>Latitud</strong> (valores entre -90 y 90)<br>
        • Una columna de <strong>Longitud</strong> (valores entre -180 y 180)<br><br>
        <strong>Columnas opcionales para personalizar iconos:</strong><br>
        • <strong>Icon</strong>: Número del icono de Google Earth (1-200)<br>
        • <strong>IconColor</strong>: Color del icono (red, blue, green, etc.)<br>
        • <strong>IconSize</strong>: Escala del icono (0.5 a 2.0)<br>
        • <strong>Folder</strong>: Organización en carpetas (usa / para subcarpetas)
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="footer">
    Flō Networks — Herramientas GIS<br>
    Hecho con Streamlit
</div>
""", unsafe_allow_html=True)
