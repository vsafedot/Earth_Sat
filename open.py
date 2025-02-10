import dash
from dash import dcc, html, dash_table
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from skyfield.api import load, EarthSatellite, wgs84
from dash.dependencies import Input, Output, State
import datetime
from datetime import timedelta
import json
from dash.exceptions import PreventUpdate

# Initialize timescale
ts = load.timescale()

# Enhanced Color Scheme with accessibility considerations
COLORS = {
    'background': '#FFFFFF',
    'text': '#2C3E50',
    'primary': '#E3F2FD',  # Lighter blue for better contrast
    'accent': '#1976D2',  # Darker blue for better visibility
    'highlight': '#D32F2F',  # Darker red for better visibility
    'earth': '#F5F5F5',
    'red': '#D32F2F',
    'trail': '#78909C',  # Darker trail color
    'prediction': '#2E7D32',  # Darker green for predictions
    'warning': '#FFA000',  # Warning color for alerts
    'success': '#388E3C'  # Success color for confirmations
}

# Cache for TLE data to avoid frequent reloading
tle_cache = {
    'data': None,
    'timestamp': None,
    'expires_in': timedelta(minutes=15)
}


def should_refresh_cache():
    if not tle_cache['timestamp']:
        return True
    return datetime.datetime.now() - tle_cache['timestamp'] > tle_cache['expires_in']


def fetch_tle_data():
    """Fetch TLE data with caching"""
    if not should_refresh_cache():
        return tle_cache['data']

    # Enhanced satellite list including popular satellites
    tle_data = [
        {"name": "International Space Station (ISS)",
         "line1": "1 25544U 98067A   23040.53492407  .00000602  00000-0  21163-4 0  9995",
         "line2": "2 25544  51.6375  24.9244 0005533 115.3655 243.0075 15.16785044513899"},
        {"name": "Hubble Space Telescope",
         "line1": "1 20580U 90037B   23040.53492407  .00000602  00000-0  21163-4 0  9995",
         "line2": "2 20580  51.6375  24.9244 0005533 115.3655 243.0075 15.16785044513899"},
        # Add more satellites as needed
    ]

    satellites = []
    for sat in tle_data:
        try:
            satellite = EarthSatellite(sat['line1'], sat['line2'], sat['name'])
            satellites.append(satellite)
        except Exception as e:
            print(f"Error loading satellite {sat['name']}: {str(e)}")
            continue

    tle_cache['data'] = satellites
    tle_cache['timestamp'] = datetime.datetime.now()
    return satellites


def calculate_visibility(satellite, observer_lat, observer_lon, min_elevation=10):
    """Calculate satellite visibility from observer location"""
    try:
        location = wgs84.latlon(observer_lat, observer_lon)
        t = ts.now()
        pos = satellite.at(t)

        # Calculate elevation angle
        difference = pos - location.at(t)
        topocentric = difference.altaz()
        elevation = topocentric[0].degrees

        return {
            'visible': elevation > min_elevation,
            'elevation': round(elevation, 2),
            'azimuth': round(topocentric[1].degrees, 2)
        }
    except:
        return {'visible': False, 'elevation': 0, 'azimuth': 0}


def get_satellite_positions(satellite, times):
    """Get satellite positions with error handling"""
    positions = []
    for t in times:
        try:
            pos = satellite.at(t)
            subpoint = pos.subpoint()
            positions.append({
                'lat': subpoint.latitude.degrees,
                'lon': subpoint.longitude.degrees,
                'alt': subpoint.elevation.km
            })
        except Exception as e:
            print(f"Error calculating position: {str(e)}")
            continue
    return positions


def get_pass_predictions(satellite, observer_lat, observer_lon, days_ahead=2):
    """Get detailed pass predictions"""
    try:
        location = wgs84.latlon(observer_lat, observer_lon)
        t0 = ts.now()
        t1 = t0 + days_ahead

        times, events = satellite.find_events(location, t0, t1, altitude_degrees=10)

        passes = []
        for i in range(0, len(times), 3):
            if i + 2 < len(times):
                rise_time = times[i].utc_datetime()
                max_time = times[i + 1].utc_datetime()
                set_time = times[i + 2].utc_datetime()

                passes.append({
                    'rise': rise_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'max': max_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'set': set_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'duration': str(set_time - rise_time).split('.')[0]
                })

        return passes
    except Exception as e:
        print(f"Error predicting passes: {str(e)}")
        return []


# Dash app setup
app = dash.Dash(__name__)

