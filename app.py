import streamlit as st
import pandas as pd
import requests
import folium
import io
from streamlit_folium import st_folium
from ortools.constraint_solver import routing_enums_pb2, pywrapcp

# Configuração da Página
st.set_page_config(page_title="Roteirizador Logístico", layout="wide")

st.title("🚚 Roteirizador Web - MG")
st.markdown("---")

# --- SIDEBAR: Configurações e Upload ---
uploaded_file = st.sidebar.file_uploader("Subir base_com_coordenadas.xlsx", type=["xlsx"])

if uploaded_file:
    df_raw = pd.read_excel(uploaded_file)
    
    # Filtro de representantes
    reps = df_raw['REPRESENTANTE'].unique()
    rep_sel = st.sidebar.selectbox("Selecione o Representante:", reps)
    
    # Filtrar dados e limpar nulos
    df_v = df_raw[df_raw['REPRESENTANTE'] == rep_sel].copy().reset_index(drop=True)
    df_v = df_v.dropna(subset=['lat', 'lon'])

    if st.sidebar.button("🚀 Calcular Rota Otimizada"):
        # --- Lógica de Geração (Backend) ---
        coords = ";".join([f"{lon},{lat}" for lat, lon in zip(df_v['lat'], df_v['lon'])])
        url = f"http://localhost:5000/table/v1/driving/{coords}?annotations=duration,distance"
        
        try:
            data = requests.get(url).json()
            matrix_time = data['durations']
            matrix_dist = data['distances']

            # OR-Tools: Otimização
            manager = pywrapcp.RoutingIndexManager(len(matrix_time), 1, 0)
            routing = pywrapcp.RoutingModel(manager)
            def cb(f, t): return int(matrix_time[manager.IndexToNode(f)][manager.IndexToNode(t)])
            idx = routing.RegisterTransitCallback(cb)
            routing.SetArcCostEvaluatorOfAllVehicles(idx)
            
            sol = routing.SolveWithParameters(pywrapcp.DefaultRoutingSearchParameters())

            if sol:
                ordem, tempos, dists = [], [0], [0]
                curr = routing.Start(0)
                while not routing.IsEnd(curr):
                    node = manager.IndexToNode(curr)
                    next_var = sol.Value(routing.NextVar(curr))
                    if not routing.IsEnd(next_var):
                        nxt_node = manager.IndexToNode(next_var)
                        tempos.append(matrix_time[node][nxt_node])
                        dists.append(matrix_dist[node][nxt_node])
                    ordem.append(node)
                    curr = next_var
                
                # Criar DataFrame da Rota
                df_rota = df_v.iloc[ordem].copy()
                df_rota['SEQUENCIA'] = range(1, len(df_rota) + 1)
                df_rota['TEMPO_MIN'] = [round(t/60, 1) for t in tempos]
                df_rota['DISTANCIA_KM'] = [round(d/1000, 1) for d in dists]
                # Formato de link amigável
                df_rota['LINK_MAPS'] = "https://www.google.com/maps/search/?api=1&query=" + \
                                       df_rota['lat'].astype(str) + "," + df_rota['lon'].astype(str)
                
                st.session_state['df_rota'] = df_rota
                st.sidebar.success("✅ Rota calculada com sucesso!")

        except Exception as e:
            st.sidebar.error(f"❌ Erro ao conectar no Docker: {e}")

    # --- EXIBIÇÃO DOS RESULTADOS (Visualização Frontend) ---
    if 'df_rota' in st.session_state:
        df_exibir = st.session_state['df_rota']
        
        tab1, tab2 = st.tabs(["📋 Lista de Lojas", "🗺️ Mapa Interativo"])
        
        with tab1:
            st.subheader(f"Roteiro: {rep_sel}")
            
            # Colunas específicas solicitadas
            colunas_visiveis = ['SEQUENCIA', 'NOME_LOJA', 'ENDERECO_COMPLETO', 'LINK_MAPS', 'TEMPO_MIN', 'DISTANCIA_KM']
            
            # Configuração da tabela clicável e formatada
            st.dataframe(
                df_exibir[colunas_visiveis],
                column_config={
                    "LINK_MAPS": st.column_config.LinkColumn("Abrir no GPS", display_text="Ver no Mapa 📍"),
                    "SEQUENCIA": st.column_config.NumberColumn("Ordem", format="%d"),
                    "TEMPO_MIN": st.column_config.NumberColumn("Tempo (min)", format="%.1f ⏳"),
                    "DISTANCIA_KM": st.column_config.NumberColumn("Km", format="%.1f 🛣️"),
                },
                hide_index=True,
                use_container_width=True
            )

            # --- BOTÃO DE DOWNLOAD (Excel para WhatsApp) ---
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_exibir[colunas_visiveis].to_excel(writer, index=False, sheet_name='Rota')
            
            st.download_button(
                label="📥 Baixar Rota para WhatsApp (Excel)",
                data=buffer.getvalue(),
                file_name=f"Rota_{rep_sel}.xlsx",
                mime="application/vnd.ms-excel"
            )

        with tab2:
            st.subheader("Visualização do Percurso")
            # Centralizar o mapa na primeira loja
            m = folium.Map(location=[df_exibir.iloc[0]['lat'], df_exibir.iloc[0]['lon']], zoom_start=12)
            
            pontos = []
            for _, row in df_exibir.iterrows():
                pos = [row['lat'], row['lon']]
                pontos.append(pos)
                folium.Marker(
                    pos, 
                    tooltip=f"{row['SEQUENCIA']}°: {row['NOME_LOJA']}",
                    icon=folium.Icon(color="blue", icon="info-sign")
                ).add_to(m)
            
            folium.PolyLine(pontos, color="red", weight=3, opacity=0.8).add_to(m)
            st_folium(m, width=1200, height=600)
else:
    st.info("👋 Bem-vindo! Por favor, faça o upload da sua planilha na barra lateral para começar.")