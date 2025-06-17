import dash
from dash import dcc, html
from dash.dependencies import Input, Output, State
import plotly.graph_objs as go
import requests
from datetime import datetime
import pytz

IP_ADDRESS = "20.55.28.240"
PORT_STH = 8666
DASH_HOST = "localhost"

def get_data(attr, lastN):
    url = f"http://{IP_ADDRESS}:{PORT_STH}/STH/v1/contextEntities/type/Sensor/id/urn:ngsi-ld:bpm:032/attributes/{attr}?lastN={lastN}"
    headers = {'fiware-service': 'smart', 'fiware-servicepath': '/'}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        try:
            return response.json()['contextResponses'][0]['contextElement']['attributes'][0]['values']
        except (KeyError, IndexError):
            return []
    return []

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
    html.Div(id='alerta-bpm', style={'display': 'none'}),

    dcc.Graph(id='graph-temp'),
    html.Div(id='alerta-temp', style={'display': 'none'}),

    dcc.Store(id='data-store', data={
        'timestamps': [],
        'bpm': [],
        'temperatureC': []
    }),
    dcc.Interval(id='interval', interval=2 * 1000, n_intervals=0)
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
    Output('alerta-bpm', 'children'),
    Output('alerta-bpm', 'style'),
    Output('alerta-temp', 'children'),
    Output('alerta-temp', 'style'),
    Input('data-store', 'data')
)
def update_graphs(data):
    def create_graph(y_data, title, color, ylabel):
        if not data['timestamps'] or not y_data:
            return go.Figure()

        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=data['timestamps'],
            y=y_data,
            mode='lines+markers',
            name=title,
            line=dict(color=color)
        ))

        fig.update_layout(
            title=f'{title} ({y_data[-1]} {ylabel})',
            xaxis_title='Tempo',
            yaxis_title=ylabel,
            hovermode='closest'
        )
        return fig

    alerta_bpm_texto = ""
    alerta_temp_texto = ""
    alerta_bpm_style = {'display': 'none'}
    alerta_temp_style = {'display': 'none'}

    if data['bpm'] and data['temperatureC']:
        bpm = data['bpm'][-1]
        temp = data['temperatureC'][-1]
        ##################################################################################
        if bpm == 0:
            alerta_bpm_texto = f"COLOQUE O DEDO ☝️"
        elif bpm < 60: 
            alerta_bpm_texto = f"⚠️ BPM BAIXO"
        elif bpm > 100:
            alerta_bpm_texto = f"⚠️ BPM ALTO"
        
        if temp == 0:
            alerta_temp_texto = f"COLOQUE O DEDO ☝️"
        elif temp < 35:
            alerta_temp_texto = f"⚠️ TEMPERATURA BAIXA"
        elif temp > 38:
            alerta_temp_texto = f"⚠️ TEMPERATURA ALTA"
        
        if alerta_bpm_texto:
            alerta_bpm_style = {
                'color': 'white',
                'backgroundColor': 'lightcoral',
                'padding': '10px',
                'margin': '10px 20px',
                'textAlign': 'center',
                'fontWeight': 'bold',
                'display': 'block',
                'borderRadius': '15px'
            }
        
        if alerta_temp_texto:
            alerta_temp_style = {
                'color': 'white',
                'backgroundColor': 'lightcoral',
                'padding': '10px',
                'margin': '10px 20px',
                'textAlign': 'center',
                'fontWeight': 'bold',
                'display': 'block',
                'borderRadius': '15px'
            }

    return (
        create_graph(data['bpm'], 'BPM 💓', 'red', 'BPM'),
        create_graph(data['temperatureC'], 'Temperatura (C)', 'orange', '°C'),
        alerta_bpm_texto,
        alerta_bpm_style,
        alerta_temp_texto,
        alerta_temp_style
    )

if __name__ == '__main__':
    app.run(debug=True, host=DASH_HOST, port=8050)
