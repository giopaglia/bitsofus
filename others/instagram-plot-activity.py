import os
import json
import matplotlib.pyplot as plt
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Access environment variables
INSTAGRAM_BASE_DIR = os.getenv('INSTAGRAM_BASE_DIR')


# === Carica il file JSON ===
with open(INSTAGRAM_BASE_DIR + "/your_instagram_activity/other_activity/time_spent_on_instagram.json", 'r') as f:
	data = json.load(f)

# === Estrai tutti gli intervalli start-end ===
intervals = []

for entry in data:
	label_values = entry.get('label_values', [])
	for label in label_values:
		if label.get('label') == 'Intervals':
			for vec in label.get('vec', []):
				start_time = None
				end_time = None
				for d in vec.get('dict', []):
					if d.get('label') == 'Start time':
						start_time = d.get('timestamp_value')
					if d.get('label') == 'End time':
						end_time = d.get('timestamp_value')
				if start_time and end_time:
					intervals.append((start_time, end_time))

# === Crea un DataFrame per lavorare meglio ===
records = []

for start, end in intervals:
	start_dt = datetime.fromtimestamp(start)
	end_dt = datetime.fromtimestamp(end)
	duration_sec = end - start
	records.append({
		'start_time': start_dt,
		'end_time': end_dt,
		'duration_seconds': duration_sec
	})

df = pd.DataFrame(records)
df['date'] = df['start_time'].dt.date
df['weekday'] = df['start_time'].dt.strftime('%A')
df['hour'] = df['start_time'].dt.hour

# === Facciamo dei plot ===

# 1. Tempo speso per giorno
daily_time = df.groupby('date')['duration_seconds'].sum() / 60  # minuti
plt.figure(figsize=(10,5))
daily_time.plot(kind='bar')
plt.ylabel('Tempo su Instagram (minuti)')
plt.title('Tempo speso su Instagram per giorno')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

# 2. Distribuzione degli accessi per ora del giorno
plt.figure(figsize=(10,5))
df['hour'].value_counts().sort_index().plot(kind='bar')
plt.xlabel('Ora del giorno')
plt.ylabel('Numero di sessioni')
plt.title('Distribuzione degli accessi su Instagram per ora del giorno')
plt.xticks(rotation=0)
plt.tight_layout()
plt.show()

# 3. Tempo medio per sessione
mean_session_time = df['duration_seconds'].mean() / 60  # minuti
print(f"Tempo medio per sessione: {mean_session_time:.2f} minuti")

# 4. Tempo speso per giorno della settimana
weekly_time = df.groupby('weekday')['duration_seconds'].sum()
weekday_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']

plt.figure(figsize=(10,5))
weekly_time.reindex(weekday_order).plot(kind='bar')
plt.ylabel('Tempo totale su Instagram (secondi)')
plt.title('Tempo speso su Instagram per giorno della settimana')
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()
