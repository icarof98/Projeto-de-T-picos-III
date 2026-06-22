import streamlit as st
from streamlit_folium import st_folium
import dengue_pool_detector as detector
import os

st.set_page_config(page_title="Dengue Pool Detector", page_icon="🦟", layout="wide")

st.title("Dengue Pool Detector 🦟💦")
st.markdown("""
Esta ferramenta utiliza visão computacional em imagens de satélite para identificar
possíveis piscinas e ajudar no planejamento da fiscalização de focos do mosquito da Dengue.
""")

st.sidebar.header("Configurações de Busca")

# Allow the user to choose between searching by text name or direct coordinates
search_type = st.sidebar.radio("Buscar por:", ("Nome do Local", "Coordenadas (Lat/Lon)"))

location_query = ""
input_lat, input_lon = None, None

if search_type == "Nome do Local":
    location_query = st.sidebar.text_input("Digite a Cidade ou Bairro:", "Moema, São Paulo")
else:
    col1, col2 = st.sidebar.columns(2)
    input_lat = col1.number_input("Latitude:", value=-23.58434, format="%.5f")
    input_lon = col2.number_input("Longitude:", value=-46.66632, format="%.5f")

radius_km = st.sidebar.slider("Raio de busca (km):", min_value=0.1, max_value=2.0, value=0.5, step=0.1)

# Placeholder for the map so it always shows something, even on initial load
map_placeholder = st.empty()

if "map_rendered" not in st.session_state:
    st.session_state.map_rendered = False

if not st.session_state.map_rendered:
    # Render default map of Brazil
    import folium
    default_m = folium.Map(location=[-14.235, -51.925], zoom_start=4, tiles="OpenStreetMap")
    with map_placeholder.container():
        st.markdown("### Mapa de Visualização")
        st_folium(default_m, width=800, height=500)

if st.sidebar.button("Iniciar Mapeamento"):
    st.session_state.map_rendered = True
    map_placeholder.empty() # Clear the default map

    lat, lon = None, None

    if search_type == "Nome do Local":
        if not location_query:
            st.sidebar.error("Por favor, insira um local.")
        else:
            with st.spinner(f"Buscando coordenadas para '{location_query}'..."):
                lat, lon = detector.get_location_coordinates(location_query)

            if lat is None or lon is None:
                st.error("Não foi possível encontrar as coordenadas para este local via texto. Tente usar a opção de 'Coordenadas'.")
    else:
        # Use directly provided coordinates
        lat, lon = input_lat, input_lon

    if lat is not None and lon is not None:
        st.success(f"Buscando ao redor das coordenadas: {lat:.5f}, {lon:.5f}")

        start_lat, start_lon, end_lat, end_lon = detector.get_bounding_box(lat, lon, radius_km)

        progress_bar = st.progress(0)
        status_text = st.empty()

        pools_data = []
        has_error = False

        # Start scan using the generator
        for update in detector.scan_area_yield(start_lat, start_lon, end_lat, end_lon):
            if "error" in update:
                st.error(update["error"])
                has_error = True
                break
            elif "done" in update:
                progress_bar.progress(100)
                status_text.text("Escaneamento concluído!")
                pools_data = update["pools"]
            else:
                prog = update["progress"]
                pools_data = update["pools"]
                progress_bar.progress(prog)
                status_text.text(f"Escaneando área... {int(prog*100)}% concluído. Piscinas detectadas até agora: {len(pools_data)}")

        if not has_error:
            st.session_state.scan_complete = True
            st.session_state.pools_data = pools_data
            if len(pools_data) > 0:
                csv_path, m = detector.generate_reports(pools_data)
                st.session_state.csv_path = csv_path
                st.session_state.result_map = m
            else:
                import folium
                st.session_state.result_map = folium.Map(location=[lat, lon], zoom_start=14, tiles="OpenStreetMap")
                st.session_state.csv_path = None

if st.session_state.get("scan_complete", False):
    pools_data = st.session_state.pools_data
    st.subheader(f"Resultado: {len(pools_data)} piscina(s) detectada(s).")

    if len(pools_data) > 0:
        with map_placeholder.container():
            st.markdown("### Mapa de Piscinas Detectadas")
            st_folium(st.session_state.result_map, width=800, height=500)

        with open(st.session_state.csv_path, "r", encoding="utf-8") as f:
            st.download_button(
                label="📥 Baixar Relatório (CSV)",
                data=f.read(),
                file_name="detected_pools.csv",
                mime="text/csv"
            )
    else:
        st.info("Nenhuma piscina detectada nesta região com o raio selecionado.")
        with map_placeholder.container():
            st.markdown("### Área Buscada (Nenhuma piscina encontrada)")
            st_folium(st.session_state.result_map, width=800, height=500)
