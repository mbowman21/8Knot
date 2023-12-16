from dash import html, dcc, callback
import dash
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import logging
from dateutil.relativedelta import *  # type: ignore
import plotly.express as px
from pages.utils.graph_utils import get_graph_time_values, color_seq
from queries.contributors_query import contributors_query as ctq
import io
from cache_manager.cache_manager import CacheManager as cm
from pages.utils.job_utils import nodata_graph
import time
import app


PAGE = "project_engagement"
VIZ_ID = "committers"

gc_committers = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Committers",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """Visualizes the number of individuals who have committed code to a project. \n
                             This is different from contributors because these individuals have commits \n
                              merged into the project. """
                        ),
                    ],
                    id=f"popover-{PAGE}-{VIZ_ID}",
                    target=f"popover-target-{PAGE}-{VIZ_ID}",
                    placement="top",
                    is_open=False,
                ),
                dcc.Loading(
                    dcc.Graph(id=f"{PAGE}-{VIZ_ID}"),
                ),
                dbc.Form(
                    [
                        dbc.Row(
                            [
                                dbc.Label(
                                    "",
                                    html_for=f"action-dropdown-{PAGE}-{VIZ_ID}",
                                    width="auto",
                                ),
                                dbc.Col(
                                    [
                                        html.Div([
                                            dcc.Dropdown(
                                                id=f"action-dropdown-{PAGE}-{VIZ_ID}",
                                                value="Commit",
                                                clearable=False,
                                            )
                                            ], style= {'display': 'none'}
                                        ),
                                        

                                        dbc.Alert(
                                            children="""No contributions of this type have been made.\n
                                            Please select a different contribution type.""",
                                            id=f"check-alert-{PAGE}-{VIZ_ID}",
                                            dismissable=True,
                                            fade=False,
                                            is_open=False,
                                            color="warning",
                                        ),
                                    ],
                                    className="me-2",
                                    width=3,
                                ),
                            ],
                            align="center",
                        ),
                        dbc.Row(
                            [
                                dbc.Label(
                                    "Date Interval:",
                                    html_for=f"date-interval-{PAGE}-{VIZ_ID}",
                                    width="auto",
                                ),
                                dbc.Col(
                                    dbc.RadioItems(
                                        id=f"date-interval-{PAGE}-{VIZ_ID}",
                                        options=[
                                            {"label": "Month", "value": "M1"},
                                            {"label": "Quarter", "value": "M3"},
                                            {"label": "6 Months", "value": "M6"},
                                            {"label": "Year", "value": "M12"},
                                        ],
                                        value="M1",
                                        inline=True,
                                    ),
                                    className="me-2",
                                ),
                                dbc.Col(
                                    dbc.Button(
                                        "About Graph",
                                        id=f"popover-target-{PAGE}-{VIZ_ID}",
                                        color="secondary",
                                        size="sm",
                                    ),
                                    width="auto",
                                    style={"paddingTop": ".5em"},
                                ),
                            ],
                            align="center",
                        ),
                    ]
                ),
            ]
        )
    ],
)


# callback for graph info popover
@callback(
    Output(f"popover-{PAGE}-{VIZ_ID}", "is_open"),
    [Input(f"popover-target-{PAGE}-{VIZ_ID}", "n_clicks")],
    [State(f"popover-{PAGE}-{VIZ_ID}", "is_open")],
)
def toggle_popover(n, is_open):
    if n:
        return not is_open
    return is_open


# callback for contributors by action graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    Output(f"check-alert-{PAGE}-{VIZ_ID}", "is_open"),
    [
        Input("repo-choices", "data"),
        Input(f"date-interval-{PAGE}-{VIZ_ID}", "value"),
        Input(f"action-dropdown-{PAGE}-{VIZ_ID}", "value"),
        Input("bot-switch", "value"),
    ],
    background=True,
)
def committers_graph(repolist, interval, action, bot_switch):

    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=ctq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=ctq, repos=repolist)

    start = time.perf_counter()
    logging.warning(f"{VIZ_ID}- START")

    # test if there is data
    if df.empty:
        logging.warning(f"{VIZ_ID} - NO DATA AVAILABLE")
        return nodata_graph, False

    # remove bot data
    if bot_switch:
        df = df[~df["cntrb_id"].isin(app.bots_list)]

    # checks if there is a contribution of a specfic action in repo set
    if not df["Action"].str.contains(action).any():
        return dash.no_update, True

    # function for all data pre processing
    df = process_data(df, interval, action)

    fig = create_figure(df, interval, action)

    logging.warning(f"{VIZ_ID} - END - {time.perf_counter() - start}")
    return fig, False


def process_data(df: pd.DataFrame, interval, action):

    # convert to datetime objects rather than strings
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True)

    # order values chronologically by COLUMN_TO_SORT_BY date
    df = df.sort_values(by="created_at", axis=0, ascending=True)

    # drop all contributions that are not the selected action
    df = df[df["Action"].str.contains(action)]

    return df


def create_figure(df: pd.DataFrame, interval, action):
    # time values for graph
    x_r, x_name, hover, period = get_graph_time_values(interval)

    # create plotly express histogram
    fig = px.histogram(df, x="created_at", color_discrete_sequence=[color_seq[3]])

    # creates bins with interval size and customizes the hover value for the bars
    fig.update_traces(
        xbins_size=interval,
        hovertemplate=hover + "<br>" + action + " Contributors: %{y}<br><extra></extra>",
        marker_line_width=0.1,
        marker_line_color="black",
    )

    # update xaxes to align for the interval bin size
    fig.update_xaxes(
        showgrid=True,
        ticklabelmode="period",
        dtick=period,
        rangeslider_yaxis_rangemode="match",
        range=x_r,
    )

    # layout styling
    fig.update_layout(
        xaxis_title=x_name,
        yaxis_title="Committers",
        margin_b=40,
        font=dict(size=14),
    )

    return fig
