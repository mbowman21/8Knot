from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
import warnings

from .visualizations.bus_factor import gc_bus_factor_pie
from .visualizations.time_to_first_response import gc_time_to_first_response
from .visualizations.release_frequency import gc_release_frequency_chart
from .visualizations.change_request_closure_ratio import gc_change_request_closure_ratio

# import visualization cards

warnings.filterwarnings("ignore")

dash.register_page(__name__, path="/project_starter_health")

layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(gc_bus_factor_pie, width=6),
                dbc.Col(gc_time_to_first_response, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_release_frequency_chart, width=6),
                dbc.Col(gc_change_request_closure_ratio, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
    ],
    fluid=True,
)