import requests
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
import pandas as pd
import numpy as np

class RoteirizadorEngine:
    def __init__(self, docker_url="http://router.project-osrm.org"):
        # Alterado para o servidor público do OSRM para funcionar na nuvem
        self.docker_url = docker_url

    def obter_matrizes(self, df):
        coords = ";".join([f"{lon},{lat}" for lat, lon in zip(df['lat'], df['lon'])])
        url = f"{self.docker_url}/table/v1/driving/{coords}?annotations=duration,distance"
        
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data['durations'], data['distances']
        except Exception as e:
            # PLANO B: Se o servidor de mapas falhar, calcula por distância euclidiana (linha reta)
            # Isso evita que o app trave completamente
            n = len(df)
            matrix_dist = np.zeros((n, n))
            matrix_time = np.zeros((n, n))
            
            for i in range(n):
                for j in range(n):
                    # Cálculo de distância aproximada em metros
                    d = np.sqrt((df.iloc[i]['lat'] - df.iloc[j]['lat'])**2 + 
                                (df.iloc[i]['lon'] - df.iloc[j]['lon'])**2) * 111320
                    matrix_dist[i][j] = int(d)
                    matrix_time[i][j] = int(d / 13) # Estimativa de 46 km/h (13 m/s)
            return matrix_time.tolist(), matrix_dist.tolist()

    def resolver_tsp(self, df):
        matrix_time, matrix_dist = self.obter_matrizes(df)
        
        if not matrix_time:
            return None, None, None

        manager = pywrapcp.RoutingIndexManager(len(matrix_time), 1, 0)
        routing = pywrapcp.RoutingModel(manager)

        def transit_cb(f, t):
            return int(matrix_time[manager.IndexToNode(f)][manager.IndexToNode(t)])
        
        transit_id = routing.RegisterTransitCallback(transit_cb)
        routing.SetArcCostEvaluatorOfAllVehicles(transit_id)
        
        params = pywrapcp.DefaultRoutingSearchParameters()
        params.first_solution_strategy = routing_enums_pb2.FirstSolutionStrategy.PATH_CHEAPEST_ARC
        
        solution = routing.SolveWithParameters(params)
        
        if solution:
            ordem, tempos, dists = [], [0], [0]
            curr = routing.Start(0)
            while not routing.IsEnd(curr):
                node = manager.IndexToNode(curr)
                next_var = solution.Value(routing.NextVar(curr))
                if not routing.IsEnd(next_var):
                    nxt_node = manager.IndexToNode(next_var)
                    tempos.append(matrix_time[node][nxt_node])
                    dists.append(matrix_dist[node][nxt_node])
                ordem.append(node)
                curr = next_var
            return ordem, tempos, dists
        return None, None, None