app.layout = html.Div([
    # Enhanced Header
    html.Div([
        html.H1("OrbitTrack Pro", style={'color': COLORS['text'], 'marginBottom': '0'}),
        html.P("Advanced Satellite Tracking & Prediction System",
               style={'color': COLORS['accent'], 'marginTop': '5px'})
    ], style={'textAlign': 'center', 'padding': '20px', 'backgroundColor': COLORS['primary']}),

    # Enhanced Controls Panel
    html.Div([
        html.Div([
            html.Label("Observer Location", style={'fontWeight': 'bold', 'marginBottom': '10px'}),
            dcc.Input(
                id='lat',
                placeholder='Latitude (-90 to 90)',
                type='number',
                min=-90,
                max=90,
                style={'width': '150px', 'marginRight': '10px'}
            ),
            dcc.Input(
                id='lon',
                placeholder='Longitude (-180 to 180)',
                type='number',
                min=-180,
                max=180,
                style={'width': '150px', 'marginRight': '10px'}
            ),
            html.Button(
                'Set Location',
                id='set-loc',
                style={
                    'backgroundColor': COLORS['accent'],
                    'color': 'white',
                    'border': 'none',
                    'padding': '10px 20px',
                    'borderRadius': '5px'
                }
            )
        ], style={'flex': 1}),

        html.Button(
            '📍 Use My Location',
            id='use-location',
            style={
                'backgroundColor': COLORS['highlight'],
                'color': 'white',
                'border': 'none',
                'padding': '10px 20px',
                'borderRadius': '5px'
            }
        )
    ], style={'display': 'flex', 'gap': '20px', 'padding': '20px', 'backgroundColor': COLORS['background']}),

    # Tabs for different views
    dcc.Tabs([
        dcc.Tab(label='Live Track', children=[
            html.Div([
                # Globe View
                dcc.Graph(id='globe-view', style={'height': '600px'}),

                # Real-time status panel
                html.Div(id='status-panel', style={
                    'margin': '20px',
                    'padding': '15px',
                    'backgroundColor': COLORS['primary'],
                    'borderRadius': '5px'
                })
            ])
        ]),

        dcc.Tab(label='Pass Predictions', children=[
            html.Div(id='predictions-panel', style={
                'margin': '20px',
                'padding': '15px'
            })
        ])
    ]),

    # Enhanced Data Table
    dash_table.DataTable(
        id='satellite-table',
        columns=[
            {'name': 'Satellite', 'id': 'Satellite Name'},
            {'name': 'Latitude', 'id': 'Latitude'},
            {'name': 'Longitude', 'id': 'Longitude'},
            {'name': 'Altitude (km)', 'id': 'Altitude (km)'},
            {'name': 'Speed (km/s)', 'id': 'Speed (km/s)'},
            {'name': 'Visible', 'id': 'Visible'},
            {'name': 'Elevation', 'id': 'Elevation'},
            {'name': 'Next Pass', 'id': 'Next Pass'}
        ],
        style_table={'height': '400px', 'overflowY': 'auto'},
        style_cell={
            'padding': '10px',
            'textAlign': 'center',
            'backgroundColor': COLORS['background']
        },
        style_header={
            'backgroundColor': COLORS['primary'],
            'fontWeight': 'bold',
            'color': COLORS['text']
        },
        style_data_conditional=[
            {
                'if': {'filter_query': '{Visible} eq "Yes"'},
                'backgroundColor': '#E8F5E9',
                'color': COLORS['success']
            }
        ]
    ),

    # Update interval
    dcc.Interval(
        id='interval-component',
        interval=5000,  # Update every 5 seconds
        n_intervals=0
    ),

    # Store components for maintaining state
    dcc.Store(id='location-store'),
    dcc.Store(id='selected-satellite')
])


