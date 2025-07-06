import os
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access environment variables
INSTAGRAM_BASE_DIR = os.getenv('INSTAGRAM_BASE_DIR')


# === Carica il file dei commenti ===
with open(INSTAGRAM_BASE_DIR + "/your_instagram_activity/comments/post_comments_1.json", 'r') as f:
	comments = json.load(f)

# === Estrai i dati ===
records = []
for entry in comments:
	comment_data = entry['string_map_data']
	comment_text = comment_data['Comment']['value']
	media_owner = None
	if "Media Owner" in comment_data.keys():
		media_owner = comment_data['Media Owner']['value']
	timestamp = comment_data['Time']['timestamp']

	records.append({
		'comment': comment_text,
		'media_owner': media_owner,
		'timestamp': datetime.fromtimestamp(timestamp),
	})

df = pd.DataFrame(records)
df['date'] = df['timestamp'].dt.date

# === Colori consistenti per media_owner ===
unique_owners = df['media_owner'].unique()
colors = {owner: px.colors.qualitative.Plotly[i % len(px.colors.qualitative.Plotly)] for i, owner in enumerate(unique_owners)}

# === Plot 1: Numero di commenti nel tempo ===
fig1 = px.histogram(
	df,
	x="date",
	color="media_owner",
	color_discrete_map=colors,
	barmode="group",
	title="Numero di commenti nel tempo",
	labels={"date": "Data", "count": "Numero di commenti"}
)

# === Aggiungi slider per bargap ===
fig1.update_layout(
	bargap=0.1,
	updatemenus=[
		{
			"buttons": [
				{"args": [{"bargap": g}], "label": f"{g:.2f}", "method": "relayout"}
				for g in [0.05, 0.1, 0.2, 0.3, 0.5]
			],
			"direction": "left",
			"pad": {"r": 10, "t": 10},
			"showactive": True,
			"type": "buttons",
			"x": 0.0,
			"xanchor": "left",
			"y": 1.15,
			"yanchor": "top",
			"bgcolor": "lightgray",
			"bordercolor": "gray",
			"borderwidth": 1
		}
	]
)

# === Plot 2: Media Owner più commentati ===
owner_counts = df['media_owner'].value_counts().reset_index()
owner_counts.columns = ['media_owner', 'num_comments']

fig2 = px.bar(
	owner_counts,
	x="media_owner",
	y="num_comments",
	color="media_owner",
	color_discrete_map=colors,
	title="Numero di commenti per Media Owner",
	labels={"media_owner": "Utente", "num_comments": "Numero di commenti"}
)

fig2.update_layout(bargap=0.2)

# === Mostra i plot ===
fig1.show()
fig2.show()
