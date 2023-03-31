from scipy.spatial import KDTree
from webcolors import (
    CSS3_HEX_TO_NAMES,
    hex_to_rgb,
)
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.colors import aci2rgb
import streamlit as st
import uuid
from io import StringIO
import math


def get_distance(lat_1, lng_1, lat_2, lng_2):
    """https://stackoverflow.com/a/44743104"""
    d_lat = lat_2 - lat_1
    d_lng = lng_2 - lng_1

    temp = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat_1) * math.cos(lat_2) * math.sin(d_lng / 2) ** 2
    )

    return 6373.0 * (2 * math.atan2(math.sqrt(temp), math.sqrt(1 - temp)))


ezdxf.addons.drawing.properties.MODEL_SPACE_BG_COLOR = "#FFFFFF"
color_multipler = {"yellowgreen": 1, "yellow": 2, "darkred": 3}


def convert_rgb_to_names(rgb_tuple):
    # a dictionary of all the hex and their respective names in css3
    css3_db = CSS3_HEX_TO_NAMES
    names = []
    rgb_values = []
    for color_hex, color_name in css3_db.items():
        names.append(color_name)
        rgb_values.append(hex_to_rgb(color_hex))

    kdt_db = KDTree(rgb_values)
    distance, index = kdt_db.query(rgb_tuple)
    return names[index]


def show_dxf2img(doc):
    msp = doc.modelspace()
    # Recommended: audit & repair DXF document before rendering
    auditor = doc.audit()
    # The auditor.errors attribute stores severe errors,
    # which *may* raise exceptions when rendering.
    if len(auditor.errors) != 0:
        raise ValueError("The DXF document is damaged and can't be converted!")

    fig = plt.figure()
    ax = fig.add_axes([0, 0, 1, 1])
    ctx = RenderContext(doc)
    ctx.set_current_layout(msp)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(msp, finalize=True)

    st.pyplot(fig)


st.markdown(
    """
# Threat modelling risk calculator
This calculator calculates the risk of your threat model like the example shown below.

## How to use:
1. Download the example VISO file below 
2. Create a threat model (based on the example) in Microsoft VISO 
2. Save the threat model as "AutoCAD Interchange (*.dxf)"
3. Upload the .dxf file
4. View your risk score
"""
)
with open("viso_demo.vsdx", "rb") as file:
    st.download_button(
        label="Download the example VISO threat model",
        data=file,
        file_name="example_threat_model.vsdx",
        mime="text/csv",
    )

st.header("The Threat Model")
dxf_file = st.file_uploader("Upload your own.dxf file")
if dxf_file is not None:
    stringio = StringIO(dxf_file.getvalue().decode("utf-8"))

    filename = str(uuid.uuid4())
    with open(filename, "w") as f:
        f.write(stringio.read())

    try:
        drawing = ezdxf.readfile(filename)
    except Exception as e:
        st.write(f"Failed to load .dxf file. {str(e)}")
        drawing = None
else:
    drawing = ezdxf.readfile("demo.dxf")
    st.write("A demo threat model is shown now.")

if drawing is not None:
    # Extract the data from the Visio file
    groups = []
    current_group = {}
    for entity in drawing.entities:
        if entity.DXFTYPE == "LWPOLYLINE" or entity.DXFTYPE == "SPLINE":
            if current_group:
                groups.append(current_group)
            current_group = {}

        if entity.DXFTYPE == "LWPOLYLINE" and entity.dxf.count == 2:
            current_group["type"] = "circle"
        elif entity.DXFTYPE == "LWPOLYLINE" and entity.dxf.count == 4:
            current_group["type"] = "rectangle"
        elif entity.DXFTYPE == "SPLINE":
            current_group["type"] = "line"
        elif entity.DXFTYPE == "MTEXT":
            current_group["text"] = entity.dxf.text.split(";")[-1].replace("\P", "")
        elif entity.DXFTYPE == "HATCH":
            rgb_color = aci2rgb(entity.dxf.color)
            current_group["color"] = convert_rgb_to_names(rgb_color)

    n_red_nodes = len(
        [
            group
            for group in groups
            if group["type"] == "circle" and group["color"] in ["darkred", "red"]
        ]
    )
    n_yellow_nodes = len(
        [
            group
            for group in groups
            if group["type"] == "circle" and group["color"] == "yellow"
        ]
    )
    n_green_nodes = len(
        [
            group
            for group in groups
            if group["type"] == "circle"
            and group["color"] in ["yellowgreen", "springgreen"]
        ]
    )

    n_edges = len(
        [group for group in groups if group["type"] == "line" and "text" in group]
    )

    n_assets = len(
        [group for group in groups if group["type"] == "rectangle" and "text" in group]
    )
    show_dxf2img(drawing)

    risk = n_red_nodes * 3 + n_yellow_nodes * 2 + n_green_nodes + n_edges

    st.markdown(
        f"""
    # Analysis
    Here we shown results of the analysis of your model
    
    #### Node analysis
    Number of green nodes: {n_green_nodes}
    
    Number of yellow nodes: {n_yellow_nodes}
    
    Number of red nodes: {n_red_nodes}
    
    #### Connection analysis
    
    Number of edges: {n_edges}
    
    #### Assets
    Number of assets: {n_assets}
    
    #### Risk analysis
    Current risk calculation:
    risk = n_red_nodes * 3 + n_yellow_nodes * 2 + n_green_nodes + n_edges
    
    Calculated risk value: **{risk}**
    """
    )
