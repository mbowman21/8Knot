from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
import warnings

# import visualization cards

warnings.filterwarnings("ignore")

dash.register_page(__name__, path="/project_engagement")

layout = dbc.Container(
    [
        dbc.Row(
            [

            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),

    ],
    fluid=True,
)