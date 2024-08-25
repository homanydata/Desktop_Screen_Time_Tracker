import dash
from dash import dcc, html
import pandas as pd
from summarizer import get_daily_usage, get_unique_days, get_usage_by_apps
import plotly.express as px
from dash.dependencies import Input, Output

# Initialize the Dash app
app = dash.Dash(__name__)

# Load the initial data
df = get_daily_usage()
df['date'] = pd.to_datetime(df['date'])
unique_days = get_unique_days()

# Function to aggregate data and format the date column
def aggregate_data(df, level):
    if level == 'Daily':
        df['formatted_date'] = df['date'].dt.strftime('%Y-%m-%d')
    elif level == 'Monthly':
        df = df.resample('M', on='date').sum().reset_index()
        df['formatted_date'] = df['date'].dt.strftime('%Y-%m')
    elif level == 'Yearly':
        df = df.resample('Y', on='date').sum().reset_index()
        df['formatted_date'] = df['date'].dt.strftime('%Y')
    return df

# Define the layout of the app
app.layout = html.Div(children=[
    html.H1(children='Screen Time Tracker'),

    html.Div(children='''
        A simple Dash app to track screen time usage at different levels.
    '''),

    # Aggregation level selection
    dcc.RadioItems(
        id='aggregation-level',
        options=[
            {'label': 'Daily', 'value': 'Daily'},
            {'label': 'Monthly', 'value': 'Monthly'},
            {'label': 'Yearly', 'value': 'Yearly'}
        ],
        value='Daily',
        labelStyle={'display': 'inline-block'}
    ),

    # Main usage graph
    dcc.Graph(
        id='Daily Usage Graph',
        config={
            'scrollZoom': True,
            'displayModeBar': True,
            'displaylogo': False,
            'modeBarButtonsToRemove': [
                'pan2d', 'select2d', 'lasso2d', 'zoomIn2d', 'zoomOut2d',
                'autoScale2d', 'resetScale2d', 'hoverClosestCartesian',
                'hoverCompareCartesian', 'toggleSpikelines'
            ],
            'modeBarButtonsToAdd': ['toImage']
        }
    ),

    # Dropdown for selecting a specific day
    html.H2('Select a Day to View App Usage'),
    dcc.Dropdown(
        id='day-selection',
        options=[{'label': day, 'value': day} for day in unique_days],
        placeholder='Select a day',
    ),

    # Graph to display app usage for selected day
    dcc.Graph(id='App Usage Graph')
])

# Callback to update the main usage graph based on the selected aggregation level
@app.callback(
    Output('Daily Usage Graph', 'figure'),
    [Input('aggregation-level', 'value')]
)
def update_graph(selected_level):
    aggregated_df = aggregate_data(df, selected_level)
    fig = px.bar(aggregated_df, x='formatted_date', y='usage', title=f'{selected_level} Screen Time Usage')
    return fig

# Callback to update the app usage graph based on the selected day
@app.callback(
    Output('App Usage Graph', 'figure'),
    [Input('day-selection', 'value')]
)
def update_app_usage(selected_day):
    if selected_day is None:
        return {}  # Return an empty figure if no day is selected

    app_usage_df = get_usage_by_apps(selected_day)
    app_usage_df = app_usage_df.sort_values(by='usage', ascending=False)  # Sort by usage in descending order
    fig = px.bar(app_usage_df, y='app_name', x='usage', orientation='h', title=f'App Usage on {selected_day}')
    return fig

# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)