import os
import json
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access environment variables
INSTAGRAM_BASE_DIR = os.getenv('INSTAGRAM_BASE_DIR')

# === Carica il file della conversazione ===
with open(INSTAGRAM_BASE_DIR + "/your_instagram_activity/messages/inbox/annachiarazagati_534061071315123/message_1.json", 'r') as f:
	chat = json.load(f)

# === Estrai messaggi ===
messages = chat['messages']
participants = [p['name'] for p in chat['participants']]

# === Prepara un DataFrame ===
records = []

for msg in messages:
	sender = msg.get('sender_name')
	timestamp = msg.get('timestamp_ms')
	content = msg.get('content', '')  # alcuni messaggi sono attachment

	if timestamp and sender:
		records.append({
			'sender': sender,
			'timestamp': datetime.fromtimestamp(timestamp / 1000),  # ms -> s
			'content': content
		})

df = pd.DataFrame(records)
df['date'] = df['timestamp'].dt.date
df['hour'] = df['timestamp'].dt.hour

# === Palette di colori consistenti ===
colors = {
	participants[0]: '#1f77b4',  # Blu
	participants[1]: '#ff7f0e'   # Arancione
}

# # === Plot 1: Numero di messaggi per giorno (INTERATTIVO) ===
# fig = px.histogram(
#     df, 
#     x="date", 
#     color="sender",
#     color_discrete_map=colors,
#     barmode="stack",
#     title="Numero di messaggi per giorno",
#     labels={"date": "Data", "count": "Numero di messaggi"}
# )
# fig.update_layout(bargap=0.2)
# fig.show()

# === Figura di base ===
fig = px.histogram(
	df, 
	x="date", 
	color="sender",
	color_discrete_map=colors,
	barmode="stack",
	title="Numero di messaggi per giorno",
	labels={"date": "Data", "count": "Numero di messaggi"}
)

# === Aggiunta slider per il bargap ===
fig.update_layout(
	bargap=0.1,  # valore iniziale
	updatemenus=[
		{
			"buttons": [
				{
					"args": [{"bargap": g}],
					"label": f"{g:.2f}",
					"method": "relayout"
				}
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

fig.show()

# === Plot 2: Totale messaggi inviati da ciascuno (STATICO) ===
plt.figure(figsize=(6,6))
df['sender'].value_counts().plot(
	kind='pie', 
	autopct='%1.1f%%', 
	startangle=140, 
	colors=[colors[name] for name in df['sender'].unique()]
)
plt.title('Percentuale di messaggi inviati')
plt.ylabel('')
plt.tight_layout()
plt.show()

# === Plot 3: Attività per ora del giorno (STATICO) ===
plt.figure(figsize=(12,6))
df.groupby(['hour', 'sender']).size().unstack(fill_value=0).plot(
	kind='bar', 
	stacked=True, 
	width=0.8,
	color=[colors[name] for name in df['sender'].unique()]
)
plt.title('Distribuzione dei messaggi per ora del giorno')
plt.ylabel('Messaggi')
plt.xlabel('Ora')
plt.xticks(rotation=0)
plt.tight_layout()
plt.show()

# === Statistica bonus ===
print(f"\nNumero totale di messaggi: {len(df)}")
print(df['sender'].value_counts())
