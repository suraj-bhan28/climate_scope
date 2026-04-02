
ClimateScope is a weather data analysis project created during the Infosys Springboard Internship.  
The project focuses on preparing global weather data for analysis and visualization.

## Dataset
Global Weather Repository (provided by mentor)

## Milestone 1 – Data Preparation
Completed tasks:
- Loaded dataset using pandas
- Inspected dataset structure
- Handled missing values
- Removed duplicate rows
- Converted `last_updated` to datetime
- Created cleaned dataset
- Aggregated data monthly

## Output Files
- data/processed/cleaned_weather.csv
- data/processed/monthly_weather.csv

## Tools Used
Python, Pandas, VS Code


## Milestone 2 – Core Analysis & Visualization Design

Completed tasks:
- Generated statistical summary using `df.describe()`
- Analyzed temperature distribution using histogram
- Calculated monthly average temperature using resampling
- Visualized monthly temperature trend using line plot
- Created correlation matrix for key weather variables
- Generated heatmap to study relationships between variables
- Identified extreme weather events:
  - Extreme heat (> 40°C)
  - Extreme cold (< -10°C)
  - High wind (> 60 kph)
- Compared average temperature across countries
- Identified Top 5 hottest and Top 5 coldest countries

Output:
- Statistical summary report (console output)
- Temperature distribution plot
- Monthly temperature trend plot
- Correlation heatmap
- Extreme weather event counts
- Country-wise temperature comparison

Tools Used:
Python, Pandas, Matplotlib, Seaborn


