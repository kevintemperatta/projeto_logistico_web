import requests
from ortools.constraint_solver import routing_enums_pb2, pywrapcp
import pandas as pd

class RoteirizadorEngine:
    def __init__(self, docker_url="http://localhost:5000"):
        self.docker_url = docker_url

    def obter_matrizes(self, df):
        coords = ";".join([f"{lon},{lat}" for lat, lon in zip(df['lat'], df['lon'])])
        url = f"{self.docker_url}/table/v1/driving/{coords}?annotations=duration,distance"
        response = requests.get(url).json()
        return response['durations'], response['distances']

    def resolver_tsp(self, df):
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