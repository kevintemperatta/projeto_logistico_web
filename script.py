import pandas as pd
import requests
import os
from ortools.constraint_solver import routing_enums_pb2, pywrapcp

# 1. Configurações de Pastas
ARQUIVO_ENTRADA = "base_com_coordenadas.xlsx"
PASTA_SAIDA = "C:/logistica/Rotas_Finais_Oficiais"

if not os.path.exists(PASTA_SAIDA):
    os.makedirs(PASTA_SAIDA)

# 2. Carregar e Validar (SIM/NÃO)
df = pd.read_excel(ARQUIVO_ENTRADA)

# Criar coluna de status para conferência
df['OK_PARA_ROTA'] = df.apply(lambda r: "SIM" if pd.notna(r.get('lat')) and pd.notna(r.get('lon')) else "NÃO", axis=1)

# Filtrar apenas o que está OK para processar no Docker
df_ready = df[df['OK_PARA_ROTA'] == "SIM"].copy()

print(f"Total: {len(df)} | Prontos: {len(df_ready)} | Erros: {len(df) - len(df_ready)}")

# 3. Processar Roteirização
for representante in df_ready['REPRESENTANTE'].unique():
    df_r = df_ready[df_ready['REPRESENTANTE'] == representante].copy().reset_index(drop=True)
    
    if len(df_r) < 2: continue
        
    # Chamada ao seu Docker Local
    coords = ";".join([f"{lon},{lat}" for lat, lon in zip(df_r['lat'], df_r['lon'])])
    url = f"http://localhost:5000/table/v1/driving/{coords}?annotations=duration,distance"
    
    try:
        data = requests.get(url).json()
        matrix_time = data['durations']
        matrix_dist = data['distances']
        
        # Otimização OR-Tools
        manager = pywrapcp.RoutingIndexManager(len(matrix_time), 1, 0)
        routing = pywrapcp.RoutingModel(manager)
        def cb(f, t): return int(matrix_time[manager.IndexToNode(f)][manager.IndexToNode(t)])
        idx = routing.RegisterTransitCallback(cb)
        routing.SetArcCostEvaluatorOfAllVehicles(idx)
        
        sol = routing.SolveWithParameters(pywrapcp.DefaultRoutingSearchParameters())

        if sol:
            ordem = []
            curr = routing.Start(0)
            while not routing.IsEnd(curr):
                ordem.append(manager.IndexToNode(curr))
                curr = sol.Value(routing.NextVar(curr))
            
            # Criar DataFrame da Rota
            df_rota = df_r.iloc[ordem].copy()
            
            # Inserir Sequência e LINK DE GPS
            df_rota.insert(0, 'SEQUENCIA', range(1, len(df_rota) + 1))
            
            # LINK DE GPS (Fórmula que abre direto no mapa)
            df_rota['LINK_MAPS'] = "https://www.google.com/maps/search/?api=1&query=" + \
                                   df_rota['lat'].astype(str) + "," + \
                                   df_rota['lon'].astype(str)
            
            # Salvar arquivo ÚNICO por representante
            nome_limpo = str(representante).replace(' ', '_').replace('/', '-')
            df_rota.to_excel(f"{PASTA_SAIDA}/Rota_{nome_limpo}.xlsx", index=False)
            print(f"✅ Arquivo gerado: Rota_{nome_limpo}.xlsx")

    except Exception as e:
        print(f"❌ Erro ao processar {representante}: {e}")

print("\n🚀 Processo finalizado! Confira a pasta Rotas_Finais_Oficiais.")