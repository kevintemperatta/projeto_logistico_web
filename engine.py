from ortools.constraint_solver import routing_enums_pb2, pywrapcp
import pandas as pd
import numpy as np

class RoteirizadorEngine:
    def __init__(self, docker_url=None):
        # Não precisamos mais de URL externa, o cálculo será local
        pass

    def calcular_haversine(self, lat1, lon1, lat2, lon2):
        # Calcula a distância real entre dois pontos na Terra (em metros)
        R = 6371000  # Raio da Terra em metros
        phi1, phi2 = np.radians(lat1), np.radians(lat2)
        dphi = np.radians(lat2 - lat1)
        dlambda = np.radians(lon2 - lon1)
        a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
        return 2 * R * np.arctan2(np.sqrt(a), np.sqrt(1-a))

    def obter_matrizes(self, df):
        n = len(df)
        matrix_dist = np.zeros((n, n))
        matrix_time = np.zeros((n, n))
        
        for i in range(n):
            for j in range(n):
                if i == j:
                    matrix_dist[i][j] = 0
                    matrix_time[i][j] = 0
                else:
                    dist = self.calcular_haversine(
                        df.iloc[i]['lat'], df.iloc[i]['lon'],
                        df.iloc[j]['lat'], df.iloc[j]['lon']
                    )
                    # Adicionamos um fator de 1.3 (30%) para simular as curvas das ruas
                    dist_estimada = dist * 1.3 
                    matrix_dist[i][j] = int(dist_estimada)
                    # Tempo estimado: Distância / 11 m/s (aprox 40km/h urbano)
                    matrix_time[i][j] = int(dist_estimada / 11)
        
        return matrix_time.tolist(), matrix_dist.tolist()

    def resolver_tsp(self, df):
        # Agora o processo é 100% offline e seguro
        matrix_time, matrix_dist = self.obter_matrizes(df)
        
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