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

use_yolo = st.sidebar.checkbox("Usar Inteligência Artificial Avançada (YOLO)", value=False, help="Requer modelo 'piscinas.pt' e biblioteca 'ultralytics' instalada.")

yolo_conf = 0.5
if use_yolo:
    yolo_conf = st.sidebar.slider("Confiança Mínima do YOLO", min_value=0.05, max_value=0.95, value=0.50, step=0.05, help="Diminua este valor se o modelo não estiver encontrando piscinas, mas cuidado: valores muito baixos podem gerar Falsos Positivos.")

if "scan_complete" not in st.session_state:
    st.session_state.scan_complete = False

if not st.session_state.scan_complete and "default_map" not in st.session_state:
    import folium
    st.session_state.default_map = folium.Map(location=[-14.235, -51.925], zoom_start=4, tiles="OpenStreetMap")

if "validation_complete" not in st.session_state:
    st.session_state.validation_complete = False

if not st.session_state.scan_complete and not st.session_state.validation_complete:
    st.markdown("### Mapa de Visualização")
    st_folium(st.session_state.default_map, width=800, height=500, returned_objects=[])

if st.sidebar.button("Iniciar Mapeamento"):
    st.session_state.scan_complete = False
    st.session_state.validation_complete = False

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
        for update in detector.scan_area_yield(start_lat, start_lon, end_lat, end_lon, use_yolo=use_yolo, yolo_conf=yolo_conf):
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
            # Initialize all pools as verified=True by default
            if "verified_pools" not in st.session_state:
                st.session_state.verified_pools = {p['id']: True for p in pools_data}
            else:
                st.session_state.verified_pools.clear()
                for p in pools_data:
                    st.session_state.verified_pools[p['id']] = True

            st.rerun()

if st.session_state.scan_complete and not st.session_state.validation_complete:
    pools_data = st.session_state.pools_data

    if len(pools_data) == 0:
        st.info("Nenhuma piscina detectada nesta região com o raio selecionado.")
        st.session_state.validation_complete = True
        if st.button("Voltar"):
            st.session_state.scan_complete = False
            st.rerun()
    else:
        st.subheader("🕵️ Painel de Validação de Piscinas")
        st.markdown("Revise as imagens recortadas abaixo. Desmarque a caixa das imagens que forem **Falsos Positivos**.")

        # Display images in a grid
        cols = st.columns(4)
        for i, pool in enumerate(pools_data):
            col = cols[i % 4]
            with col:
                # Updated parameter to avoid deprecation warning in newer Streamlit versions
                st.image(f"data:image/jpeg;base64,{pool['image_b64']}", width='stretch')
                # Ensure the key aligns with session_state modifications
                is_checked = st.checkbox(
                    f"Confirmar Piscina {i+1}",
                    value=st.session_state.verified_pools[pool['id']],
                    key=f"chk_{pool['id']}"
                )
                st.session_state.verified_pools[pool['id']] = is_checked

        if st.button("Finalizar Validação e Gerar Relatório", type="primary"):
            st.session_state.validation_complete = True
            st.rerun()

if st.session_state.validation_complete and len(st.session_state.pools_data) > 0:
    pools_data = st.session_state.pools_data

    # Filter only validated pools
    validated_pools = [p for p in pools_data if st.session_state.verified_pools.get(p['id'], False)]

    st.subheader(f"Resultado Final: {len(validated_pools)} piscina(s) confirmada(s).")

    if len(validated_pools) > 0:
        # Generate reports only for validated
        csv_path, m = detector.generate_reports(validated_pools)

        st.markdown("### Mapa de Piscinas Detectadas e Confirmadas")
        st_folium(m, width=800, height=500, returned_objects=[])

        with open(csv_path, "r", encoding="utf-8") as f:
            st.download_button(
                label="📥 Baixar Relatório (CSV)",
                data=f.read(),
                file_name="detected_pools_validated.csv",
                mime="text/csv"
            )
    else:
        st.warning("Todas as piscinas detectadas foram marcadas como falsos positivos na validação.")

    if st.button("Nova Busca"):
        st.session_state.scan_complete = False
        st.session_state.validation_complete = False
        st.rerun()
