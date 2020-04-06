import io
import requests
import pandas as pd
from datetime import datetime
import plotly.graph_objs as go
import plotly.offline as pyo
from plotly import subplots
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output


app = dash.Dash()

server = app.server 

url_confirmed = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_confirmed_global.csv'
url_deaths = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_deaths_global.csv'
url_recovered = 'https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_recovered_global.csv'

urls = [url_confirmed, url_deaths, url_recovered]
series = ['confirmed', 'deaths', 'recovered']
ids = ['Province/State', 'Country/Region', 'Lat', 'Long']

for url, serie in zip(urls, series):
    r = requests.get(url).content
    df = pd.read_csv(io.StringIO(r.decode('utf-8')))
    df = df.melt(id_vars=ids)
    df.rename(columns={'variable': 'date', 'value': serie}, inplace=True)
    df.loc[:, 'date'] = df['date'].apply(
        lambda x: datetime.strptime(x, '%m/%d/%y'))
    df.to_csv(f'{serie}.csv', index=False)



# get active by state/province
def active_state(state):
    confirmed = pd.read_csv('confirmed.csv')
    deaths = pd.read_csv('deaths.csv')
    recovered = pd.read_csv('recovered.csv')
    confirmed_region = confirmed[confirmed['Province/State'] == state]
    deaths_region = deaths[deaths['Province/State'] == state]
    recovered_region = recovered[recovered['Province/State'] == state]
    active_region = confirmed_region.set_index('date')
    recovered_region.set_index('date', inplace=True)
    deaths_region.set_index('date', inplace=True)
    active_region = active_region.join(recovered_region.loc[:, ['recovered']])
    active_region = active_region.join(deaths_region.loc[:, ['deaths']])
    active_region.loc[:, 'active'] = active_region['confirmed'] - \
        active_region['recovered'] - active_region['deaths']
    active_region.loc[:, 'confirmed_pd'] = active_region['confirmed'].shift(1)
    active_region.loc[:, 'new_cases'] = active_region['confirmed'] - \
        active_region['confirmed_pd']
    active_region.loc[:, 'growth'] = active_region['confirmed'] / \
        active_region['confirmed_pd']
    active_region.loc[:, 'new_cases_pd'] = active_region['new_cases'].shift(1)
    active_region.loc[:, 'growth_factor'] = active_region['new_cases'] / \
        active_region['new_cases_pd']
    active_region.loc[:, 'death_rate'] = active_region['deaths'] / \
        (active_region['recovered']+active_region['deaths'])
    active_region.loc[:, 'recovery_rate'] = active_region['recovered'] / \
        (active_region['recovered']+active_region['deaths'])
    return active_region


def plot_report(state='South Australia'):
    df = active_state(state)

    df = df[df['confirmed'] > 10]
    x = df.index.values
    cases = df['confirmed']
    active = df['active']
    recovered = df['recovered']
    deaths = df['deaths']
    recoveryrate = df['recovery_rate']

    fig = subplots.make_subplots(rows=2, cols=1,
                                subplot_titles=(
                                    'Active and Confirmed Cases', 'Recovered Cases and Deaths'),
                                shared_xaxes=True,  
                                specs=[[{"secondary_y": False}],
                                        [{"secondary_y": True}]
                                        ]
                                )


    # top chart
    # add active cases

    fig.add_trace(
        go.Scatter(
            x=x,
            y=active,
            mode='lines',
            name='active cases'
        ), row=1, col=1, secondary_y=False
    )

    # add confirmed cases
    fig.add_trace(
        go.Scatter(
            x=x,
            y=cases,
            mode='lines',
            name='confirmed cases'
        ), row=1, col=1, secondary_y=False
    )


    # bottom chart
    # add recovered cases
    fig.add_trace(
        go.Bar(
            x=x,
            y=recovered,
            name='Recovered cases'
        ), row=2, col=1, secondary_y=False
    )

    # add deaths

    fig.add_trace(
        go.Bar(
            x=x,
            y=deaths,
            name='Deaths'
        ), row=2, col=1, secondary_y=False
    )

    # add recovery rate secondary Y axis

    fig.add_trace(
        go.Scatter(
            x=x,
            y=recoveryrate,
            mode = 'lines',
            name='recovery rate'

        ), row=2, col=1, secondary_y=True
    )

    fig.update_yaxes(range=[0, 1.1], row=2, col=1,
                     secondary_y=True)

    fig.update_layout(
        title_text=f"COVID-19 Situation Status Report for {state} ",
        width=900,
        height=650
        ,
    )


    return fig



state_data = pd.read_csv('confirmed.csv')
state_data = state_data[state_data['Country/Region'] == "Australia"]
 

states_options = []
for state in state_data['Province/State'].unique():
    states_options.append({'label': state, 'value': state})


app.layout = html.Div([
    html.H2(children='How each Australian State are winning Covid-19',
            style={'text-align': 'center'})

    , html.Div([
        dcc.Graph(id='graph1')]
    )
    , html.Div([dcc.Dropdown(id='state-picker', options=states_options,
                 value='South Australia')]
               , style={'width': '60%'}
    )
]
    
    )

@app.callback(Output('graph1', 'figure'),
              [Input('state-picker', 'value')])
def update_figure(selected_state):
    fig = plot_report(selected_state)
    return fig
    


if __name__ == '__main__':
    app.run_server()