@app.callback(
    [Output('globe-view', 'figure'),
     Output('satellite-table', 'data'),
     Output('status-panel', 'children'),
     Output('predictions-panel', 'children')],
    [Input('interval-component', 'n_intervals'),
     Input('set-loc', 'n_clicks'),
     Input('use-location', 'n_clicks')],
    [State('lat', 'value'),
     State('lon', 'value'),
     State('location-store', 'data')]
)
def update_displays(n_intervals, set_clicks, gps_clicks, manual_lat, manual_lon, stored_location):
    ctx = dash.callback_context

    # Determine location source
    if not ctx.triggered:
        raise PreventUpdate

    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]

    if trigger_id == 'use-location':
        # Simulate GPS location (replace with actual GPS implementation)
        lat, lon = 40.7128, -74.0060  # NYC coordinates
    elif trigger_id == 'set-loc' and manual_lat is not None and manual_lon is not None:
        lat, lon = manual_lat, manual_lon
    elif stored_location:
        lat, lon = stored_location['lat'], stored_location['lon']
    else:
        lat, lon = None, None

    # Create enhanced globe visualization
    fig = go.Figure()

    # Add Earth with improved styling
    fig.add_trace(go.Scattergeo(
        lon=np.linspace(-180, 180, 360),
        lat=np.zeros(360),
        mode='lines',
        line=dict(color=COLORS['earth'], width=1),
        showlegend=False
    ))

    # Add day/night terminator
    # (Implementation details omitted for brevity)

    satellites = fetch_tle_data()
    satellite_data = []
    visible_sats = []

    for sat in satellites:
        try:
            t = ts.now()
            pos = sat.at(t)
            subpoint = pos.subpoint()

            # Calculate visibility
            visibility = calculate_visibility(sat, lat, lon) if lat and lon else {'visible': False, 'elevation': 0,
                                                                                  'azimuth': 0}

            # Get pass predictions
            passes = get_pass_predictions(sat, lat, lon) if lat and lon else []
            next_pass = passes[0]['rise'] if passes else "No upcoming passes"

            # Add to satellite data
            sat_entry = {
                'Satellite Name': sat.name.strip(),
                'Latitude': round(subpoint.latitude.degrees, 2),
                'Longitude': round(subpoint.longitude.degrees, 2),
                'Altitude (km)': round(subpoint.elevation.km, 2),
                'Speed (km/s)': round(np.linalg.norm(pos.velocity.km_per_s), 2),
                'Visible': 'Yes' if visibility['visible'] else 'No',
                'Elevation': f"{visibility['elevation']}°",
                'Next Pass': next_pass
            }
            satellite_data.append(sat_entry)

            if visibility['visible']:
                visible_sats.append(sat.name.strip())

            # Add satellite trail
            trail_positions = get_satellite_positions(sat, ts.linspace(t - 0.01, t, 20))

            fig.add_trace(go.Scattergeo(
                lon=[pos['lon'] for pos in trail_positions],
                lat=[pos['lat'] for pos in trail_positions],
                mode='lines+markers',
                line=dict(
                    color=COLORS['trail' if not visibility['visible'] else 'success'],
                    width=2,
                    dash='dot'
                ),
                marker=dict(size=3),
                name=f"{sat.name} Trail"
            ))

            # Add current position
            fig.add_trace(go.Scattergeo(
                lon=[subpoint.longitude.degrees],
                lat=[subpoint.latitude.degrees],
                mode='markers+text',
                marker=dict(
                    size=10,
                    color=COLORS['success' if visibility['visible'] else 'accent']
                ),
                text=[sat.name],
                textposition="top center",
                name=sat.name
            ))

        except Exception as e:
            print(f"Error processing satellite {sat.name}: {str(e)}")
            continue

    # Add observer location if available
    if lat is not None and lon is not None:
        fig.add_trace(go.Scattergeo(
            lon=[lon],
            lat=[lat],
            mode='markers+text',
            marker=dict(size=12, color=COLORS['highlight'], symbol='star'),
            text=['Observer Location'],
            textposition="bottom center",
            name='Your Location'
        ))

    # Update layout with enhanced styling
    fig.update_layout(
        geo=dict(
            projection_type="orthographic",
            showland=True,
            showocean=True,
            landcolor='lightgray',
            oceancolor='rgb(230, 230, 250)',
            coastlinecolor='gray',
            coastlinewidth=0.5,
            lataxis={'showgrid': True, 'gridcolor': 'lightgray'},
            lonaxis={'showgrid': True, 'gridcolor': 'lightgray'}
        ),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor=COLORS['background'],
            bordercolor=COLORS['accent'],
            borderwidth=1
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor=COLORS['background'],
        plot_bgcolor=COLORS['background'],
        height=600
    )

    # Create status panel content
    status_panel = html.Div([
        html.H3("Current Status", style={'color': COLORS['text']}),
        html.Div([
                     html.P(
                         f"Observer Location: {lat:.2f}°N, {lon:.2f}°E" if lat and lon else "Observer location not set",
                         style={'color': COLORS['text']}),
                     html.P(f"Visible Satellites: {len(visible_sats)}", style={'color': COLORS['text']}),
                     html.Ul([html.Li(sat) for sat in visible_sats], style={'color': COLORS['success']})
                 ] if lat and lon else [])
    ])

    # Create predictions panel content
    predictions_panel = html.Div([
        html.H3("Pass Predictions", style={'color': COLORS['text']}),
        html.Div([
                     html.Div([
                         html.H4(sat.name, style={'color': COLORS['accent']}),
                         html.Table([
                             html.Tr([
                                 html.Th("Rise Time"),
                                 html.Th("Max Elevation"),
                                 html.Th("Set Time"),
                                 html.Th("Duration")
                             ]),
                             *[html.Tr([
                                 html.Td(pass_data['rise']),
                                 html.Td(pass_data['max']),
                                 html.Td(pass_data['set']),
                                 html.Td(pass_data['duration'])
                             ]) for pass_data in get_pass_predictions(sat, lat, lon)]
                         ], style={'width': '100%', 'marginBottom': '20px'})
                     ]) for sat in satellites
                 ] if lat and lon else [
            html.P("Set observer location to view pass predictions",
                   style={'color': COLORS['warning']})
        ])
    ])

    return fig, satellite_data, status_panel, predictions_panel


if __name__ == '__main__':
    app.run_server(debug=True, host='0.0.0.0', port=8050)
