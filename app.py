import streamlit as st
import pandas as pd
import folium
import io
from streamlit_folium import st_folium
from engine import RoteirizadorEngine  # Importa a lógica da Parte 1

st.set_page_config(page_title="Dashboard Logístico", layout="wide")
engine = RoteirizadorEngine()

st.title("🚚 Sistema de Roteirização Profissional")

uploaded_file = st.sidebar.file_uploader("Subir base Excel", type=["xlsx"])

if uploaded_file:
    df_raw = pd.read_excel(uploaded_file)
    vendedor = st.sidebar.selectbox("Vendedor", df_raw['REPRESENTANTE'].unique())
    df_v = df_raw[df_raw['REPRESENTANTE'] == vendedor].dropna(subset=['lat', 'lon']).reset_index(drop=True)

    if st.sidebar.button("Calcular Rota"):
        ordem, tempos, dists = engine.resolver_tsp(df_v)
        
        if ordem:
            res = df_v.iloc[ordem].copy()
            res['SEQUENCIA'] = range(1, len(res) + 1)
            res['TEMPO_MIN'] = [round(t/60, 1) for t in tempos]
            res['DIST_KM'] = [round(d/1000, 1) for d in dists]
            res['LINK_MAPS'] = "http://maps.google.com/?q=" + res['lat'].astype(str) + "," + res['lon'].astype(str)
            st.session_state['resultado'] = res

    if 'resultado' in st.session_state:
        res = st.session_state['resultado']
        
        # Dashboard de Visualização
        tab1, tab2 = st.tabs(["📋 Roteiro Operacional", "🗺️ Visualização no Mapa"])
        
        with tab1:
            cols = ['SEQUENCIA', 'NOME_LOJA', 'ENDERECO_COMPLETO', 'LINK_MAPS', 'TEMPO_MIN', 'DIST_KM']
            st.dataframe(res[cols], column_config={"LINK_MAPS": st.column_config.LinkColumn("Abrir GPS", display_text="📍 Ir")}, hide_index=True)
            
            # Botão de Download
            buffer = io.BytesIO()
            res[cols].to_excel(buffer, index=False)
            st.download_button("📥 Baixar Excel para WhatsApp", buffer.getvalue(), f"Rota_{vendedor}.xlsx")

        with tab2:
            m = folium.Map(location=[res.iloc[0]['lat'], res.iloc[0]['lon']], zoom_start=12)
            for _, row in res.iterrows():
                folium.Marker([row['lat'], row['lon']], tooltip=f"Parada {row['SEQUENCIA']}").add_to(m)
            st_folium(m, width=1000, height=500)