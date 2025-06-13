import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import requests
from datetime import datetime
import pytz

# Constantes para IP e porta
IP_ADDRESS = "20.55.28.240"
PORT_STH = 8666
DASH_HOST = "localhost"  # Use "0.0.0.0" para acesso externo

# Função genérica para buscar dados de bpm ou temperatureC
def get_data(attr, lastN):
    url = f"http://{IP_ADDRESS}:{PORT_STH}/STH/v1/contextEntities/type/Sensor/id/urn:ngsi-ld:bpm:032/attributes/{attr}?lastN={lastN}"
    headers = {
        'fiware-service': 'smart',
        'fiware-servicepath': '/'
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        data = response.json()
        try:
            values = data['contextResponses'][0]['contextElement']['attributes'][0]['values']
            return values
        except (KeyError, IndexError) as e:
            print(f"Erro ao acessar os dados do atributo {attr}: {e}")
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

# Inicializa o app Dash
app = dash.Dash(__name__)

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
    dcc.Graph(id='graph-temp'),
    dcc.Store(id='data-store', data={
        'timestamps': [],
        'bpm': [],
        'temperatureC': []
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
    lastN = 30
    bpm_data = get_data('bpm', lastN)
    temp_data = get_data('temperatureC', lastN)

    if bpm_data and temp_data:
        timestamps = [entry['recvTime'] for entry in bpm_data]
        timestamps = convert_to_brasilia_time(timestamps)

        stored_data['timestamps'] = timestamps
        stored_data['bpm'] = [float(entry['attrValue']) for entry in bpm_data]
        stored_data['temperatureC'] = [float(entry['attrValue']) for entry in temp_data]

    return stored_data

@app.callback(
    Output('graph-bpm', 'figure'),
    Output('graph-temp', 'figure'),
    Input('data-store', 'data')
)
def update_graphs(data):
    def create_graph(y_data, title, color, ylabel):
        if not data['timestamps'] or not y_data:
            return go.Figure()

        latest_value = y_data[-1] if y_data else 0
        title_with_value = f'{title} ({latest_value} {ylabel})'

        mean_value = sum(y_data) / len(y_data)
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data['timestamps'],
            y=y_data,
            mode='lines+markers',
            name=title,
            line=dict(color=color)
        ))
        fig.add_trace(go.Scatter(
            x=[data['timestamps'][0], data['timestamps'][-1]],
            y=[mean_value, mean_value],
            mode='lines',
            name='Média',
            line=dict(color='blue', dash='dash')
        ))

        fig.update_layout(
            title=title_with_value,
            xaxis_title='Tempo',
            yaxis_title=ylabel,
            hovermode='closest'
        )
        return fig

    return (
        create_graph(data['bpm'], 'BPM 💓', 'red', 'BPM'),
        create_graph(data['temperatureC'], 'Temperatura (C)', 'orange', '°C')
    )

if __name__ == '__main__':
    app.run(debug=True, host=DASH_HOST, port=8050)
