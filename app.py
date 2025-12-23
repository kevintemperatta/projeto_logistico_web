import streamlit as st
import pandas as pd
import folium
import io
from streamlit_folium import st_folium
from engine import RoteirizadorEngine
from sklearn.cluster import KMeans

# Configurações iniciais
st.set_page_config(page_title="Dashboard Logístico", layout="wide", page_icon="🚚")
engine = RoteirizadorEngine()

st.title("🚚 Sistema de Roteirização")

uploaded_file = st.sidebar.file_uploader("1. Subir base Excel", type=["xlsx"])

if uploaded_file:
    df_raw = pd.read_excel(uploaded_file)
    
    # Seleção do Vendedor
    vendedores = df_raw['REPRESENTANTE'].unique()
    vendedor = st.sidebar.selectbox("2. Selecione o Vendedor", vendedores)
    
    # Filtragem Inicial
    df_v = df_raw[df_raw['REPRESENTANTE'] == vendedor].dropna(subset=['lat', 'lon']).reset_index(drop=True)

    # --- NOVO: FILTRO POR CIDADE (Aumenta a precisão) ---
    cidades = sorted(df_v['CIDADE'].unique()) if 'CIDADE' in df_v.columns else []
    cidades_sel = st.sidebar.multiselect("3. Filtrar por Cidade (Opcional)", cidades)
    
    if cidades_sel:
        df_v = df_v[df_v['CIDADE'].isin(cidades_sel)].reset_index(drop=True)

    # --- NOVO: LÓGICA DE CLUSTERIZAÇÃO (Agrupamento de lojas vizinhas) ---
    st.sidebar.subheader("⚙️ Configurações de Precisão")
    precisao_blocos = st.sidebar.checkbox("Agrupar lojas vizinhas (Blocos)", value=True)
    
    if precisao_blocos and len(df_v) > 3:
        # Criamos blocos geográficos para garantir que lojas próximas fiquem juntas
        n_clusters = max(1, len(df_v) // 4) 
        kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        df_v['BLOCO'] = kmeans.fit_predict(df_v[['lat', 'lon']])
    else:
        df_v['BLOCO'] = 0

    if st.sidebar.button("⚡ Calcular Rota"):
        with st.spinner(f"Otimizando geografia para {vendedor}..."):
            # Ordenar por bloco antes de enviar ao motor de busca garante que o 
            # algoritmo priorize a proximidade física imediata
            df_v = df_v.sort_values(by=['BLOCO']).reset_index(drop=True)
            
            ordem, tempos, dists = engine.resolver_tsp(df_v)
            
            if ordem:
                res = df_v.iloc[ordem].copy()
                res['SEQUENCIA'] = range(1, len(res) + 1)
                res['TEMPO_MIN'] = [round(t/60, 1) for t in tempos]
                res['DIST_KM'] = [round(d/1000, 1) for d in dists]
                res['LINK_MAPS'] = "https://www.google.com/maps/dir/?api=1&destination=" + \
                                   res['lat'].astype(str) + "," + res['lon'].astype(str)
                
                st.session_state['resultado'] = res
                st.session_state['total_km'] = round(sum(dists)/1000, 1)
                st.session_state['total_tempo'] = round(sum(tempos)/60, 1)

    if 'resultado' in st.session_state:
        res = st.session_state['resultado']
        
        # INDICADORES
        col_m1, col_m2, col_m3 = st.columns(3)
        col_m1.metric("Lojas Atendidas", len(res))
        col_m2.metric("Distância Total", f"{st.session_state['total_km']} KM")
        col_m3.metric("Tempo de Direção", f"{st.session_state['total_tempo']} MIN")

        tab1, tab2 = st.tabs(["📋 Roteiro Operacional", "🗺️ Mapa de Blocos"])
        
        with tab1:
            cols_exibir = ['SEQUENCIA', 'NOME_LOJA', 'ENDERECO_COMPLETO', 'LINK_MAPS', 'TEMPO_MIN', 'DIST_KM']
            st.dataframe(
                res[cols_exibir], 
                column_config={
                    "LINK_MAPS": st.column_config.LinkColumn("Navegação", display_text="📍 Abrir GPS"),
                    "SEQUENCIA": st.column_config.NumberColumn("Parada", format="%dº"),
                }, 
                hide_index=True, use_container_width=True
            )
            
            buffer = io.BytesIO()
            res[cols_exibir].to_excel(buffer, index=False)
            st.download_button("📥 Baixar Excel", buffer.getvalue(), f"Rota_{vendedor}.xlsx")

        with tab2:
            
            m = folium.Map(location=[res.iloc[0]['lat'], res.iloc[0]['lon']], zoom_start=12)
            
            coords_linha = []
            for _, row in res.iterrows():
                pos = [row['lat'], row['lon']]
                coords_linha.append(pos)
                
                # Cor dinâmica por bloco para visualização da precisão
                cor_bloco = '#FF4B4B' if row['BLOCO'] % 2 == 0 else '#007bff'
                
                folium.Marker(
                    location=pos,
                    tooltip=f"Parada {int(row['SEQUENCIA'])}: {row['NOME_LOJA']}",
                    icon=folium.DivIcon(html=f"""
                        <div style="font-family: sans-serif; color: white; background-color: {cor_bloco}; 
                        border-radius: 50%; width: 28px; height: 28px; display: flex; 
                        align-items: center; justify-content: center; font-weight: bold; 
                        border: 2px solid white; transform: translate(-14px, -14px);">{int(row['SEQUENCIA'])}</div>
                    """)
                ).add_to(m)
            
            folium.PolyLine(coords_linha, color="#007bff", weight=3, opacity=0.5).add_to(m)
            st_folium(m, width="100%", height=550)
else:
    st.info("👋 Suba o arquivo Excel para iniciar.")