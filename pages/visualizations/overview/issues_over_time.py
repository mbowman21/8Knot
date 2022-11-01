from dash import html, dcc
import dash
import dash_bootstrap_components as dbc
from dash import callback
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go
import pandas as pd
import datetime as dt
import logging
import plotly.express as px
from pages.utils.graph_utils import get_graph_time_values

from pages.utils.job_utils import handle_job_state, nodata_graph
from queries.issues_query import issues_query as iq
from app import jm

import time

gc_issues_over_time = dbc.Card(
    [
        dbc.CardBody(
            [
                dcc.Interval(
                    id="issues-over-time-timer",
                    disabled=False,
                    n_intervals=1,
                    max_intervals=1,
                    interval=1500,
                ),
                html.H4(
                    "Issues Over Time",
                    className="card-title",
                    style={"text-align": "center"},
                ),
                dbc.Popover(
                    [
                        dbc.PopoverHeader("Graph Info:"),
                        dbc.PopoverBody("Information on overview graph 3"),
                    ],
                    id="overview-popover-3",
                    target="overview-popover-target-3",  # needs to be the same as dbc.Button id
                    placement="top",
                    is_open=False,
                ),
                dcc.Graph(id="issues-over-time"),
                dbc.Form(
                    [
                        dbc.Row(
                            [
                                dbc.Label(
                                    "Date Interval:",
                                    html_for="issue-time-interval",
                                    width="auto",
                                    style={"font-weight": "bold"},
                                ),
                                dbc.Col(
                                    dbc.RadioItems(
                                        id="issue-time-interval",
                                        options=[
                                            {
                                                "label": "Day",
                                                "value": "D",
                                            },  # days in milliseconds for ploty use
                                            {
                                                "label": "Week",
                                                "value": "W",
                                            },  # weeks in milliseconds for ploty use
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
                                        id="overview-popover-target-3",
                                        color="secondary",
                                        size="sm",
                                    ),
                                    width="auto",
                                    style={"padding-top": ".5em"},
                                ),
                            ],
                            align="center",
                        ),
                    ]
                ),
            ]
        ),
    ],
    color="light",
)

# call backs for card graph 3 - Issue Over Time
@callback(
    Output("overview-popover-3", "is_open"),
    [Input("overview-popover-target-3", "n_clicks")],
    [State("overview-popover-3", "is_open")],
)
def toggle_popover_3(n, is_open):
    if n:
        return not is_open
    return is_open


# callback for issues over time graph
@callback(
    Output("issues-over-time", "figure"),
    Output("issues-over-time-timer", "n_intervals"),
    [
        Input("repo-choices", "data"),
        Input("issues-over-time-timer", "n_intervals"),
        Input("issue-time-interval", "value"),
    ],
)
def issues_over_time_graph(repolist, timer_pings, interval):
    logging.debug("IOT - PONG")

    ready, results, graph_update, interval_update = handle_job_state(jm, iq, repolist)
    if not ready:
        return graph_update, interval_update

    logging.debug("ISSUES_OVER_TIME_VIZ - START")
    start = time.perf_counter()

    # create dataframe from record data
    df = pd.DataFrame(results)

    # convert to datetime objects rather than strings
    try:
        df["created"] = pd.to_datetime(df["created"], utc=True)
        df["closed"] = pd.to_datetime(df["closed"], utc=True)
    except:
        logging.debug("PULL REQUEST STALENESS - NO DATA AVAILABLE")
        return nodata_graph, False, dash.no_update

    # order values chronologically by creation date
    df = df.sort_values(by="created")

    # first and last elements of the dataframe are the
    # earliest and latest events respectively
    earliest = df.iloc[0]["created"]
    latest = df.iloc[-1]["created"]

    # beginning to the end of time by the specified interval
    dates = pd.date_range(start=earliest, end=latest, freq=interval, inclusive="both")

    base = [["Date", "Created", "Closed", "Open"]]
    for date in dates:
        counts = try_new(df, date, interval)
        base.append(counts)

    df_status = pd.DataFrame(base[1:], columns=base[0])

    # time values for graph
    x_r, x_name, hover, period = get_graph_time_values(interval)

    # graph generation
    if df is not None:
        fig = go.Figure()
        fig.add_bar(
            x=df_status["Date"],
            y=df_status["Created"],
            opacity=0.75,
            hovertemplate=hover + "<br>Created: %{y}<br>" + "<extra></extra>",
            offsetgroup=0,
            name="Issues Created",
        )
        fig.add_bar(
            x=df_status["Date"],
            y=df_status["Closed"],
            opacity=0.6,
            hovertemplate=hover + "<br>Closed: %{y}<br>" + "<extra></extra>",
            offsetgroup=1,
            name="Issues Closed",
        )
        # fig.update_traces(xbins_size=interval)
        fig.update_xaxes(
            showgrid=True,
            ticklabelmode="period",
            dtick=period,
            rangeslider_yaxis_rangemode="match",
            range=x_r,
        )
        fig.update_layout(
            xaxis_title=x_name,
            yaxis_title="Number of Issues",
            bargroupgap=0.1,
            margin_b=40,
        )
        fig.add_trace(
            go.Scatter(
                x=df_status["Date"],
                y=df_status["Open"],
                mode="lines",
                name="Issues Actively Open",
                hovertemplate="Issues Open: %{y}" + "<extra></extra>",
            )
        )
        logging.debug(f"ISSUES_OVER_TIME_VIZ - END - {time.perf_counter() - start}")

        # return fig, diable timer.
        return fig, dash.no_update
    else:
        # don't change figure, disable timer.
        return dash.no_update, dash.no_update


def try_new(df, date, interval):

    num_created = 0
    num_closed = 0

    # drop rows that are more recent than the date limit
    df_lim = df[df["created"] <= date]

    df_open = df_lim[df_lim["closed"] > date]
    df_open = df_open.append(df_lim[df_lim.closed.isnull()])
    num_open = df_open.shape[0]

    str_date = date.isoformat()

    if interval == "D":
        num_created = df_lim[df_lim["created"].dt.date == date].shape[0]
        num_closed = df_lim[df_lim["closed"].dt.date == date].shape[0]
    elif interval == "W":
        num_created = df_lim[(df_lim["created"].dt.week == date.week) & (df_lim["created"].dt.year == date.year)].shape[
            0
        ]
        num_closed = df_lim[(df_lim["closed"].dt.week == date.week) & (df_lim["closed"].dt.year == date.year)].shape[0]
    elif interval == "M":
        num_created = df_lim[df_lim["created"].dt.strftime("%Y-%m") == str_date[:7]].shape[0]
        num_closed = df_lim[df_lim["closed"].dt.strftime("%Y-%m") == str_date[:7]].shape[0]
    elif interval == "Y":
        num_created = df_lim[df_lim["created"].dt.year == date.year].shape[0]
        num_closed = df_lim[df_lim["closed"].dt.year == date.year].shape[0]
    else:
        return "error"

    return [date, num_created, num_closed, num_open]
