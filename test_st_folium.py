import streamlit as st
import folium
from streamlit_folium import st_folium

if "counter" not in st.session_state:
    st.session_state.counter = 0

st.write(f"Rerun count: {st.session_state.counter}")
st.session_state.counter += 1

m = folium.Map(location=[-14.235, -51.925], zoom_start=4)
st_folium(m, width=800, height=500, returned_objects=[])
