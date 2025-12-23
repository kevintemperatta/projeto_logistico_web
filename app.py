import streamlit as st
import pandas as pd
import folium
import io
from streamlit_folium import st_folium
from engine import RoteirizadorEngine
from sklearn.cluster import KMeans

# Configurações Iniciais
st.set_page_config(page_title="Roteirizador", layout="wide", page_icon="🚚")
engine = RoteirizadorEngine()

st.title("🚚 Roteirizador - Visualização de Rota")

uploaded_file = st.sidebar.file_uploader("1. Subir base Excel", type=["xlsx"])

if uploaded_file:
    df_raw = pd.read_excel(uploaded_file)
    vendedor = st.sidebar.selectbox("2. Selecione o Vendedor", df_raw['REPRESENTANTE'].unique())
    
    df_v = df_raw[df_raw['REPRESENTANTE'] == vendedor].dropna(subset=['lat', 'lon']).reset_index(drop=True)
    num_lojas = len(df_v)

    if st.sidebar.button("⚡ Gerar Planejamento Mensal"):
        with st.spinner(f"Processando lógica..."):
            
            # 1. AGRUPAMENTO GEOGRÁFICO (Clusters)
            kmeans = KMeans(n_clusters=4, n_init=100, random_state=42)
            df_v['CLUSTER'] = kmeans.fit_predict(df_v[['lat', 'lon']])
            
            centroids = df_v.groupby('CLUSTER')[['lat', 'lon']].mean().sort_values(by='lat').index.tolist()
            mapa_semanas = {centroids[i]: f"Semana {i+1}" for i in range(4)}
            df_v['SEMANA'] = df_v['CLUSTER'].map(mapa_semanas)
            df_v['REPETIDA'] = False

            # 2. LÓGICA DE RECORRÊNCIA (10 a 30 lojas)
            if 10 <= num_lojas <= 30:
                num_extras = min(num_lojas, 10)
                repetidas = df_v.sample(n=num_extras, random_state=42).copy()
                repetidas['SEMANA'] = repetidas['CLUSTER'].apply(
                    lambda x: mapa_semanas[centroids[(centroids.index(x) + 2) % 4]]
                )
                repetidas['REPETIDA'] = True
                df_v.loc[df_v['NOME_LOJA'].isin(repetidas['NOME_LOJA']), 'REPETIDA'] = True
                df_final = pd.concat([df_v, repetidas]).reset_index(drop=True)
            else:
                df_final = df_v

            # 3. OTIMIZAÇÃO TSP
            df_final = df_final.sort_values(by=['SEMANA', 'lat', 'lon']).reset_index(drop=True)
            ordem, tempos, dists = engine.resolver_tsp(df_final)
            
            if ordem:
                res = df_final.iloc[ordem].copy()
                res['SEQUENCIA'] = range(1, len(res) + 1)
                res['TEMPO_DESLOC_MIN'] = [round(t/60, 1) for t in tempos]
                res['DIST_KM'] = [round(d/1000, 1) for d in dists]
                res['LINK_MAPS'] = "https://www.google.com/maps/search/?api=1&query=" + res['lat'].astype(str) + "," + res['lon'].astype(str)
                st.session_state['resultado'] = res

    if 'resultado' in st.session_state:
        res = st.session_state['resultado']
        modo_visao = st.sidebar.radio("Filtrar Mapa:", ["Mês Inteiro", "Semana 1", "Semana 2", "Semana 3", "Semana 4"])
        df_mapa = res if modo_visao == "Mês Inteiro" else res[res['SEMANA'] == modo_visao]

        # KPIs
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Visitas", len(df_mapa))
        c2.metric("Distância", f"{round(df_mapa['DIST_KM'].sum(), 1)} km")
        c3.metric("Tempo Estrada", f"{round(df_mapa['TEMPO_DESLOC_MIN'].sum(), 1)} min")
        c4.metric("Tempo em Loja", f"{(len(df_mapa) * 45) / 60:.1f}h")

        tab1, tab2 = st.tabs(["📋 Roteiro", "🗺️ Mapa"])
        
        with tab1:
            st.dataframe(res[['SEQUENCIA', 'SEMANA', 'NOME_LOJA', 'ENDERECO_COMPLETO', 'REPETIDA', 'LINK_MAPS']], use_container_width=True)

        with tab2:
            m = folium.Map(location=[df_mapa['lat'].mean(), df_mapa['lon'].mean()], zoom_start=11)
            cores = {"Semana 1": "#3498db", "Semana 2": "#2ecc71", "Semana 3": "#f39c12", "Semana 4": "#9b59b6"}
            
            # Mapeamento de semanas para o card
            semanas_por_loja = res.groupby('NOME_LOJA')['SEMANA'].apply(
                lambda x: ", ".join(sorted(set([s.replace("Semana ", "S") for s in x])))
            ).to_dict()

            for _, row in df_mapa.iterrows():
                cor = cores.get(row['SEMANA'], "gray")
                glow = "border: 3px solid #FFD700; box-shadow: 0 0 10px #FFD700;" if row['REPETIDA'] else "border: 2px solid white;"
                
                # Texto formatado para o card
                txt_ciclo = semanas_por_loja[row['NOME_LOJA']]
                label_recorrente = "⭐ RECORRENTE" if row['REPETIDA'] else "Visita Única"
                
                # Criando o conteúdo do card de forma mais segura
                html_card = f"""
                <div style="font-family: Arial; font-size: 12px; min-width: 150px;">
                    <b>{row['NOME_LOJA']}</b><br>
                    Parada: {row['SEQUENCIA']}º<br>
                    Ciclo: {txt_ciclo}<br>
                    <i style="color: gold;">{label_recorrente}</i>
                </div>
                """
                
                folium.Marker(
                    location=[row['lat'], row['lon']],
                    # Tooltip aparece ao passar o mouse
                    tooltip=f"{row['NOME_LOJA']} (Ciclo: {txt_ciclo})",
                    # Popup aparece ao clicar
                    popup=folium.Popup(html_card, max_width=200),
                    icon=folium.DivIcon(html=f"""
                        <div style="background-color:{cor}; color:white; border-radius:50%; width:28px; height:28px; 
                        display:flex; align-items:center; justify-content:center; font-weight:bold; {glow} transform:translate(-14px,-14px);">
                            {int(row['SEQUENCIA'])}
                        </div>""")
                ).add_to(m)
            
            if len(df_mapa) > 1:
                folium.PolyLine(df_mapa[['lat', 'lon']].values.tolist(), color="gray", weight=2, opacity=0.4).add_to(m)
            
            st_folium(m, width="100%", height=600)