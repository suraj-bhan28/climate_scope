import streamlit as st
import pandas as pd
import plotly.express as px

# ================= LOAD DATA =================
df = pd.read_csv("global_weather_clean.csv")

# Convert datetime
df['last_updated'] = pd.to_datetime(df['last_updated'])

st.title("ClimateScope: Global Weather Dashboard")

# ================= SIDEBAR FILTERS =================
st.sidebar.header("Filters")

selected_country = st.sidebar.selectbox(
    "Select Country", sorted(df['country'].unique())
)

selected_variable = st.sidebar.selectbox(
    "Weather Variable",
    ['temperature_celsius','precip_mm','humidity','wind_kph','pressure_mb','visibility_km','uv_index']
)

date_range = st.sidebar.date_input(
    "Select Date Range",
    [df['last_updated'].min().date(), df['last_updated'].max().date()]
)

# Apply filters
mask = (
    (df['country'] == selected_country) &
    (df['last_updated'].between(pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])))
)

filtered_df = df.loc[mask]

# Safety check
if filtered_df.empty:
    st.warning("No data available for selected filters")
    st.stop()


# ================= KPI METRICS =================
# Quick statistical summary for decision makers

st.subheader("Current Summary")

col1, col2, col3, col4 = st.columns(4)

col1.metric("Avg Temp (°C)", round(filtered_df['temperature_celsius'].mean(),2))
col2.metric("Avg Humidity (%)", round(filtered_df['humidity'].mean(),2))
col3.metric("Avg Wind (kph)", round(filtered_df['wind_kph'].mean(),2))
col4.metric("Avg Precip (mm)", round(filtered_df['precip_mm'].mean(),2))


# ================= TIME SERIES TREND =================
# Shows how weather variable changes over time

st.subheader("Time Trend")

time_series = filtered_df.sort_values("last_updated")

fig_time = px.line(
    time_series,
    x='last_updated',
    y=selected_variable,
    title=f"{selected_variable} Trend Over Time in {selected_country}"
)

st.plotly_chart(fig_time, use_container_width=True)


# ================= MONTHLY SEASONAL TREND =================
# Detects seasonal patterns across months

st.subheader("Seasonal Monthly Pattern")

filtered_df['month'] = filtered_df['last_updated'].dt.month

monthly_avg = filtered_df.groupby('month')[selected_variable].mean().reset_index()

fig_month = px.line(
    monthly_avg,
    x='month',
    y=selected_variable,
    markers=True,
    title=f"Monthly Seasonal Trend of {selected_variable}"
)

st.plotly_chart(fig_month, use_container_width=True)


# ================= GLOBAL CHOROPLETH =================
# Shows geographic comparison between countries

st.subheader("Global Comparison")

regional_avg = df.groupby('country')[selected_variable].mean().reset_index()

fig_map = px.choropleth(
    regional_avg,
    locations='country',
    locationmode='country names',
    color=selected_variable,
    title=f"Global {selected_variable} Comparison",
    color_continuous_scale='RdYlBu'
)

st.plotly_chart(fig_map, use_container_width=True)


# ================= DISTRIBUTION HISTOGRAM =================
# Shows distribution and spread of values

st.subheader("Distribution of Selected Variable")

fig_hist = px.histogram(
    filtered_df,
    x=selected_variable,
    nbins=40,
    title=f"Distribution of {selected_variable}"
)

st.plotly_chart(fig_hist, use_container_width=True)


# ================= EXTREME EVENTS BOXPLOT =================
# Helps detect outliers like storms or heatwaves

st.subheader("Extreme Events Detection")

fig_box = px.box(
    filtered_df,
    y=selected_variable,
    title=f"Extreme Values in {selected_country}"
)

st.plotly_chart(fig_box, use_container_width=True)


# ================= WEATHER RELATIONSHIP SCATTER =================
# Shows relationship between two weather variables

st.subheader("Weather Relationship Explorer")

x_axis = st.selectbox(
    "X-axis",
    ['temperature_celsius','humidity','wind_kph','pressure_mb','visibility_km'],
    index=0
)

y_axis = st.selectbox(
    "Y-axis",
    ['temperature_celsius','humidity','wind_kph','pressure_mb','visibility_km'],
    index=1
)

fig_scatter = px.scatter(
    filtered_df,
    x=x_axis,
    y=y_axis,
    title=f"{y_axis} vs {x_axis}",
    opacity=0.6
)

st.plotly_chart(fig_scatter, use_container_width=True)


# ================= CORRELATION HEATMAP =================
# Shows relationships useful for analysis and ML insights

st.subheader("Weather Correlation Heatmap")

corr_cols = [
    'temperature_celsius','precip_mm','humidity','wind_kph',
    'pressure_mb','visibility_km','uv_index'
]

corr_matrix = filtered_df[corr_cols].corr()

fig_heat = px.imshow(
    corr_matrix,
    text_auto=True,
    aspect="auto",
    title="Correlation Between Weather Variables"
)

st.plotly_chart(fig_heat, use_container_width=True)


# ================= AIR QUALITY ANALYSIS =================
# Important environmental indicators

st.subheader("Air Quality Indicators")

aq_cols = ['air_quality_PM2.5','air_quality_PM10','air_quality_Ozone']

aq_avg = filtered_df[aq_cols].mean().reset_index()
aq_avg.columns = ['Pollutant','Value']

fig_aq = px.bar(
    aq_avg,
    x='Pollutant',
    y='Value',
    title="Average Air Quality Levels"
)

st.plotly_chart(fig_aq, use_container_width=True)