"""
ClimateScope - Advanced Weather Analytics Dashboard
Streamlit Implementation of Power BI Visualizations

MANUAL SETUP REQUIRED:
======================
1. Install required packages:
   pip install streamlit pandas numpy plotly folium streamlit-folium pydeck

2. For map visualizations to work properly, you may need to get a Mapbox token:
   - Sign up at https://www.mapbox.com/
   - Get your free API token
   - Replace 'YOUR_MAPBOX_TOKEN_HERE' in the code below

3. Place this script and the 'global_weather_clean.csv' file in the same directory

4. Run with: streamlit run climate_scope_dashboard.py

5. For deployment, set up environment variable for Mapbox token if using advanced maps
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')

# =============================================================================
# PAGE CONFIGURATION
# =============================================================================
st.set_page_config(
    page_title="ClimateScope - Global Weather Analytics",
    page_icon="🌍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =============================================================================
# CUSTOM CSS - Dark Theme (Digital Cockpit Aesthetic)
# =============================================================================
st.markdown("""
<style>
    :root {
        --bg-primary: #1A1D21;
        --bg-secondary: #37474F;
        --accent-teal: #4DB6AC;
        --accent-amber: #FFCA28;
        --text-primary: #ECEFF1;
        --text-secondary: #B0BEC5;
    }
    .main { background-color: #1A1D21; color: #ECEFF1; }
    .stApp { background-color: #1A1D21; }
    h1, h2, h3, h4 { color: #4DB6AC !important; font-family: 'Liter', sans-serif; }
    .metric-card {
        background: linear-gradient(135deg, #37474F 0%, #263238 100%);
        border-radius: 12px; padding: 20px;
        border-left: 4px solid #4DB6AC;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .kpi-value { font-size: 2.5em; font-weight: bold; color: #4DB6AC; }
    .kpi-label { color: #B0BEC5; font-size: 0.9em; text-transform: uppercase; letter-spacing: 1px; }
    .alert-card {
        background: linear-gradient(135deg, #37474F 0%, #263238 100%);
        border-radius: 12px; padding: 15px;
        border-left: 4px solid #FFCA28;
    }
    .stSelectbox, .stSlider, .stDateInput { background-color: #37474F; border-radius: 8px; }
    .css-1d391kg { background-color: #263238; }
    .dataframe { background-color: #37474F; color: #ECEFF1; }
    .js-plotly-plot { background-color: transparent !important; }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# DATA LOADING AND PREPROCESSING
# =============================================================================
@st.cache_data
def load_data():
    """Load and preprocess weather data"""
    df = pd.read_csv('global_weather_clean.csv')
    df['last_updated'] = pd.to_datetime(df['last_updated'])

    # Extract continent from timezone
    df['continent'] = df['timezone'].str.split('/').str[0]

    # Create a guaranteed positive size column for visualizations.
    min_temp = df['temperature_celsius'].min()
    df['viz_size'] = df['temperature_celsius'] - min_temp + 1

    # Create temperature categories
    df['temp_category'] = pd.cut(
        df['temperature_celsius'],
        bins=[-float('inf'), 10, 25, 35, float('inf')],
        labels=['Cold (<10°C)', 'Moderate (10-25°C)', 'Hot (25-35°C)', 'Extreme (>35°C)']
    )

    # Create wind categories
    df['wind_category'] = pd.cut(
        df['wind_kph'],
        bins=[0, 5, 15, 25, 40, 60, float('inf')],
        labels=['Calm (0-5)', 'Light (5-15)', 'Moderate (15-25)', 'Strong (25-40)', 'Gale (40-60)', 'Storm (>60)']
    )

    # Calculate comfort index (Heat Index approximation)
    df['comfort_index'] = (
        -42.379
        + 2.04901523 * df['temperature_celsius']
        + 10.14333127 * df['humidity']
        - 0.22475541 * df['temperature_celsius'] * df['humidity']
    )

    # AQI Status
    def get_aqi_status(aqi):
        if aqi <= 50:
            return "Good"
        elif aqi <= 100:
            return "Moderate"
        elif aqi <= 150:
            return "Unhealthy for Sensitive"
        else:
            return "Unhealthy"

    df['aqi_status'] = df['air_quality_us-epa-index'].apply(get_aqi_status)

    return df


# Load data
try:
    df = load_data()
    data_loaded = True
except Exception as e:
    st.error(f"Error loading data: {e}")
    st.info("Please ensure 'global_weather_clean.csv' is in the same directory as this script")
    data_loaded = False

if data_loaded:
    # Get latest data per country for overview
    latest_df = df.loc[df.groupby('country')['last_updated'].idxmax()].copy()

    # =============================================================================
    # SIDEBAR - FILTERS
    # =============================================================================
    st.sidebar.markdown("## 🌍 ClimateScope Filters")
    st.sidebar.markdown("---")

    # Continent filter
    continents = ['All'] + sorted(df['continent'].unique().tolist())
    selected_continent = st.sidebar.selectbox("Continent", continents)

    # Country filter (dependent on continent)
    if selected_continent != 'All':
        countries = ['All'] + sorted(df[df['continent'] == selected_continent]['country'].unique().tolist())
    else:
        countries = ['All'] + sorted(df['country'].unique().tolist())

    selected_country = st.sidebar.selectbox("Country", countries)

    # Date range filter
    min_date = df['last_updated'].min().date()
    max_date = df['last_updated'].max().date()

    date_range = st.sidebar.date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date
    )

    # Temperature range slider
    temp_range = st.sidebar.slider(
        "Temperature Range (°C)",
        float(df['temperature_celsius'].min()),
        float(df['temperature_celsius'].max()),
        (float(df['temperature_celsius'].min()), float(df['temperature_celsius'].max()))
    )

    # Apply filters
    filtered_df = df.copy()

    if selected_continent != 'All':
        filtered_df = filtered_df[filtered_df['continent'] == selected_continent]

    if selected_country != 'All':
        filtered_df = filtered_df[filtered_df['country'] == selected_country]

    if len(date_range) == 2:
        filtered_df = filtered_df[
            (filtered_df['last_updated'].dt.date >= date_range[0]) &
            (filtered_df['last_updated'].dt.date <= date_range[1])
        ]

    filtered_df = filtered_df[
        (filtered_df['temperature_celsius'] >= temp_range[0]) &
        (filtered_df['temperature_celsius'] <= temp_range[1])
    ]

    # Get latest filtered data
    latest_filtered = filtered_df.loc[filtered_df.groupby('country')['last_updated'].idxmax()].copy()

    # =============================================================================
    # MAIN DASHBOARD TITLE
    # =============================================================================
    st.markdown("""
    <div style='text-align: center; padding: 20px;'>
        <h1 style='font-size: 3em; margin-bottom: 0;'>🌍 ClimateScope</h1>
        <p style='color: #B0BEC5; font-size: 1.2em;'>Advanced Power BI Dashboard for Global Weather Analytics</p>
    </div>
    """, unsafe_allow_html=True)

    # =============================================================================
    # NAVIGATION TABS
    # =============================================================================
    tab1, tab2, tab3, tab4 = st.tabs([
        "🌡️ Temperature Overview",
        "💧 Humidity & Air Quality",
        "🌪️ Wind & Precipitation",
        "🗺️ Geographic Patterns"
    ])

    # =============================================================================
    # TAB 1: GLOBAL TEMPERATURE OVERVIEW
    # =============================================================================
    with tab1:
        st.markdown("## 🌡️ Global Temperature Overview Dashboard")

        # KPI Cards Row
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            avg_temp = latest_filtered['temperature_celsius'].mean()
            st.markdown(f"""
            <div class='metric-card'>
                <div class='kpi-label'>Global Average</div>
                <div class='kpi-value'>{avg_temp:.1f}°C</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            max_temp = latest_filtered['temperature_celsius'].max()
            max_temp_country = latest_filtered.loc[latest_filtered['temperature_celsius'].idxmax(), 'country']
            st.markdown(f"""
            <div class='metric-card'>
                <div class='kpi-label'>Highest Recorded</div>
                <div class='kpi-value'>{max_temp:.1f}°C</div>
                <div style='color: #FFCA28; font-size: 0.8em;'>{max_temp_country}</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            min_temp = latest_filtered['temperature_celsius'].min()
            min_temp_country = latest_filtered.loc[latest_filtered['temperature_celsius'].idxmin(), 'country']
            st.markdown(f"""
            <div class='metric-card'>
                <div class='kpi-label'>Lowest Recorded</div>
                <div class='kpi-value'>{min_temp:.1f}°C</div>
                <div style='color: #4DB6AC; font-size: 0.8em;'>{min_temp_country}</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            extreme_count = len(latest_filtered[latest_filtered['temperature_celsius'] > 35])
            st.markdown(f"""
            <div class='alert-card'>
                <div class='kpi-label'>Extreme Heat Alerts</div>
                <div class='kpi-value' style='color: #FFCA28;'>{extreme_count}</div>
                <div style='color: #B0BEC5; font-size: 0.8em;'>Countries affected</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Temperature Trends by Region
        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.markdown("### 📊 Temperature Trends by Region")

            region_temp = latest_filtered.groupby('continent')['temperature_celsius'].agg(['mean', 'min', 'max']).reset_index()
            region_temp = region_temp.sort_values('mean', ascending=True)

            fig = go.Figure()
            fig.add_trace(go.Bar(
                y=region_temp['continent'],
                x=region_temp['mean'],
                name='Average',
                orientation='h',
                marker_color='#4DB6AC',
                text=region_temp['mean'].round(1),
                textposition='auto'
            ))
            fig.add_trace(go.Scatter(
                y=region_temp['continent'],
                x=region_temp['max'],
                mode='markers',
                name='Max',
                marker=dict(color='#FFCA28', size=12, symbol='diamond')
            ))
            fig.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=400,
                xaxis_title='Temperature (°C)',
                yaxis_title='Continent',
                legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_right:
            st.markdown("### 🌡️ Temperature Distribution")

            temp_dist = latest_filtered['temp_category'].value_counts()
            colors = ['#4DB6AC', '#81C784', '#FFB74D', '#E57373']
            fig_pie = go.Figure(data=[go.Pie(
                labels=temp_dist.index,
                values=temp_dist.values,
                hole=0.4,
                marker_colors=colors,
                textinfo='label+percent',
                textfont_size=10
            )])
            fig_pie.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                height=350,
                showlegend=False,
                margin=dict(t=30, b=30, l=30, r=30)
            )
            st.plotly_chart(fig_pie, use_container_width=True)

        # Temperature vs Feels Like Comparison
        st.markdown("### 🔄 Actual vs Feels-Like Temperature")

        fig_scatter = px.scatter(
            latest_filtered,
            x='temperature_celsius',
            y='feels_like_celsius',
            color='continent',
            size='humidity',
            hover_data=['country', 'humidity'],
            template='plotly_dark',
            color_discrete_sequence=px.colors.qualitative.Set2
        )
        fig_scatter.add_trace(go.Scatter(
            x=[-30, 50],
            y=[-30, 50],
            mode='lines',
            line=dict(dash='dash', color='gray'),
            name='Perfect Match',
            showlegend=True
        ))
        fig_scatter.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=450,
            xaxis_title='Actual Temperature (°C)',
            yaxis_title='Feels Like Temperature (°C)'
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Anomaly Detection
        st.markdown("### ⚠️ Temperature Anomaly Detection")

        latest_filtered['temp_zscore'] = np.abs(
            (latest_filtered['temperature_celsius'] - latest_filtered['temperature_celsius'].mean()) /
            latest_filtered['temperature_celsius'].std()
        )
        anomalies = latest_filtered[latest_filtered['temp_zscore'] > 2].sort_values('temp_zscore', ascending=False).head(10)

        if not anomalies.empty:
            fig_anomaly = go.Figure()
            fig_anomaly.add_trace(go.Scatter(
                x=latest_filtered['country'],
                y=latest_filtered['temperature_celsius'],
                mode='markers',
                name='Normal',
                marker=dict(color='#4DB6AC', size=8, opacity=0.6)
            ))
            fig_anomaly.add_trace(go.Scatter(
                x=anomalies['country'],
                y=anomalies['temperature_celsius'],
                mode='markers',
                name='Anomaly (|Z| > 2)',
                marker=dict(color='#FFCA28', size=15, symbol='star')
            ))
            fig_anomaly.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=350,
                xaxis_title='Country',
                yaxis_title='Temperature (°C)',
                showlegend=True
            )
            st.plotly_chart(fig_anomaly, use_container_width=True)
        else:
            st.info("No significant temperature anomalies detected in current selection.")

    # =============================================================================
    # TAB 2: HUMIDITY & AIR QUALITY
    # =============================================================================
    with tab2:
        st.markdown("## 💧 Humidity & Comfort Index Dashboard")

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            avg_humidity = latest_filtered['humidity'].mean()
            st.markdown(f"""
            <div class='metric-card'>
                <div class='kpi-label'>Avg Humidity</div>
                <div class='kpi-value'>{avg_humidity:.1f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            avg_comfort = latest_filtered['comfort_index'].mean()
            st.markdown(f"""
            <div class='metric-card'>
                <div class='kpi-label'>Comfort Index</div>
                <div class='kpi-value'>{avg_comfort:.1f}</div>
                <div style='color: #B0BEC5; font-size: 0.8em;'>
                    {'Comfortable' if 60 < avg_comfort < 80 else 'Uncomfortable'}
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            max_humidity = latest_filtered['humidity'].max()
            max_hum_country = latest_filtered.loc[latest_filtered['humidity'].idxmax(), 'country']
            st.markdown(f"""
            <div class='metric-card'>
                <div class='kpi-label'>Highest Humidity</div>
                <div class='kpi-value'>{max_humidity:.0f}%</div>
                <div style='color: #4DB6AC; font-size: 0.8em;'>{max_hum_country}</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            min_humidity = latest_filtered['humidity'].min()
            min_hum_country = latest_filtered.loc[latest_filtered['humidity'].idxmin(), 'country']
            st.markdown(f"""
            <div class='metric-card'>
                <div class='kpi-label'>Lowest Humidity</div>
                <div class='kpi-value'>{min_humidity:.0f}%</div>
                <div style='color: #FFCA28; font-size: 0.8em;'>{min_hum_country}</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        col_left, col_right = st.columns([2, 1])

        with col_left:
            st.markdown("### 🌡️💧 Temperature vs Humidity Correlation")

            fig_corr = px.scatter(
                latest_filtered,
                x='temperature_celsius',
                y='humidity',
                color='continent',
                size='comfort_index',
                hover_data=['country', 'comfort_index'],
                template='plotly_dark',
                trendline='ols',
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            corr_coef = latest_filtered['temperature_celsius'].corr(latest_filtered['humidity'])
            fig_corr.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=450,
                title=f'Correlation: r = {corr_coef:.3f}',
                xaxis_title='Temperature (°C)',
                yaxis_title='Humidity (%)'
            )
            st.plotly_chart(fig_corr, use_container_width=True)

        with col_right:
            st.markdown("### 📊 Humidity Distribution")

            humidity_dist = pd.cut(
                latest_filtered['humidity'],
                bins=[0, 30, 60, 80, 100],
                labels=['Dry (<30%)', 'Moderate (30-60%)', 'Humid (60-80%)', 'Very Humid (>80%)']
            ).value_counts()

            fig_hum_dist = go.Figure(data=[go.Bar(
                x=humidity_dist.index,
                y=humidity_dist.values,
                marker_color=['#4DB6AC', '#81C784', '#FFB74D', '#E57373']
            )])
            fig_hum_dist.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=450,
                xaxis_title='Humidity Category',
                yaxis_title='Number of Locations',
                xaxis_tickangle=-45
            )
            st.plotly_chart(fig_hum_dist, use_container_width=True)

        # Air Quality Section
        st.markdown("---")
        st.markdown("## 🌬️ Air Quality Analytics")

        col1, col2, col3, col4, col5, col6 = st.columns(6)

        aqi_metrics = {
            'PM2.5': 'air_quality_PM2.5',
            'PM10': 'air_quality_PM10',
            'CO': 'air_quality_Carbon_Monoxide',
            'Ozone': 'air_quality_Ozone',
            'NO₂': 'air_quality_Nitrogen_dioxide',
            'SO₂': 'air_quality_Sulphur_dioxide'
        }

        cols = [col1, col2, col3, col4, col5, col6]
        for (name, col_name), col in zip(aqi_metrics.items(), cols):
            with col:
                avg_val = latest_filtered[col_name].mean()
                st.markdown(f"""
                <div style='background: linear-gradient(135deg, #37474F 0%, #263238 100%);
                            border-radius: 8px; padding: 15px; text-align: center;'>
                    <div style='color: #B0BEC5; font-size: 0.8em;'>{name}</div>
                    <div style='color: #4DB6AC; font-size: 1.5em; font-weight: bold;'>{avg_val:.1f}</div>
                    <div style='color: #B0BEC5; font-size: 0.7em;'>μg/m³</div>
                </div>
                """, unsafe_allow_html=True)

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown("### 🎯 Air Quality Component Radar")

            aqi_avg = latest_filtered[list(aqi_metrics.values())].mean()
            fig_radar = go.Figure(data=go.Scatterpolar(
                r=aqi_avg.values.tolist() + [aqi_avg.values[0]],
                theta=list(aqi_metrics.keys()) + [list(aqi_metrics.keys())[0]],
                fill='toself',
                fillcolor='rgba(77, 182, 172, 0.3)',
                line=dict(color='#4DB6AC', width=2)
            ))
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, max(aqi_avg.values) * 1.2]),
                    bgcolor='rgba(0,0,0,0)'
                ),
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                height=400,
                showlegend=False
            )
            st.plotly_chart(fig_radar, use_container_width=True)

        with col_right:
            st.markdown("### 📋 EPA Air Quality Index Distribution")

            aqi_dist = latest_filtered['aqi_status'].value_counts()
            aqi_colors = {
                'Good': '#4DB6AC',
                'Moderate': '#FFCA28',
                'Unhealthy for Sensitive': '#FF9800',
                'Unhealthy': '#E57373'
            }
            fig_aqi = go.Figure(data=[go.Bar(
                x=aqi_dist.index,
                y=aqi_dist.values,
                marker_color=[aqi_colors.get(x, '#4DB6AC') for x in aqi_dist.index]
            )])
            fig_aqi.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=400,
                xaxis_title='AQI Category',
                yaxis_title='Number of Locations'
            )
            st.plotly_chart(fig_aqi, use_container_width=True)

        # Combo Chart: Humidity + Precipitation
        st.markdown("### 🌧️ Humidity & Precipitation Correlation")

        country_agg = latest_filtered.groupby('country').agg({
            'humidity': 'mean',
            'precip_mm': 'mean',
            'temperature_celsius': 'mean'
        }).reset_index().sort_values('humidity', ascending=False).head(20)

        fig_combo = make_subplots(specs=[[{"secondary_y": True}]])
        fig_combo.add_trace(
            go.Bar(
                x=country_agg['country'],
                y=country_agg['humidity'],
                name='Humidity (%)',
                marker_color='#4DB6AC',
                opacity=0.7
            ),
            secondary_y=False
        )
        fig_combo.add_trace(
            go.Scatter(
                x=country_agg['country'],
                y=country_agg['precip_mm'],
                name='Precipitation (mm)',
                mode='lines+markers',
                line=dict(color='#FFCA28', width=3),
                marker=dict(size=8)
            ),
            secondary_y=True
        )
        fig_combo.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400,
            xaxis_tickangle=-45,
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        fig_combo.update_yaxes(title_text="Humidity (%)", secondary_y=False)
        fig_combo.update_yaxes(title_text="Precipitation (mm)", secondary_y=True)
        st.plotly_chart(fig_combo, use_container_width=True)

    # =============================================================================
    # TAB 3: WIND & PRECIPITATION
    # =============================================================================
    with tab3:
        st.markdown("## 🌪️ Wind Patterns & Precipitation Analytics")

        # Wind KPIs
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            avg_wind = latest_filtered['wind_kph'].mean()
            st.markdown(f"""
            <div class='metric-card'>
                <div class='kpi-label'>Avg Wind Speed</div>
                <div class='kpi-value'>{avg_wind:.1f}</div>
                <div style='color: #B0BEC5; font-size: 0.8em;'>km/h</div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            prevailing_dir = latest_filtered['wind_direction'].mode().iloc[0] if not latest_filtered.empty else 'N/A'
            st.markdown(f"""
            <div class='metric-card'>
                <div class='kpi-label'>Prevailing Direction</div>
                <div class='kpi-value' style='font-size: 2em;'>{prevailing_dir}</div>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            avg_precip = latest_filtered['precip_mm'].mean()
            st.markdown(f"""
            <div class='metric-card'>
                <div class='kpi-label'>Avg Precipitation</div>
                <div class='kpi-value'>{avg_precip:.2f}</div>
                <div style='color: #B0BEC5; font-size: 0.8em;'>mm per location</div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            high_wind_count = len(latest_filtered[latest_filtered['wind_kph'] > 40])
            st.markdown(f"""
            <div class='alert-card'>
                <div class='kpi-label'>Wind Alerts</div>
                <div class='kpi-value' style='color: #FFCA28;'>{high_wind_count}</div>
                <div style='color: #B0BEC5; font-size: 0.8em;'>High wind events</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        col_left, col_right = st.columns([1, 1])

        with col_left:
            st.markdown("### 🧭 Wind Rose Chart")

            wind_dir_order = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                              'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
            wind_dist = latest_filtered['wind_direction'].value_counts().reindex(wind_dir_order, fill_value=0)
            wind_speed_by_dir = latest_filtered.groupby('wind_direction')['wind_kph'].mean().reindex(wind_dir_order, fill_value=0)

            fig_wind = go.Figure(go.Barpolar(
                r=wind_dist.values,
                theta=wind_dist.index,
                marker_color=wind_speed_by_dir.values,
                marker_colorscale='Teal',
                opacity=0.8
            ))
            fig_wind.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                polar=dict(
                    radialaxis=dict(
                        showline=False,
                        showticklabels=False,
                        ticks='',
                        range=[0, wind_dist.max() * 1.2]
                    ),
                    bgcolor='rgba(0,0,0,0)'
                ),
                height=450
            )
            st.plotly_chart(fig_wind, use_container_width=True)

        with col_right:
            st.markdown("### 📊 Wind Speed Categories")

            wind_cat_dist = latest_filtered['wind_category'].value_counts()
            fig_wind_cat = go.Figure(data=[go.Bar(
                x=wind_cat_dist.index,
                y=wind_cat_dist.values,
                marker_color=['#4DB6AC', '#81C784', '#FFB74D', '#FF9800', '#E57373', '#B71C1C']
            )])
            fig_wind_cat.update_layout(
                template='plotly_dark',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                height=450,
                xaxis_title='Wind Category',
                yaxis_title='Count',
                xaxis_tickangle=-30
            )
            st.plotly_chart(fig_wind_cat, use_container_width=True)

        # Precipitation Intensity by Region
        st.markdown("### 🌧️ Precipitation Intensity by Region")

        precip_by_region = latest_filtered.groupby('continent')['precip_mm'].agg(['mean', 'max', 'sum']).reset_index()

        fig_precip = go.Figure()
        fig_precip.add_trace(go.Bar(
            name='Average',
            x=precip_by_region['continent'],
            y=precip_by_region['mean'],
            marker_color='#4DB6AC'
        ))
        fig_precip.add_trace(go.Scatter(
            name='Maximum',
            x=precip_by_region['continent'],
            y=precip_by_region['max'],
            mode='markers',
            marker=dict(color='#FFCA28', size=12, symbol='diamond')
        ))
        fig_precip.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400,
            barmode='group',
            xaxis_title='Continent',
            yaxis_title='Precipitation (mm)',
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
        )
        st.plotly_chart(fig_precip, use_container_width=True)

        # Wind vs Precipitation Correlation
        st.markdown("### 🔄 Wind vs Precipitation Correlation")

        fig_wind_precip = px.scatter(
            latest_filtered,
            x="wind_kph",
            y="precip_mm",
            size="viz_size",
            color="humidity",
            hover_name="location_name",
            hover_data={
                "viz_size": False,
                "temperature_celsius": True,
                "country": True
            },
            template='plotly_dark'
        )
        wind_precip_corr = latest_filtered['wind_kph'].corr(latest_filtered['precip_mm'])
        fig_wind_precip.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=450,
            title=f'Correlation: r = {wind_precip_corr:.3f}',
            xaxis_title='Wind Speed (km/h)',
            yaxis_title='Precipitation (mm)'
        )
        st.plotly_chart(fig_wind_precip, use_container_width=True)

    # =============================================================================
    # TAB 4: GEOGRAPHIC PATTERNS
    # =============================================================================
    with tab4:
        st.markdown("## 🗺️ Geographic Weather Pattern Explorer")

        map_type = st.radio(
            "Select Map Visualization",
            ["Bubble Map (Temperature)", "Heat Map (AQI)", "Wind Direction Map"],
            horizontal=True
        )

        if map_type == "Bubble Map (Temperature)":
            st.markdown("### 🌡️ Temperature Bubble Map")

            fig_map = px.scatter_geo(
                latest_filtered,
                lat='latitude',
                lon='longitude',
                color='temperature_celsius',
                size='viz_size',
                hover_name='country',
                hover_data={
                    'viz_size': False,
                    'temperature_celsius': True,
                    'humidity': True,
                    'wind_kph': True
                },
                color_continuous_scale='RdYlBu_r',
                projection='natural earth',
                template='plotly_dark',
                title='Global Temperature Distribution (Marker size relative to heat)'
            )
            fig_map.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                geo=dict(
                    bgcolor='rgba(0,0,0,0)',
                    showland=True,
                    landcolor='#37474F',
                    showocean=True,
                    oceancolor='#1A1D21',
                    showcoastlines=True,
                    coastlinecolor='#4DB6AC'
                ),
                height=600
            )
            st.plotly_chart(fig_map, use_container_width=True)

        elif map_type == "Heat Map (AQI)":
            st.markdown("### 🌬️ Air Quality Index Heat Map")

            fig_heat = px.density_mapbox(
                latest_filtered,
                lat='latitude',
                lon='longitude',
                z='air_quality_us-epa-index',
                radius=20,
                center=dict(lat=20, lon=0),
                zoom=1,
                mapbox_style='carto-darkmatter',
                color_continuous_scale='YlOrRd',
                title='Air Quality Hotspots'
            )
            fig_heat.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                height=600
            )
            st.plotly_chart(fig_heat, use_container_width=True)

        else:  # Wind Direction Map
            st.markdown("### 🧭 Wind Direction & Speed Map")

            latest_filtered['wind_u'] = -latest_filtered['wind_kph'] * np.sin(np.radians(latest_filtered['wind_degree']))
            latest_filtered['wind_v'] = -latest_filtered['wind_kph'] * np.cos(np.radians(latest_filtered['wind_degree']))

            fig_wind_map = px.scatter_geo(
                latest_filtered,
                lat='latitude',
                lon='longitude',
                color='wind_kph',
                size='wind_kph',
                hover_name='country',
                hover_data=['wind_kph', 'wind_direction', 'wind_degree'],
                color_continuous_scale='Viridis',
                projection='natural earth',
                template='plotly_dark',
                title='Global Wind Patterns'
            )
            fig_wind_map.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                geo=dict(
                    bgcolor='rgba(0,0,0,0)',
                    showland=True,
                    landcolor='#37474F',
                    showocean=True,
                    oceancolor='#1A1D21'
                ),
                height=600
            )
            st.plotly_chart(fig_wind_map, use_container_width=True)

        # Regional Comparison Bar Chart
        st.markdown("---")
        st.markdown("### 📊 Regional Temperature Comparison")

        region_stats = latest_filtered.groupby('continent').agg({
            'temperature_celsius': 'mean',
            'humidity': 'mean',
            'wind_kph': 'mean',
            'air_quality_us-epa-index': 'mean'
        }).reset_index()

        fig_3d = go.Figure(data=[go.Bar(
            x=region_stats['continent'],
            y=region_stats['temperature_celsius'],
            text=region_stats['temperature_celsius'].round(1),
            textposition='auto',
            marker=dict(
                color=region_stats['temperature_celsius'],
                colorscale='Teal',
                showscale=True
            )
        )])
        fig_3d.update_layout(
            template='plotly_dark',
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            height=400,
            xaxis_title='Continent',
            yaxis_title='Average Temperature (°C)',
            title='Regional Temperature Comparison'
        )
        st.plotly_chart(fig_3d, use_container_width=True)

        # Weather Condition Matrix
        st.markdown("### 📋 Weather Condition Matrix by Region")

        matrix_data = latest_filtered.groupby('continent').agg({
            'temperature_celsius': 'mean',
            'wind_kph': 'mean',
            'precip_mm': 'sum',
            'humidity': 'mean',
            'air_quality_us-epa-index': 'mean'
        }).round(2).reset_index()

        st.dataframe(
            matrix_data,
            use_container_width=True,
            hide_index=True,
            column_config={
                'continent': 'Continent',
                'temperature_celsius': st.column_config.NumberColumn('Avg Temp (°C)', format='%.1f'),
                'wind_kph': st.column_config.NumberColumn('Avg Wind (km/h)', format='%.1f'),
                'precip_mm': st.column_config.NumberColumn('Total Precip (mm)', format='%.1f'),
                'humidity': st.column_config.NumberColumn('Avg Humidity (%)', format='%.1f'),
                'air_quality_us-epa-index': st.column_config.NumberColumn('Avg AQI', format='%.1f')
            }
        )

    # =============================================================================
    # SIDEBAR EXPORT
    # =============================================================================
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📥 Export Data")

    csv = latest_filtered.to_csv(index=False).encode('utf-8')
    st.sidebar.download_button(
        label="Download Filtered Data (CSV)",
        data=csv,
        file_name=f'climate_data_{datetime.now().strftime("%Y%m%d")}.csv',
        mime='text/csv'
    )

else:
    st.error("""
    ## ❌ Data Loading Failed

    Please ensure:
    1. The file `global_weather_clean.csv` is in the same directory as this script
    2. The CSV file is not corrupted
    3. You have read permissions for the file

    **Expected file location:** Same directory as `climate_scope_dashboard.py`
    """)
