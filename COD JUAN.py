import streamlit as st
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import os
from matplotlib.lines import Line2D
from io import BytesIO

st.set_page_config(layout="wide")

st.title("Graficador de Taladros")

# ---------------------------
# CONFIGURACIÓN
# ---------------------------

cmap = st.selectbox(
    "Seleccione mapa de colores",
    sorted([m for m in plt.colormaps() if not m.endswith("_r")]),
    index=plt.colormaps().index("viridis")
)

# ---------------------------
# SUBIR ARCHIVOS
# ---------------------------

archivo_excel = st.file_uploader(
    "Subir archivo Excel",
    type=["xlsx"]
)

archivos_dxf = st.file_uploader(
    "Subir archivos DXF (opcional)",
    type=["dxf"],
    accept_multiple_files=True
)

# ---------------------------
# FUNCIÓN DXF
# ---------------------------

def obtener_coordenadas(geom):

    if geom.is_empty:
        return []

    coords_limpias = []

    def procesar_coord(c):
        if len(c) >= 2:
            return (c[0], c[1])
        return None

    if geom.geom_type == 'Point':
        return [(geom.x, geom.y)]

    elif geom.geom_type in ['LineString', 'Polygon']:
        try:
            for c in geom.coords:
                xy = procesar_coord(c)
                if xy:
                    coords_limpias.append(xy)
        except:
            pass

    elif geom.geom_type == 'MultiLineString':
        for line in geom.geoms:
            for c in line.coords:
                xy = procesar_coord(c)
                if xy:
                    coords_limpias.append(xy)

    return coords_limpias

# ---------------------------
# GENERAR GRÁFICO
# ---------------------------

if archivo_excel is not None:

    df = pd.read_excel(archivo_excel)

    fig, ax = plt.subplots(figsize=(14, 14), dpi=200)

    # ---------------------------
    # LEER DXF
    # ---------------------------

    if archivos_dxf:

        for archivo_dxf in archivos_dxf:

            try:
                nombre_archivo_dxf = os.path.splitext(archivo_dxf.name)[0]

                with open(f"temp_{archivo_dxf.name}", "wb") as f:
                    f.write(archivo_dxf.getbuffer())

                gdf = gpd.read_file(
                    f"temp_{archivo_dxf.name}",
                    engine="pyogrio"
                )

                gdf['coordenadas'] = gdf['geometry'].apply(obtener_coordenadas)

                for coords in gdf['coordenadas']:

                    if coords:

                        xs, ys = zip(*coords)

                        if nombre_archivo_dxf.lower() == "poligono":

                            ax.plot(
                                xs,
                                ys,
                                linestyle='-',
                                linewidth=2,
                                color='black'
                            )

                        else:

                            ax.plot(
                                xs,
                                ys,
                                linestyle='-',
                                linewidth=2.5,
                                label=nombre_archivo_dxf
                            )

            except Exception as e:
                st.error(f"Error en DXF {archivo_dxf.name}: {e}")

    # ---------------------------
    # TALADROS NORMALES
    # ---------------------------

    df_validos = df[df['ESTADO'] != 'TAPADO']

    scatter = ax.scatter(
        df_validos['X'],
        df_validos['Y'],
        c=df_validos['CARGA'],
        cmap=cmap,
        s=60,
        edgecolor='k',
        linewidth=0.5,
        label='Taladros'
    )

    # ---------------------------
    # TAPADOS
    # ---------------------------

    df_tapados = df[df['ESTADO'] == 'TAPADO']

    ax.scatter(
        df_tapados['X'],
        df_tapados['Y'],
        c='red',
        marker='x',
        s=150,
        label='Tapados'
    )

    # ---------------------------
    # CÍRCULOS MAGENTA
    # ---------------------------

    for _, row in df_validos.iterrows():

        tipo = str(row['TIPO']).upper()

        L = row['LONGITUD']

        x = row['X']
        y = row['Y']

        dibujar = False

        if tipo == "BUFFER" and L < 15:
            dibujar = True

        elif tipo == "PP" and L < 14:
            dibujar = True

        elif tipo == "PRODUCCION" and L < 15:
            dibujar = True

        if dibujar:

            circle = plt.Circle(
                (x, y),
                radius=1.3,
                edgecolor='magenta',
                facecolor='none',
                linewidth=2.2
            )

            ax.add_patch(circle)

    # ---------------------------
    # AJUSTES
    # ---------------------------

    ax.set_xlabel("X")
    ax.set_ylabel("Y")

    ax.set_aspect('equal', adjustable='box')

    ax.grid(True, alpha=0.3)

    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label("Carga")

    legend_elements = [
        Line2D(
            [0],
            [0],
            marker='o',
            color='w',
            markerfacecolor='none',
            markeredgecolor='magenta',
            markersize=10,
            label='Taladros substándar'
        )
    ]

    handles, labels = ax.get_legend_handles_labels()

    ax.legend(
        handles + legend_elements,
        labels + ['Taladros substándar'],
        loc='lower right',
        fontsize=8
    )

    plt.tight_layout()

    # ---------------------------
    # MOSTRAR
    # ---------------------------

    st.pyplot(fig)

    # ---------------------------
    # DESCARGA HD
    # ---------------------------

    buffer = BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=300,
        bbox_inches='tight'
    )

    st.download_button(
        label="Descargar gráfico HD",
        data=buffer.getvalue(),
        file_name="grafico_taladros.png",
        mime="image/png"
    )