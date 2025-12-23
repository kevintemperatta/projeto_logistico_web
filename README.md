# 🚚 Roteirizador Logístico Inteligente (Minas Gerais)

![Status do Projeto](https://img.shields.io/badge/Status-Em%20constante%20evolu%C3%A7%C3%A3o-orange?style=for-the-badge&logo=git)
![Tecnologias](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)

Esta aplicação é uma solução de engenharia logística que automatiza a roteirização de centenas de pontos de venda. Utiliza infraestrutura **Docker** para geoprocessamento e algoritmos de **IA de busca** para otimização de trajetos.



## 🌟 Diferenciais da Solução
- **Malha Rodoviária Real:** Diferente de cálculos por raio (linha reta), o sistema utiliza o motor OSRM para considerar ruas, sentidos e estradas reais.
- **Otimização de Sequência:** Resolve o Problema do Caixeiro Viajante (TSP) via Google OR-Tools, minimizando o tempo total de deslocamento.
- **Dashboard Web Interativo:** Interface amigável para upload de planilhas e visualização de rotas em tempo real.
- **Mobilidade:** Geração de links clicáveis que integram a planilha de saída diretamente ao GPS do smartphone do condutor.

## 🛠️ Arquitetura Técnica
A solução é dividida em três camadas de serviço:
1. **Camada de Dados:** Processamento de planilhas Excel e validação de coordenadas.
2. **Camada de Inteligência:** Container Docker rodando **OSRM** (porta 5000) para matrizes de distância e **OR-Tools** para roteirização.
3. **Camada de Apresentação:** Interface Web desenvolvida em **Streamlit** com visualização de mapas via **Folium**.



## 🚀 Como Executar o Projeto

### 1. Requisitos do Sistema
- Docker & Docker Compose.
- Python 3.10 ou superior.

### 2. Configurar o Motor de Roteirização (OSRM)
Certifique-se de que o container com o mapa de Minas Gerais está ativo:
```bash
docker run -t -i -p 5000:5000 -v "${PWD}:/data" osrm/osrm-backend osrm-routed --algorithm mld /data/minas-gerais-latest.osrm

# Instalar bibliotecas necessárias
pip install -r requirements.txt

# Iniciar o Dashboard
streamlit run app.py
