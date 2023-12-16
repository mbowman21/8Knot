from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
import warnings

from .visualizations.issues_closed import gc_issues_closed
from .visualizations.issues_updated import gc_issues_updated
from .visualizations.contributors import gc_contributors
from .visualizations.change_requests_accepted import gc_change_requests_accepted
from .visualizations.committers import gc_committers

# import visualization cards

warnings.filterwarnings("ignore")

dash.register_page(__name__, path="/project_engagement")

layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(gc_issues_closed, width=6),
                dbc.Col(gc_issues_updated, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_contributors, width=6),
                dbc.Col(gc_change_requests_accepted, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
        dbc.Row(
            [
                dbc.Col(gc_committers, width=6),
            ],
            align="center",
            style={"marginBottom": ".5%"},
        ),
    ],
    fluid=True,
)