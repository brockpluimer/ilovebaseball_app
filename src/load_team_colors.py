# Load team colors from the text file
@st.cache_data
def load_team_colors():
    team_colors = {}
    with open('team_colors.txt', 'r') as file:
        for line in file:
            team, color = line.strip().split(': ')
            team_colors[team.upper()] = color

def get_team_color(team, team_colors):
    return team_colors.get(str(team).upper(), 'grey')