# Dengue Pool Detector

Esta aplicação ajuda as equipes de Controle da Dengue a identificar possíveis focos de reprodução de mosquitos detectando piscinas em imagens de satélite. Ela utiliza visão computacional para encontrar a cor azul/ciano característica das piscinas, calcula suas coordenadas geográficas e gera relatórios com os endereços.

## Como funciona (Metodologia)

1. **Busca de Imagens de Satélite**: O sistema busca blocos de imagens de satélite de alta resolução a partir de um raio em volta do local pesquisado, usando o serviço público da Esri World Imagery.
2. **Visão Computacional (OpenCV)**: Cada imagem é convertida e filtrada para isolar a cor das piscinas.
3. **Geolocalização (Geopy)**: O sistema converte os pixels de volta para coordenadas globais (Latitude/Longitude) e busca os nomes das ruas e bairros.
4. **Interface Gráfica**: Uma interface web interativa é gerada usando **Streamlit**.

## Pré-requisitos

É necessário ter o Python 3.x instalado. Instale as dependências usando o pip:

```bash
pip install requests opencv-python-headless numpy geopy folium pandas streamlit streamlit-folium
```

## Como usar a Interface Web

1. Abra o terminal na pasta do projeto.
2. Execute o seguinte comando para iniciar a interface:
   ```bash
   streamlit run app.py
   ```
3. O seu navegador vai abrir automaticamente uma aba (geralmente em `http://localhost:8501`).
4. Na barra lateral esquerda:
   - Digite o nome da cidade ou bairro que deseja rastrear (ex: "Moema, São Paulo").
   - Ajuste o "Raio de busca (km)" para definir a área de abrangência.
5. Clique em **"Iniciar Mapeamento"**.
6. Uma barra de progresso indicará o status do rastreamento em tempo real.
7. Ao finalizar, o mapa com os marcadores de piscinas aparecerá na tela e você poderá clicar no botão **"📥 Baixar Relatório (CSV)"** para exportar os endereços encontrados.
