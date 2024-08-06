import os
import streamlit as st

@st.cache_data
def load_team_colors():
    team_colors = {}
    # Get the directory of the current script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Construct the path to the data file
    file_path = os.path.join(script_dir, 'data', 'team_colors.txt')
    
    try:
        with open(file_path, 'r') as file:
            for line in file:
                team, color = line.strip().split(': ')
                team_colors[team.upper()] = color
    except FileNotFoundError:
        st.error(f"Could not find the file: {file_path}")
        st.error(f"Current working directory: {os.getcwd()}")
        st.error(f"Contents of current directory: {os.listdir()}")
        st.error(f"Contents of 'data' directory: {os.listdir(os.path.join(script_dir, 'data'))}")
    return team_colors

def get_team_color(team, team_colors=None):
    if team_colors is None:
        team_colors = load_team_colors()
    return team_colors.get(str(team).upper(), 'grey')