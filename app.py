"""
CSV/Excel → KMZ Converter v2
==============================
Convierte archivos CSV o Excel a KMZ para Google Earth.
Soporta: folders anidados, iconos de Google Earth, colores, tamaños, visibilidad.

Deploy: Streamlit Community Cloud
"""

import streamlit as st
import pandas as pd
import zipfile
import io
import os
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
    /* Icon gallery */
    .icon-gallery {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(72px, 1fr));
        gap: 4px;
        max-height: 350px;
        overflow-y: auto;
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 6px;
        background: #fafafa;
    }
    .icon-card {
        display: flex; flex-direction: column;
        align-items: center; justify-content: center;
        padding: 4px 2px;
        border-radius: 6px;
        border: 1px solid transparent;
        transition: all 0.15s;
        background: white;
    }
    .icon-card:hover {
        border-color: #0066cc;
        background: #e3f2fd;
        transform: scale(1.08);
    }
    .icon-card img { width: 28px; height: 28px; }
    .icon-card .icon-num {
        font-size: 0.65rem; color: #666;
        margin-top: 2px; font-weight: 600;
    }
    .icon-card .icon-label {
        font-size: 0.55rem; color: #999;
        white-space: nowrap; overflow: hidden;
        text-overflow: ellipsis; max-width: 68px;
    }
    .icon-section-title {
        font-weight: 700; font-size: 0.85rem;
        color: #333; margin: 8px 0 4px 0;
        padding: 3px 8px; background: #f0f0f0;
        border-radius: 4px;
    }
    .selected-icon-preview {
        display: flex; align-items: center; gap: 12px;
        background: #f8f9fa; border: 2px solid #0066cc;
        border-radius: 8px; padding: 10px 16px; margin: 8px 0;
    }
    .selected-icon-preview img { width: 36px; height: 36px; }
    .selected-icon-preview .icon-info { font-size: 0.9rem; color: #333; }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════
#  ICON CATALOG
# ═══════════════════════════════════════════════════════════

ICON_CATALOG = {}

# 1-10: Numbered paddles
for i in range(1, 11):
    ICON_CATALOG[i] = {
        "name": f"Número {i}",
        "url": f"https://maps.google.com/mapfiles/kml/paddle/{i}.png",
        "category": "Números (1-10)"
    }

# 11-36: Letter paddles
for i, letter in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ", start=11):
    ICON_CATALOG[i] = {
        "name": f"Letra {letter}",
        "url": f"https://maps.google.com/mapfiles/kml/paddle/{letter}.png",
        "category": "Letras (11-36)"
    }

# 37-80: Shapes
_shapes = {
    37: ("arrow-reverse", "Flecha inversa"), 38: ("arrow", "Flecha"),
    39: ("donut", "Donut"), 40: ("forbidden", "Prohibido"),
    41: ("info-i", "Info"), 42: ("polygon", "Polígono"),
    43: ("open-diamond", "Diamante"), 44: ("square", "Cuadrado"),
    45: ("star", "Estrella"), 46: ("target", "Objetivo"),
    47: ("triangle", "Triángulo"), 48: ("cross-hairs", "Mira"),
    49: ("placemark_square", "Marcador □"),
    50: ("placemark_circle", "Marcador ○"),
    51: ("homegardenbusiness", "Casa/negocio"),
    52: ("homes", "Casa azul"), 53: ("home", "Casa"),
    54: ("tree", "Árbol"), 55: ("fire", "Fuego"),
    56: ("campfire", "Fogata"), 57: ("ranger_station", "Ranger"),
    58: ("hospitals", "Hospital"), 59: ("lodging", "Hotel"),
    60: ("phone", "Teléfono"), 61: ("dollar", "Dólar"),
    62: ("atm", "ATM"), 63: ("bus", "Autobús"),
    64: ("cabs", "Taxi"), 65: ("caution", "Precaución"),
    66: ("earthquake", "Sismo"), 67: ("falling_rocks", "Derrumbe"),
    68: ("post_office", "Correo"), 69: ("police", "Policía"),
    70: ("sunny", "Soleado"), 71: ("mountains", "Montañas"),
    72: ("travel_and_tourism", "Turismo"), 73: ("nuclear", "Nuclear"),
    74: ("cross-hairs_highlight", "Mira resaltada"),
    75: ("volcano", "Volcán"), 76: ("camera", "Cámara"),
    77: ("webcam", "Webcam"), 78: ("sun", "Sol"),
    79: ("gear", "Engranaje"), 80: ("firedept", "Bomberos"),
}
for num, (slug, name) in _shapes.items():
    ICON_CATALOG[num] = {
        "name": name,
        "url": f"https://maps.google.com/mapfiles/kml/shapes/{slug}.png",
        "category": "Formas (37-80)"
    }

# 161-168: Pushpins
_pushpins = {
    161: ("blue-pushpin", "Chincheta azul"),
    162: ("grn-pushpin", "Chincheta verde"),
    163: ("ltblu-pushpin", "Chincheta celeste"),
    164: ("pink-pushpin", "Chincheta rosa"),
    165: ("purple-pushpin", "Chincheta morada"),
    166: ("red-pushpin", "Chincheta roja"),
    167: ("wht-pushpin", "Chincheta blanca"),
    168: ("ylw-pushpin", "Chincheta amarilla"),
}
for num, (slug, name) in _pushpins.items():
    ICON_CATALOG[num] = {
        "name": name,
        "url": f"https://maps.google.com/mapfiles/kml/pushpin/{slug}.png",
        "category": "Chinchetas (161-168)"
    }

# 171-200: Colored paddles
_paddles = {
    171: ("blu-blank", "Azul"), 172: ("blu-diamond", "Azul diamante"),
    173: ("blu-circle", "Azul círculo"), 174: ("blu-square", "Azul cuadrado"),
    175: ("blu-stars", "Azul estrella"),
    176: ("grn-blank", "Verde"), 177: ("grn-diamond", "Verde diamante"),
    178: ("grn-circle", "Verde círculo"), 179: ("grn-square", "Verde cuadrado"),
    180: ("grn-stars", "Verde estrella"),
    181: ("ltblu-blank", "Celeste"), 182: ("ltblu-diamond", "Celeste diamante"),
    183: ("pink-blank", "Rosa"), 184: ("pink-diamond", "Rosa diamante"),
    185: ("purple-blank", "Morado"), 186: ("purple-diamond", "Morado diamante"),
    187: ("red-blank", "Rojo"), 188: ("red-diamond", "Rojo diamante"),
    189: ("red-circle", "Rojo círculo"), 190: ("red-square", "Rojo cuadrado"),
    191: ("wht-blank", "Blanco"), 192: ("wht-diamond", "Blanco diamante"),
    193: ("ylw-blank", "Amarillo"), 194: ("ylw-diamond", "Amarillo diamante"),
    195: ("ylw-circle", "Amarillo círculo"), 196: ("ylw-square", "Amarillo cuadrado"),
    197: ("ylw-stars", "Amarillo estrella"),
    198: ("orange-blank", "Naranja"), 199: ("orange-diamond", "Naranja diamante"),
    200: ("orange-circle", "Naranja círculo"),
}
for num, (slug, name) in _paddles.items():
    ICON_CATALOG[num] = {
        "name": name,
        "url": f"https://maps.google.com/mapfiles/kml/paddle/{slug}.png",
        "category": "Marcadores de color (171-200)"
    }


def get_icon_url(icon_number, icon_color=None):
    """Retorna la URL del icono de Google Earth según el número."""
    icon_number = int(icon_number) if icon_number else 161
    if icon_number in ICON_CATALOG:
        return ICON_CATALOG[icon_number]["url"]
    return "https://maps.google.com/mapfiles/kml/paddle/red-circle.png"


def render_icon_gallery():
    """Genera HTML de la galería de iconos organizada por categoría."""
    categories = {}
    for num, info in sorted(ICON_CATALOG.items()):
        cat = info["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append((num, info))

    html = ""
    for cat_name, icons in categories.items():
        html += f'<div class="icon-section-title">{cat_name}</div>'
        html += '<div class="icon-gallery">'
        for num, info in icons:
            html += f'''<div class="icon-card" title="#{num} - {info['name']}">
                <img src="{info['url']}" alt="{info['name']}">
                <div class="icon-num">#{num}</div>
                <div class="icon-label">{info['name']}</div>
            </div>'''
        html += '</div>'
    return html


# ═══════════════════════════════════════════════════════════
#  FUNCIONES AUXILIARES
# ═══════════════════════════════════════════════════════════

def color_name_to_kml(color_name):
    """Convierte nombre de color a formato KML (aabbggrr)."""
    colors = {
        "red": "ff0000ff", "blue": "ffff0000", "green": "ff00ff00",
        "yellow": "ff00ffff", "orange": "ff0080ff", "purple": "ff800080",
        "pink": "ffcbc0ff", "white": "ffffffff", "black": "ff000000",
        "cyan": "ffffff00",
    }
    if color_name and color_name.lower() in colors:
        return colors[color_name.lower()]
    if color_name and color_name.startswith('#') and len(color_name) == 7:
        r, g, b = color_name[1:3], color_name[3:5], color_name[5:7]
        return f"ff{b}{g}{r}"
    return None


def detect_lat_lon_columns(df):
    """Detecta automáticamente las columnas de latitud y longitud."""
    lat_patterns = ['latitude', 'lat', 'latitud', 'y', 'coord_y', 'lat_y']
    lon_patterns = ['longitude', 'lon', 'lng', 'longitud', 'long', 'x', 'coord_x', 'lon_x']
    cols_lower = {c.lower().strip(): c for c in df.columns}
    lat_col = next((cols_lower[p] for p in lat_patterns if p in cols_lower), None)
    lon_col = next((cols_lower[p] for p in lon_patterns if p in cols_lower), None)
    return lat_col, lon_col


def is_visible(value):
    """Evalúa si un valor indica visibilidad (True/Yes/x = visible)."""
    if pd.isna(value):
        return True
    val = str(value).strip().lower()
    if val in ('true', 'yes', 'x', '1', 'si', 'sí'):
        return True
    if val in ('false', 'no', '0', ''):
        return False
    return True


# ═══════════════════════════════════════════════════════════
#  BUILD KML
# ═══════════════════════════════════════════════════════════

def build_kml(df, lat_col, lon_col, name_col, folder_cols, desc_cols,
              icon_col, icon_color_col, icon_size_col, visibility_col,
              default_icon, default_color, default_size, default_visibility,
              doc_name):
    """Construye el contenido KML a partir del DataFrame."""

    ns = "http://www.opengis.net/kml/2.2"
    ET.register_namespace('', ns)

    kml = ET.Element(f'{{{ns}}}kml')
    document = ET.SubElement(kml, f'{{{ns}}}Document')
    ET.SubElement(document, f'{{{ns}}}name').text = doc_name

    styles_cache = {}

    def get_or_create_style(icon_num, color, size):
        key = f"{icon_num}_{color}_{size}"
        if key not in styles_cache:
            style_id = f"style_{len(styles_cache)}"
            style = ET.SubElement(document, f'{{{ns}}}Style')
            style.set('id', style_id)
            icon_style = ET.SubElement(style, f'{{{ns}}}IconStyle')
            if size:
                ET.SubElement(icon_style, f'{{{ns}}}scale').text = str(size)
            kml_color = color_name_to_kml(color) if color else None
            if kml_color:
                ET.SubElement(icon_style, f'{{{ns}}}color').text = kml_color
            icon_el = ET.SubElement(icon_style, f'{{{ns}}}Icon')
            ET.SubElement(icon_el, f'{{{ns}}}href').text = get_icon_url(icon_num, color)
            styles_cache[key] = style_id
        return styles_cache[key]

    def get_folder_path(row):
        parts = []
        for col in folder_cols:
            val = str(row.get(col, '')).strip()
            if val and val.lower() != 'nan':
                parts.append(val)
        return parts

    folder_tree = {}

    def get_or_create_folder(path_parts, parent):
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

    placemarks_created = 0
    hidden_count = 0
    errors = []

    for idx, row in df.iterrows():
        try:
            lat = row[lat_col]
            lon = row[lon_col]

            if pd.isna(lat) or pd.isna(lon):
                continue

            lat = float(lat)
            lon = float(lon)

            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                errors.append(f"Fila {idx + 2}: Coordenadas fuera de rango ({lat}, {lon})")
                continue

            name_val = str(row.get(name_col, f'Point_{idx + 1}')).strip()
            if name_val.lower() == 'nan':
                name_val = f'Point_{idx + 1}'

            path_parts = get_folder_path(row)
            parent = get_or_create_folder(path_parts, document)

            placemark = ET.SubElement(parent, f'{{{ns}}}Placemark')
            ET.SubElement(placemark, f'{{{ns}}}name').text = name_val

            # Visibility
            if visibility_col and visibility_col in row.index:
                vis = is_visible(row[visibility_col])
            else:
                vis = default_visibility

            ET.SubElement(placemark, f'{{{ns}}}visibility').text = "1" if vis else "0"
            if not vis:
                hidden_count += 1

            # Descripción
            if desc_cols:
                desc_parts = []
                for col in desc_cols:
                    val = str(row.get(col, '')).strip()
                    if val and val.lower() != 'nan':
                        desc_parts.append(f"<b>{col}:</b> {val}")
                if desc_parts:
                    desc = ET.SubElement(placemark, f'{{{ns}}}description')
                    desc.text = "<![CDATA[" + "<br>".join(desc_parts) + "]]>"

            # Estilo
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

            point = ET.SubElement(placemark, f'{{{ns}}}Point')
            ET.SubElement(point, f'{{{ns}}}coordinates').text = f"{lon},{lat},0"

            placemarks_created += 1

        except Exception as e:
            errors.append(f"Fila {idx + 2}: {str(e)}")

    return kml, placemarks_created, hidden_count, errors, len(folder_tree)


def kml_to_kmz(kml_element):
    """Convierte un elemento KML a bytes KMZ."""
    xml_str = ET.tostring(kml_element, encoding='unicode', xml_declaration=False)
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str

    try:
        xml_str = minidom.parseString(xml_str).toprettyxml(indent="  ")
        lines = xml_str.split('\n')
        if lines[0].startswith('<?xml'):
            xml_str = '\n'.join(lines[1:])
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str
    except Exception:
        pass

    kmz_buffer = io.BytesIO()
    with zipfile.ZipFile(kmz_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('doc.kml', xml_str.encode('utf-8'))
    return kmz_buffer.getvalue()


# ═══════════════════════════════════════════════════════════
#  INTERFAZ DE USUARIO
# ═══════════════════════════════════════════════════════════

st.markdown("""
<div class="main-header">
    <h1>🌍 CSV/Excel → KMZ Converter</h1>
    <p>Convierte tus datos a archivos KMZ para Google Earth<br>
    con folders, iconos personalizados, colores, tamaños y visibilidad.</p>
</div>
""", unsafe_allow_html=True)

# ─── PASO 1 ───
st.markdown('<div class="step-header">📁 Paso 1: Sube tu archivo</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Archivo CSV o Excel",
    type=["csv", "xlsx", "xls"],
    help="Debe contener columnas de Latitud y Longitud"
)

if uploaded_file is not None:
    try:
        file_name = uploaded_file.name
        if file_name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        else:
            xls = pd.ExcelFile(uploaded_file)
            if len(xls.sheet_names) > 1:
                sheet = st.selectbox("Selecciona la hoja:", xls.sheet_names)
            else:
                sheet = xls.sheet_names[0]
            df = pd.read_excel(uploaded_file, sheet_name=sheet)

        st.success(f"✅ **{file_name}** — {len(df):,} filas × {len(df.columns)} columnas")

        with st.expander("👀 Vista previa de datos", expanded=False):
            st.dataframe(df.head(20), use_container_width=True, height=300)

    except Exception as e:
        st.error(f"Error al leer el archivo: {e}")
        st.stop()

    all_cols = list(df.columns)

    # ─── PASO 2 ───
    st.markdown('<div class="step-header">📍 Paso 2: Columnas de coordenadas</div>', unsafe_allow_html=True)

    auto_lat, auto_lon = detect_lat_lon_columns(df)
    col1, col2 = st.columns(2)
    with col1:
        lat_col = st.selectbox("Columna de Latitud", all_cols,
                               index=all_cols.index(auto_lat) if auto_lat else 0)
    with col2:
        lon_col = st.selectbox("Columna de Longitud", all_cols,
                               index=all_cols.index(auto_lon) if auto_lon else min(1, len(all_cols) - 1))

    # ─── PASO 3 ───
    st.markdown('<div class="step-header">🏷️ Paso 3: Nombre y descripción</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        name_col = st.selectbox("Columna para nombre del punto", ["(auto-generar)"] + all_cols,
                                help="Se muestra como título del punto en Google Earth")
        if name_col == "(auto-generar)":
            name_col = None
    with col2:
        doc_name = st.text_input("Nombre del documento KMZ",
                                 value=os.path.splitext(file_name)[0],
                                 help="Título que aparece en Google Earth")

    desc_cols = st.multiselect("Columnas para la descripción (popup)", all_cols,
                               help="Estas columnas se mostrarán al hacer clic en un punto")

    # ─── PASO 4 ───
    st.markdown('<div class="step-header">📂 Paso 4: Organización por folders</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
        Selecciona columnas para organizar tus datos en folders dentro de Google Earth. 
        El <strong>orden importa</strong>: la primera columna será el folder principal, 
        la segunda el subfolder, etc.
    </div>
    """, unsafe_allow_html=True)

    folder_cols = st.multiselect("Columnas para folders (en orden jerárquico)", all_cols,
                                 help="Ej: Estado → Ciudad → Zona crea folders anidados")

    if folder_cols:
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

    # Galería visual
    with st.expander("📖 Galería de iconos — click para ver todos los iconos disponibles", expanded=False):
        st.markdown("""
        <div class="info-box">
            Usa el <strong>número (#)</strong> debajo de cada icono para seleccionarlo como 
            icono por defecto, o ponlo en la columna <strong>Icon</strong> de tu archivo 
            para asignar iconos diferentes por fila.
        </div>
        """, unsafe_allow_html=True)
        st.markdown(render_icon_gallery(), unsafe_allow_html=True)

    # Tabs de configuración
    tab_default, tab_column = st.tabs(["🎯 Icono por defecto", "📊 Icono desde columna"])

    with tab_default:
        col1, col2, col3 = st.columns(3)
        with col1:
            default_icon = st.number_input("Número de icono", min_value=1, max_value=200, value=161,
                                           help="Abre la galería arriba para ver los iconos")
        with col2:
            default_color = st.selectbox("Color del icono",
                                         ["(ninguno)", "red", "blue", "green", "yellow",
                                          "orange", "purple", "pink", "white", "black", "cyan"])
            if default_color == "(ninguno)":
                default_color = None
        with col3:
            default_size = st.number_input("Tamaño del icono", min_value=0.1, max_value=5.0,
                                           value=1.0, step=0.1, help="1.0 = tamaño normal")

        # Preview del icono seleccionado
        if default_icon in ICON_CATALOG:
            info = ICON_CATALOG[default_icon]
            st.markdown(f"""
            <div class="selected-icon-preview">
                <img src="{info['url']}" alt="{info['name']}">
                <div class="icon-info">
                    <strong>#{default_icon}</strong> — {info['name']}
                    <br><span style="color:#888; font-size:0.8rem;">{info['category']}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with tab_column:
        st.markdown("""
        <div class="info-box">
            Si tu archivo tiene columnas <strong>Icon</strong>, <strong>IconColor</strong> o 
            <strong>IconSize</strong>, selecciónalas aquí para que cada punto tenga su propio estilo.
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns(3)
        with col1:
            icon_col = st.selectbox("Columna Icon (número)", ["(no usar)"] + all_cols)
            icon_col = None if icon_col == "(no usar)" else icon_col
        with col2:
            icon_color_col = st.selectbox("Columna IconColor", ["(no usar)"] + all_cols)
            icon_color_col = None if icon_color_col == "(no usar)" else icon_color_col
        with col3:
            icon_size_col = st.selectbox("Columna IconSize", ["(no usar)"] + all_cols)
            icon_size_col = None if icon_size_col == "(no usar)" else icon_size_col

    # ─── PASO 6: Visibilidad ───
    st.markdown('<div class="step-header">👁️ Paso 6: Visibilidad (IsVisible)</div>', unsafe_allow_html=True)

    st.markdown("""
    <div class="info-box">
        Controla qué elementos se muestran u ocultan al abrir el KMZ en Google Earth.
        Equivale a marcar/desmarcar la casilla junto a cada elemento en el panel "My Places".<br><br>
        <strong>Valores válidos en la columna:</strong> True, Yes, x, Si → visible | False, No, (vacío) → oculto<br>
        <strong>Tip de rendimiento:</strong> Si tienes miles de filas, establece visibilidad en "Oculto" por defecto 
        para que Google Earth cargue rápido. Luego activa folders individualmente cuando los necesites.
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        visibility_col = st.selectbox("Columna IsVisible", ["(no usar)"] + all_cols,
                                      help="Valores: True, Yes, x, Si, False, No, vacío")
        visibility_col = None if visibility_col == "(no usar)" else visibility_col
    with col2:
        default_visibility = st.selectbox("Visibilidad por defecto",
                                          ["Visible (mostrar)", "Oculto (esconder)"],
                                          help="Se aplica cuando no hay columna o el valor está vacío")
        default_visibility = default_visibility.startswith("Visible")

    # ─── PASO 7: Generar ───
    st.markdown('<div class="step-header">🚀 Paso 7: Generar KMZ</div>', unsafe_allow_html=True)

    output_name = st.text_input("Nombre del archivo de salida",
                                value=os.path.splitext(file_name)[0] + ".kmz")

    if st.button("🌍 Generar KMZ", type="primary", use_container_width=True):
        with st.spinner("Generando archivo KMZ..."):
            try:
                kml_element, placemarks, hidden, errors, num_folders = build_kml(
                    df=df, lat_col=lat_col, lon_col=lon_col,
                    name_col=name_col, folder_cols=folder_cols,
                    desc_cols=desc_cols, icon_col=icon_col,
                    icon_color_col=icon_color_col, icon_size_col=icon_size_col,
                    visibility_col=visibility_col,
                    default_icon=default_icon, default_color=default_color,
                    default_size=default_size, default_visibility=default_visibility,
                    doc_name=doc_name
                )

                kmz_bytes = kml_to_kmz(kml_element)
                kmz_size_kb = len(kmz_bytes) / 1024

                vis_info = ""
                if hidden > 0:
                    vis_info = f"<br>👁️ <strong>{placemarks - hidden:,}</strong> visibles, <strong>{hidden:,}</strong> ocultos"

                st.markdown(f"""
                <div class="result-card">
                    <strong>✅ KMZ generado exitosamente</strong><br>
                    📍 <strong>{placemarks:,}</strong> puntos creados{vis_info}<br>
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
    st.markdown("""
    <div class="info-box">
        <strong>📋 Tu archivo debe contener al mínimo:</strong><br>
        • Una columna de <strong>Latitud</strong> (valores entre -90 y 90)<br>
        • Una columna de <strong>Longitud</strong> (valores entre -180 y 180)<br><br>
        <strong>Columnas opcionales para personalizar:</strong><br>
        • <strong>Icon</strong>: Número del icono de Google Earth (1-200)<br>
        • <strong>IconColor</strong>: Color del icono (red, blue, green, etc. o #RRGGBB)<br>
        • <strong>IconSize</strong>: Escala del icono (0.5 a 2.0)<br>
        • <strong>IsVisible</strong>: Mostrar/ocultar elementos (True, Yes, x, False, No)<br>
        • <strong>Folder</strong>: Organización en carpetas
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("""
<div class="footer">
    Flō Networks — Herramientas GIS<br>
    Hecho con Streamlit
</div>
""", unsafe_allow_html=True)
