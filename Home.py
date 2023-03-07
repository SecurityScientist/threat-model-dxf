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
from collections import defaultdict
import streamlit as st
import uuid
from io import StringIO


ezdxf.addons.drawing.properties.MODEL_SPACE_BG_COLOR = "#FFFFFF"
color_multipler = {
  "yellowgreen": 1,
  "yellow": 2,
  "darkred": 3
}

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


st.markdown("""
# Threat modelling risk calculator

How to use:
1. Create a threat model (like the example) in Microsoft VISO 
2. Save the threat model as "AutoCAD Interchange (*.dxf)"
3. Upload the .dxf file
4. View your risk score

""")
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
    n_nodes = defaultdict(int)
    n_edges = 0
    for entity in drawing.entities:
        if entity.DXFTYPE == 'HATCH':
            rgb_color = aci2rgb(entity.dxf.color)
            color_name = convert_rgb_to_names(rgb_color)
            n_nodes[color_name] += 1


        elif entity.DXFTYPE == 'LINE' or entity.DXFTYPE == 'SPLINE':
            n_edges += 1


    n_red_nodes = n_nodes["darkred"]
    n_yellow_nodes = n_nodes["yellow"]
    n_green_nodes = n_nodes["yellowgreen"]

    show_dxf2img(drawing)


    risk = n_red_nodes * 3 + n_yellow_nodes * 2 + n_green_nodes + n_edges

    st.write("-"*10)
    st.write(f"Number of green nodes: {n_green_nodes}")
    st.write(f"Number of yellow nodes: {n_yellow_nodes}")
    st.write(f"Number of red nodes: {n_red_nodes}")
    st.write(f"Number of edges: {n_edges}")
    st.write()
    st.write("-"*10)
    st.write("Current risk calculation:")
    st.write("risk = n_red_nodes * 3 + n_yellow_nodes * 2 + n_green_nodes + n_edges")
    st.write()
    st.write("-"*10)
    st.write(f"Calculated risk value for this attack tree: {risk}")
