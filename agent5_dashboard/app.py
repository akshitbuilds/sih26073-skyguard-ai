"""
SkyGuard AI - Agent 5: Correction & Alert + Dashboard
Smart India Hackathon 2026 | SIH26073 | Team Agentic Genesis

Run with:  streamlit run app.py

Data source: currently mock_data.py (self-contained simulation of the
Agent 1-4 pipeline output). Swap `load_records()` to pull from the real
backend feed/API once integration happens - see the SWAP-IN POINT comment.
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timezone

from schema import HEALTH_COLOR, SEVERITY_COLOR, SEVERITY_ORDER, HEALTH_ORDER
from mock_data import build_network, build_current_records
from correction import estimate_corrected_value

st.set_page_config(page_title="SkyGuard AI Dashboard", page_icon="🌦️", layout="wide")

# ----------------------------------------------------------------------------
# DATA LOADING  (SWAP-IN POINT: replace this function body with a call to the
# real Agent 1-4 pipeline output / API / JSON feed, keeping the same return
# shape: a list of records following schema.RECORD_FIELDS.)
# ----------------------------------------------------------------------------
@st.cache_data(ttl=30)
def load_records(_seed_tick: int):
    histories, true_values = build_network()

    def corr_fn(sid, hist, snap, meta, healthy_ids):
        return estimate_corrected_value(sid, hist, snap, meta, healthy_ids)

    records = build_current_records(histories, corr_fn)
    return records, histories


if "tick" not in st.session_state:
    st.session_state.tick = 0

records, histories = load_records(st.session_state.tick)
df = pd.DataFrame(records)

# ----------------------------------------------------------------------------
# SIDEBAR
# ----------------------------------------------------------------------------
with st.sidebar:
    st.title("🌦️ SkyGuard AI")
    st.caption("Agent 5 · Correction & Alert + Dashboard")
    st.caption("SIH 2026 · SIH26073 · Ministry of Earth Sciences")
    st.caption("Team: Agentic Genesis")
    st.divider()

    if st.button("🔄 Refresh feed (simulate new tick)", use_container_width=True):
        st.session_state.tick += 1
        st.cache_data.clear()
        st.rerun()

    st.caption(f"Last refreshed: {datetime.now(timezone.utc).strftime('%H:%M:%S UTC')}")
    st.divider()

    st.subheader("Filters")
    health_filter = st.multiselect("Sensor health", ["green", "amber", "red"], default=["green", "amber", "red"])
    severity_filter = st.multiselect(
        "Alert severity", ["critical", "high", "medium", "low", "none"],
        default=["critical", "high", "medium", "low", "none"],
    )
    st.divider()
    st.subheader("Network summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("🟢", int((df["sensor_health_status"] == "green").sum()))
    c2.metric("🟡", int((df["sensor_health_status"] == "amber").sum()))
    c3.metric("🔴", int((df["sensor_health_status"] == "red").sum()))

filtered_df = df[df["sensor_health_status"].isin(health_filter) & df["alert_severity"].isin(severity_filter)]

# ----------------------------------------------------------------------------
# HEADER
# ----------------------------------------------------------------------------
st.title("SkyGuard AI — Live Network Monitor")
st.caption("Distinguishing genuine weather events from Automatic Weather Station sensor faults, in real time.")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total stations", len(df))
m2.metric("Active faults", int(df["anomaly_type"].isin(
    ["sensor_stuck", "sensor_spike", "sensor_drift", "sensor_dropout"]).sum()))
m3.metric("Genuine events flagged (cleared)", int((df["anomaly_type"] == "genuine_event").sum()))
m4.metric("Critical/High alerts", int(df["alert_severity"].isin(["critical", "high"]).sum()))

st.divider()

# ----------------------------------------------------------------------------
# MAP + STATION LIST
# ----------------------------------------------------------------------------
left, right = st.columns([1.3, 1])

with left:
    st.subheader("📍 Station Map — colored by sensor health")
    map_df = filtered_df.copy()
    map_df["color"] = map_df["sensor_health_status"].map(
        lambda h: {"green": [46, 204, 113], "amber": [243, 156, 18], "red": [231, 76, 60]}[h]
    )
    map_df["size"] = map_df["alert_severity"].map(
        {"critical": 45000, "high": 35000, "medium": 25000, "low": 18000, "none": 12000}
    )

    try:
        import pydeck as pdk
        layer = pdk.Layer(
            "ScatterplotLayer",
            data=map_df,
            get_position="[longitude, latitude]",
            get_fill_color="color",
            get_radius="size",
            pickable=True,
            opacity=0.75,
        )
        view_state = pdk.ViewState(latitude=21.22, longitude=70.98, zoom=7.2)
        st.pydeck_chart(pdk.Deck(
            layers=[layer], initial_view_state=view_state,
            tooltip={"text": "{station_id} ({_station_name})\nHealth: {sensor_health_status}\nAnomaly: {anomaly_type}"},
            map_provider="carto",
            map_style="light",
        ))
    except Exception:
        st.map(map_df.rename(columns={"latitude": "lat", "longitude": "lon"})[["lat", "lon"]])

    st.subheader("📋 Station List")
    list_view = filtered_df[[
        "station_id", "_station_name", "sensor_health_status", "anomaly_type", "alert_severity", "confidence_score"
    ]].rename(columns={"_station_name": "name", "sensor_health_status": "health", "confidence_score": "confidence"})
    list_view = list_view.sort_values(
        by="health", key=lambda s: s.map(HEALTH_ORDER)
    )

    def _badge(val, colormap):
        color = colormap.get(val, "#999")
        return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:10px;font-size:0.8em;">{val}</span>'

    display_rows = []
    for _, row in list_view.iterrows():
        display_rows.append({
            "Station": f"{row['station_id']} · {row['name']}",
            "Health": _badge(row["health"], HEALTH_COLOR),
            "Anomaly type": row["anomaly_type"],
            "Severity": _badge(row["alert_severity"], SEVERITY_COLOR),
            "Confidence": f"{row['confidence']:.0%}",
        })
    st.markdown(
        pd.DataFrame(display_rows).to_html(escape=False, index=False),
        unsafe_allow_html=True,
    )

# ----------------------------------------------------------------------------
# ALERT FEED
# ----------------------------------------------------------------------------
with right:
    st.subheader("🚨 Alert Feed")
    alert_df = filtered_df[filtered_df["alert_severity"] != "none"].copy()
    alert_df["_sort"] = alert_df["alert_severity"].map(SEVERITY_ORDER)
    alert_df = alert_df.sort_values("_sort")

    if alert_df.empty:
        st.success("No active alerts. All monitored stations nominal.")
    else:
        for _, row in alert_df.iterrows():
            color = SEVERITY_COLOR.get(row["alert_severity"], "#999")
            with st.container(border=True):
                st.markdown(
                    f'<span style="background:{color};color:white;padding:2px 10px;'
                    f'border-radius:10px;font-size:0.85em;font-weight:600;">'
                    f'{row["alert_severity"].upper()}</span> &nbsp; **{row["station_id"]}** · {row["_station_name"]}',
                    unsafe_allow_html=True,
                )
                anomaly_label = row["anomaly_type"].replace("_", " ").title()
                st.markdown(f"**{anomaly_label}** &nbsp;|&nbsp; confidence {row['confidence_score']:.0%}")
                st.caption(row["explanation"]["reasoning_text"])

# ----------------------------------------------------------------------------
# STATION DETAIL VIEW
# ----------------------------------------------------------------------------
st.divider()
st.subheader("🔍 Station Detail")

station_ids = sorted(df["station_id"].tolist())
default_idx = 0
flagged_ids = df[df["anomaly_type"] != "none"]["station_id"].tolist()
if flagged_ids:
    default_idx = station_ids.index(sorted(flagged_ids)[0])

selected_id = st.selectbox("Select a station", station_ids, index=default_idx)
selected = df[df["station_id"] == selected_id].iloc[0]

d1, d2 = st.columns([1, 1.2])

with d1:
    st.markdown(f"### {selected_id} — {selected['_station_name']}")
    health = selected["sensor_health_status"]
    st.markdown(
        f'Sensor health: <span style="background:{HEALTH_COLOR[health]};color:white;'
        f'padding:2px 10px;border-radius:10px;">{health.upper()}</span>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**Anomaly type:** {selected['anomaly_type'].replace('_', ' ').title()}")
    st.markdown(f"**Alert severity:** {selected['alert_severity'].upper()}")
    st.markdown(f"**Confidence score:** {selected['confidence_score']:.0%}")
    st.markdown(f"**Screening flag:** `{selected['screening_flag']}`")

    st.markdown("**Why it was flagged:**")
    st.info(selected["explanation"]["reasoning_text"])
    st.markdown("**Top contributing factors:**")
    for factor in selected["explanation"]["top_factors"]:
        st.markdown(f"- `{factor}`")

    st.markdown("**Detection scores:**")
    sc1, sc2, sc3 = st.columns(3)
    sc1.metric("Spatial deviation", f"{selected['spatial_deviation_score']:.2f}")
    sc2.metric("Physical consistency", f"{selected['physical_consistency_score']:.2f}")
    sc3.metric("ML anomaly score", f"{selected['ml_anomaly_score']:.2f}")

with d2:
    st.markdown("**Raw reading vs. corrected value**")
    raw = {"Temperature (°C)": selected["temperature_c"],
           "Pressure (hPa)": selected["pressure_hpa"],
           "Humidity (%)": selected["humidity_pct"]}
    corrected = selected["corrected_value"]

    if corrected:
        comp_df = pd.DataFrame({
            "Metric": list(raw.keys()),
            "Raw (as reported)": list(raw.values()),
            "Corrected (estimated true)": [corrected["temperature_c"], corrected["pressure_hpa"], corrected["humidity_pct"]],
        })
        st.dataframe(comp_df, hide_index=True, use_container_width=True)
    elif selected["anomaly_type"] == "genuine_event":
        st.success("Classified as a genuine weather event — raw values are trusted, no correction applied.")
        st.dataframe(pd.DataFrame({"Metric": list(raw.keys()), "Raw (as reported)": list(raw.values())}),
                     hide_index=True, use_container_width=True)
    else:
        st.dataframe(pd.DataFrame({"Metric": list(raw.keys()), "Raw (as reported)": list(raw.values())}),
                     hide_index=True, use_container_width=True)
        st.caption("No correction available (insufficient history/neighbor data).")

    st.markdown("**Recent history (last 12 hours)**")
    hist_df = pd.DataFrame(histories[selected_id])
    hist_df = hist_df.set_index("timestamp")
    metric_choice = st.radio("Metric", ["temperature_c", "pressure_hpa", "humidity_pct"], horizontal=True)
    chart_df = hist_df[[metric_choice]].copy()
    if corrected:
        chart_df.loc[chart_df.index[-1], "corrected"] = corrected[metric_choice]
    st.line_chart(chart_df)

st.divider()
st.caption("SkyGuard AI · Agent 5 (Correction & Alert + Dashboard) · Team Agentic Genesis · SIH 2026 · SIH26073")