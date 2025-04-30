import dash
from dash import dcc, html

from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import requests
from datetime import datetime
import pytz

# Constants for IP and port
IP_ADDRESS = "20.55.28.240"
PORT_STH = 8666
DASH_HOST = "localhost"  # Use "0.0.0.0" para acesso externo

# Função genérica para buscar dados de bpm ou spo2
def get_data(attr, lastN):
    url = f"http://{IP_ADDRESS}:{PORT_STH}/STH/v1/contextEntities/type/Sensor/id/urn:ngsi-ld:bpm:030/attributes/{attr}?lastN={lastN}"
    headers = {
        'fiware-service': 'smart',
        'fiware-servicepath': '/'
    }
    response = requests.get(url, headers=headers)
    
    #print(f"URL: {url}")
    #print(f"Status: {response.status_code}")
    #print(f"Resposta da API: {response.text}")
    
    if response.status_code == 200:
        data = response.json()
        try:
            values = data['contextResponses'][0]['contextElement']['attributes'][0]['values']
            return values
        except KeyError as e:
            print(f"Key error: {e}")
            return []
    else:
        print(f"Erro ao acessar {url}: {response.status_code}")
        return []

# Converte UTC para horário de Brasília
def convert_to_brasilia_time(timestamps):
    utc = pytz.utc
    brasilia = pytz.timezone('America/Sao_Paulo')
    converted = []
    for t in timestamps:
        t = t.replace('T', ' ').replace('Z', '')
        try:
            dt = datetime.strptime(t, '%Y-%m-%d %H:%M:%S.%f')
        except ValueError:
            dt = datetime.strptime(t, '%Y-%m-%d %H:%M:%S')
        converted.append(utc.localize(dt).astimezone(brasilia))
    return converted

# Inicializa o app
app = app = dash.Dash(__name__)


app.layout = html.Div([
    html.H1(
        'Painel de Monitoramento de Saúde - Hospital Sabará',
        style={
            'font-family': 'Arial, sans-serif',
            'color': 'lightblue',
            'text-shadow': '1px 1px 2px black',
            'text-align': 'center',
            'margin-top': '40px',
        }
    ),
    dcc.Graph(id='graph-bpm'),
    dcc.Graph(id='graph-spo2'),
    dcc.Store(id='data-store', data={
        'timestamps': [],
        'bpm': [],
        'spo2': []
    }),
    dcc.Interval(
        id='interval',
        interval=2 * 1000,  # 2 segundos
        n_intervals=0
    )
])

@app.callback(
    Output('data-store', 'data'),
    Input('interval', 'n_intervals'),
    State('data-store', 'data')
)
def update_data(n, stored_data):
    lastN = 20
    bpm_data = get_data('bpm', lastN)
    spo2_data = get_data('spo2', lastN)

    if bpm_data and spo2_data:
        timestamps = [entry['recvTime'] for entry in bpm_data]
        timestamps = convert_to_brasilia_time(timestamps)

        stored_data['timestamps'] = timestamps
        stored_data['bpm'] = [float(entry['attrValue']) for entry in bpm_data]
        stored_data['spo2'] = [float(entry['attrValue']) for entry in spo2_data]

    return stored_data

@app.callback(
    Output('graph-bpm', 'figure'),
    Output('graph-spo2', 'figure'),
    Input('data-store', 'data')
)


def update_graphs(data):
    def create_graph(y_data, title, color, ylabel):
        if not data['timestamps'] or not y_data:
            return go.Figure()
        
        # Pega o último valor para exibir no título
        latest_value = y_data[-1] if y_data else 0
        title_with_value = f'{title} ({latest_value} {ylabel})'

        mean_value = sum(y_data) / len(y_data)
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data['timestamps'], y=y_data, mode='lines+markers', name=title, line=dict(color=color)))
        fig.add_trace(go.Scatter(x=[data['timestamps'][0], data['timestamps'][-1]],
                                 y=[mean_value, mean_value], mode='lines', name='Média', line=dict(color='blue', dash='dash')))
        
        # Ajustando o intervalo do eixo Y para 0 a 100
        fig.update_layout(
            title=title_with_value,  # Atualiza o título com o valor atual
            xaxis_title='Tempo', 
            yaxis_title=ylabel,
            yaxis=dict(range=[0, 100]),  # Definindo o intervalo fixo de 0 a 100
            hovermode='closest'
        )
        
        return fig

    return (
        create_graph(data['bpm'], 'BPM 💓', 'red', 'BPM'),
        create_graph(data['spo2'], 'SpO2 🩺', 'green', '%')
    )

if __name__ == '__main__':
    app.run(debug=True, host=DASH_HOST, port=8050)
