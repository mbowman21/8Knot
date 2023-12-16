from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
from dash import callback
from dash.dependencies import Input, Output, State
import pandas as pd
import logging
import plotly.express as px
from pages.utils.graph_utils import get_graph_time_values, color_seq
from cache_manager.cache_manager import CacheManager as cm
from pages.utils.job_utils import nodata_graph
import io
import time

from queries.issues_updated_query import issues_updated_query as iuq


PAGE = "project_engagement"
VIZ_ID = "issues_updated"

gc_issues_updated = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H3(
                    "Issues Updated",
                    className="card-title",
                    style={"textAlign": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody(
                            """
                            Issues updated during a certain period of time.
                            """
                        ),
                    ],
                    id=f"popover-{PAGE}-{VIZ_ID}",
                    target=f"popover-target-{PAGE}-{VIZ_ID}",  # needs to be the same as dbc.Button id
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
                                    "Date Interval:",
                                    html_for=f"date-interval-{PAGE}-{VIZ_ID}",
                                    width="auto",
                                ),
                                dbc.Col(
                                    dbc.RadioItems(
                                        id=f"date-interval-{PAGE}-{VIZ_ID}",
                                        options=[
                                            {
                                                "label": "Day",
                                                "value": "D",
                                            },
                                            {
                                                "label": "Week",
                                                "value": "W",
                                            },
                                            {"label": "Month", "value": "M"},
                                            {"label": "Year", "value": "Y"},
                                        ],
                                        value="M",
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
        ),
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


# callback for commits over time graph
@callback(
    Output(f"{PAGE}-{VIZ_ID}", "figure"),
    [
        Input("repo-choices", "data"),
        Input(f"date-interval-{PAGE}-{VIZ_ID}", "value"),
    ],
    background=True,
)
def issues_updated_over_time_graph(repolist, interval):
    # wait for data to asynchronously download and become available.
    cache = cm()
    df = cache.grabm(func=iuq, repos=repolist)
    while df is None:
        time.sleep(1.0)
        df = cache.grabm(func=iuq, repos=repolist)

    print(df)

    # data ready.
    start = time.perf_counter()
    logging.warning("ISSUES_UPDATED_OVER_TIME_VIZ - START")

    # test if there is data
    if df.empty:
        logging.warning("ISSUES_UPDATED OVER TIME - NO DATA AVAILABLE")
        return nodata_graph

    # function for all data pre processing
    df_created = process_data(df, interval)

    fig = create_figure(df_created, interval)

    logging.warning(f"ISSUES_UPDATED_OVER_TIME_VIZ - END - {time.perf_counter() - start}")
    return fig


def process_data(df: pd.DataFrame, interval):
    # convert to datetime objects with consistent column name
    # incoming value should be a posix integer.
    df["date"] = pd.to_datetime(df["date"], utc=True)
    df.rename(columns={"date": "created"}, inplace=True)

    # variable to slice on to handle weekly period edge case
    period_slice = None
    if interval == "W":
        # this is to slice the extra period information that comes with the weekly case
        period_slice = 10

    # get the count of commits in the desired interval in pandas period format, sort index to order entries
    df_created = (
        df.groupby(by=df.created.dt.to_period(interval))["issues_updated"]
        .nunique()
        .reset_index()
        .rename(columns={"created": "Date"})
    )

    # converts date column to a datetime object, converts to string first to handle period information
    # the period slice is to handle weekly corner case
    df_created["Date"] = pd.to_datetime(df_created["Date"].astype(str).str[:period_slice])

    return df_created


def create_figure(df_created: pd.DataFrame, interval):
    # time values for graph
    x_r, x_name, hover, period = get_graph_time_values(interval)

    # graph geration
    fig = px.bar(
        df_created,
        x="Date",
        y="issues_updated",
        range_x=x_r,
        labels={"x": x_name, "y": "Issues Updated"},
        color_discrete_sequence=[color_seq[3]],
    )
    fig.update_traces(hovertemplate=hover + "<br>Issues Updated: %{y}<br>")
    fig.update_xaxes(
        showgrid=True,
        ticklabelmode="period",
        dtick=period,
        rangeslider_yaxis_rangemode="match",
        range=x_r,
    )
    fig.update_layout(
        xaxis_title=x_name,
        yaxis_title="Number of Issues Updated",
        margin_b=40,
        margin_r=20,
        font=dict(size=14),
    )

    return fig
