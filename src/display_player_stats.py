from load_data import load_and_filter_data, load_and_prepare_data
import os
import pandas as pd
import numpy as np
import streamlit as st
from typing import Optional, List, Union


def display_player_stats(player_data, player_type):
    team_colors = load_team_colors()
    id_to_name = player_data.groupby('IDfg').apply(lambda x: f"{x['Name'].iloc[0]} ({x['year'].min()}-{x['year'].max()})").to_dict()
    player_data = player_data.sort_values(['IDfg', 'year'])

    # Define stat order for pitchers and hitters
    pitcher_stat_order = ['WAR', 'W', 'L', 'ERA', 'G', 'GS', 'IP', 'AVG' 'WHIP', 'FIP', 'CG', 'ShO', 'SV', 'K/9', 'BB/9', 'K/BB', 'H/9', 'HR/9', 'BS', 'TBF', 'H', 'R', 'HR', 'SO', 'BB', 'IBB', 'HBP', 'WP', 'BK', 'GB%', 'FB%', 'LD%', 'IFH', 'IFFB', 'Balls', 'Strikes', 'Pitches']
    hitter_stat_order = ['WAR', 'G', 'AB', 'PA', 'H', '1B', '2B', '3B', 'HR', 'R', 'RBI', 'AVG', 'OBP', 'SLG', 'OPS', 'BB', 'SO', 'HBP', 'SF', 'SH', 'GDP', 'SB', 'CS', 'GB', 'FB', 'BB%', 'K%', 'BB/K', 'ISO']

    stat_order = pitcher_stat_order if player_type == "Pitcher" else hitter_stat_order

    # Define rate stats (stats that should be averaged instead of summed)
    rate_stats = ['AVG', 'OBP', 'SLG', 'OPS', 'BB%', 'K%', 'ISO', 'BABIP', 'wRC+', 'wOBA', 'ERA', 'WHIP', 'K/9', 'BB/9', 'H/9','HR/9', 'K/BB', 'FIP', 'xFIP']

    st.header("Career Summary")
    for idfg in player_data['IDfg'].unique():
        player_career = player_data[player_data['IDfg'] == idfg]
        player_name = id_to_name[idfg]
        st.write(f"{player_name}: {player_career['year'].min()} - {player_career['year'].max()} ({len(player_career)} seasons)")

    st.header("Career Stats")
    career_stats = player_data.groupby('IDfg').agg(
        {col: 'mean' if col in rate_stats else 'sum' 
         for col in player_data.select_dtypes(include=['int64', 'float64']).columns 
         if col not in ['year', 'IDfg']}
    )
    career_stats['Name'] = career_stats.index.map(id_to_name)

    if 'Age' in career_stats.columns:
        age_col = career_stats.pop('Age')
        career_stats['Age'] = age_col

    career_stats = career_stats.reset_index().set_index(['Name', 'IDfg'])

    # Reorder columns based on stat_order
    ordered_cols = [col for col in stat_order if col in career_stats.columns]
    other_cols = [col for col in career_stats.columns if col not in ordered_cols and col not in ['Name', 'IDfg']]
    career_stats = career_stats[ordered_cols + other_cols]

    # Function to format numbers while preserving original precision
    def format_number(x):
        if isinstance(x, int):
            return f"{x}"
        elif isinstance(x, float):
            if x.is_integer():
                return f"{int(x)}"
            else:
                return f"{x:.3f}"
        return x

    st.dataframe(career_stats.applymap(format_number))

    st.header("Yearly Stats")
    yearly_stats = player_data.copy()
    yearly_stats['Name'] = yearly_stats['IDfg'].map(id_to_name)

    # Remove the 'season' column if it exists
    if 'season' in yearly_stats.columns:
        yearly_stats = yearly_stats.drop('season', axis=1)

    # Define the new order for the first few columns
    first_cols = ['Name', 'IDfg', 'year', 'Age', 'Team', 'WAR']

    # Reorder columns for yearly stats
    ordered_cols = first_cols + [col for col in stat_order if col in yearly_stats.columns and col not in first_cols]
    other_cols = [col for col in yearly_stats.columns if col not in ordered_cols]
    yearly_stats = yearly_stats[ordered_cols + other_cols]

    formatted_yearly_stats = yearly_stats.applymap(format_number)
    st.dataframe(formatted_yearly_stats.set_index(['Name', 'IDfg', 'year']))

    st.header("Stat Explorer")
    numeric_columns = player_data.select_dtypes(include=['int64', 'float64']).columns
    stat_options = [col for col in numeric_columns if col not in ['year', 'IDfg']]
    
    # Determine default stat based on player type
    if player_type == "Pitcher":
        default_stat = 'ERA' if 'ERA' in stat_options else stat_options[0]
    else:
        default_stat = 'HR' if 'HR' in stat_options else stat_options[0]

    selected_stat = st.selectbox("Choose a stat to visualize:", stat_options, index=stat_options.index(default_stat))

    # Season-by-season plot
    fig = px.line(player_data, x='year', y=selected_stat, color='IDfg', 
                  title=f"Yearly {selected_stat}",
                  hover_data={'IDfg': False, 'Name': True, selected_stat: ':.2f'})

    fig.update_traces(hovertemplate='Name: %{customdata[0]}<br>Year: %{x}<br>' + f'{selected_stat}: ' + '%{y:.2f}<extra></extra>')

    for trace in fig.data:
        idfg = int(trace.name)
        player_subset = player_data[player_data['IDfg'] == idfg]
        if not player_subset.empty:
            player_info = player_subset.iloc[-1]
            trace.name = player_info['Name']
            trace.line.color = get_team_color(player_info['Team'], team_colors)
            trace.customdata = player_subset[['Name']]
        else:
            trace.name = f"Unknown Player (ID: {idfg})"
            trace.line.color = 'grey'
            trace.customdata = np.full((len(trace.x), 1), f"Unknown Player (ID: {idfg})")
    
    st.plotly_chart(fig)

    # Calculate cumulative stats or career average for rate stats
    career_data = []
    for idfg, group in player_data.groupby('IDfg'):
        group = group.sort_values('year')
        group['career_year'] = range(1, len(group) + 1)
        
        if selected_stat in rate_stats:
            if player_type == "Pitcher":
                weight = 'IP'
            else:  # Hitter
                weight = 'PA' if 'PA' in group.columns else 'G'
            
            group[f'Career_Avg_{selected_stat}'] = (group[selected_stat] * group[weight]).cumsum() / group[weight].cumsum()
            title = f"Yearly Career Average {selected_stat}"
            y_axis = f'Career_Avg_{selected_stat}'
        else:
            group[f'Cumulative_{selected_stat}'] = group[selected_stat].cumsum()
            title = f"Cumulative {selected_stat} Over Career"
            y_axis = f'Cumulative_{selected_stat}'
        
        career_data.append(group)

    career_df = pd.concat(career_data)

    # Create the figure with custom hover template
    fig_career = px.line(career_df, x='career_year', y=y_axis, 
                         color='IDfg',
                         title=title,
                         labels={'career_year': 'Career Year'},
                         hover_data={'IDfg': False, 'Name': True, y_axis: ':.2f'})

    # Update hover template to show player name
    fig_career.update_traces(hovertemplate='Name: %{customdata[0]}<br>Career Year: %{x}<br>' + f'{y_axis}: ' + '%{y:.2f}<extra></extra>')

    # Customize the lines for each player
    for trace in fig_career.data:
        idfg = int(trace.name)
        player_subset = career_df[career_df['IDfg'] == idfg]
        if not player_subset.empty:
            player_info = player_subset.iloc[-1]
            trace.name = player_info['Name']
            trace.line.color = get_team_color(player_info['Team'], team_colors)
            # Add custom data for hover
            trace.customdata = player_subset[['Name']]
        else:
            trace.name = f"Unknown Player (ID: {idfg})"
            trace.line.color = 'grey'
            trace.customdata = np.full((len(trace.x), 1), f"Unknown Player (ID: {idfg})")

    st.plotly_chart(fig_career)

    if selected_stat in rate_stats:
        st.info(f"{selected_stat} is a rate stat, so the second graph shows the career average at each point in time.")
    else:
        st.info(f"{selected_stat} is a counting stat, so the second graph shows cumulative values over time.")