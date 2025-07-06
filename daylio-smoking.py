import os
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import mplcursors
import re
from statsmodels.graphics.tsaplots import plot_acf
import config

# Load data
df = pd.read_csv(os.path.join(os.getenv('DAYLIO_BASE_DIR'), "daylio_export_2025_07_03.csv"))

# Directory di salvataggio
OUTPUT_DIR = Path(os.path.join(os.getenv('TARGET_DIR', './takeout-downloaded'), "daylio-smoking"))
os.makedirs(OUTPUT_DIR, exist_ok=True)


# Function to parse an individual token
def parse_token(token):
	"""
	Converts a single token to a numeric value if possible.
	For example:
	- '1/2' => 0.5
	- '6+'  => 6
	- '2'   => 2
	Otherwise returns None.
	"""
	token = token.strip()
	if re.match(r'^\d+/\d+$', token):
		num, denom = token.split("/")
		return float(num) / float(denom)
	elif re.match(r'^\d+\+$', token):
		return int(token[:-1])
	elif re.match(r'^\d+$', token):
		return int(token)
	else:
		return None

# Function to parse the 'activities' column
def parse_entry(entry):
	"""
	Parses the entire string like '1/2 | 2 | party'
	and sums all numeric quantities.
	"""
	if pd.isnull(entry):
		return 0
	tokens = entry.split("|")
	total = 0
	for token in tokens:
		val = parse_token(token)
		if val is not None:
			total += val
	return total


####################################################################################################
####################################################################################################
####################################################################################################
# # PREPROCESSING: note that this duplicates lines.
# # Split 'activities' by '|' and explode into separate rows
# df['activities'] = df['activities'].fillna('')  # replace NaN with empty string
# df['activities'] = df['activities'].astype(str)

# # Split by '|' (and strip spaces)
# df['activities_list'] = df['activities'].apply(lambda x: [a.strip() for a in x.split('|') if a.strip()])

# # Explode: creates one row per activity
# df = df.explode('activities_list').reset_index(drop=True)
df['activities_list'] = df['activities'].fillna('')  # replace NaN with empty string
####################################################################################################
####################################################################################################
####################################################################################################



# Apply parsing to the 'activities' column
df["cigarettes"] = df["activities_list"].apply(parse_entry)

# Convert full_date to datetime
df["full_date"] = pd.to_datetime(df["full_date"], errors="coerce")


# 1️⃣ Riempire giorni mancanti con 0 sigarette
df['full_date'] = pd.to_datetime(df['full_date'])
all_dates = pd.date_range(start=df['full_date'].min(), end=df['full_date'].max(), freq='D')
df_all = pd.DataFrame({'full_date': all_dates})
df = pd.merge(df_all, df, on='full_date', how='left')

# Normalizza valori non numerici (li useremo per le linee verticali)
df['cigarettes_str'] = df['cigarettes'].astype(str)
df['cigarettes_numeric'] = pd.to_numeric(df['cigarettes'], errors='coerce')

# 0 se non presente
df['cigarettes_numeric'] = df['cigarettes_numeric'].fillna(0).astype(float)

df0 = df

df = df0.groupby("full_date").agg(cigarettes_numeric=("cigarettes_numeric", "sum")).reset_index()
df = df0.sort_values("full_date").set_index("full_date")

def isfloat(x):
	x = str(x).strip()
	if x in ["6+", "1/2"]:
		return True
	try:
		float(x)
		return True
	except ValueError:
		return False

# Giorno della settimana e mese in inglese
df['weekday_name'] = df.index.day_name()
df['month_name'] = df.index.month_name()
df['day_of_month'] = df.index.day


# Print general statistics
print("General Statistics:")
print(df["cigarettes_numeric"].describe())

# 2️⃣ Distribuzione temporale - barplot
plt.figure(figsize=(14,6))
plt.bar(df.index, df['cigarettes_numeric'], width=0.8, color='skyblue', edgecolor='k')
plt.xlabel("Date")
plt.ylabel("Number of cigarettes")
plt.title("Cigarette count over time")
plt.axhline(6, color='red', linestyle='--', label='Cutoff: 6 cigarettes')
plt.legend()

# Flag per linee verticali con note
df0['note_marker'] = df0['activities_list'].apply(lambda x : not isfloat(x))

# Linee verticali con tooltip per valori non numerici
for _, row in df0[df0['note_marker']].iterrows():
	plt.axvline(row["full_date"], color='orange', linestyle='--', alpha=0.7)
	plt.text(row["full_date"], plt.ylim()[1]*0.8, row['cigarettes_str'],
			 rotation=90, color='orange', fontsize=8)

# Tooltip interattivo
mplcursors.cursor(hover=True)

plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "cigarettes_over_time.png"))
# plt.show()
plt.close()




# Moving averages with different windows
plt.figure(figsize=(15,5))
plt.plot(df.index, df["cigarettes_numeric"], label="Daily", alpha=0.2)
for window in [14,30,180]:
	rolling = df["cigarettes_numeric"].rolling(window=window, min_periods=1).mean()
	plt.plot(df.index, rolling, label=f"{window}-day MA")
plt.title("Moving Averages of Cigarettes per Day")
plt.xlabel("Date")
plt.ylabel("Number of Cigarettes")
plt.legend()
plt.grid()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "cigarettes_over_time_ma.png"))
plt.close()

# Histogram
plt.figure(figsize=(8,4))
sns.histplot(df["cigarettes_numeric"], bins=12, kde=True)
plt.title("Histogram of Cigarettes per Day")
plt.xlabel("Number of Cigarettes")
plt.ylabel("Frequency")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "cigarettes_per_day_histogram.png"))
plt.close()

# 3️⃣ Distribuzione per giorno della settimana - boxplot
plt.figure(figsize=(10,6))
sns.boxplot(
	x='weekday_name', y='cigarettes_numeric', data=df,
	order=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'],
	showmeans=True,
	meanprops={"marker":"D","markerfacecolor":"red","markeredgecolor":"black"}
)
plt.axhline(6, color='red', linestyle='--', label='Cutoff: 6 cigarettes')
plt.xlabel("Day of the week")
plt.ylabel("Number of cigarettes")
plt.title("Cigarettes by day of the week")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "cigarettes_by_weekday.png"))
plt.close()

# 4️⃣ Distribuzione per giorno del mese - boxplot
plt.figure(figsize=(12,6))
sns.boxplot(
	x='day_of_month', y='cigarettes_numeric', data=df,
	showmeans=True,
	meanprops={"marker":"D","markerfacecolor":"red","markeredgecolor":"black"}
)
plt.axhline(6, color='red', linestyle='--', label='Cutoff: 6 cigarettes')
plt.xlabel("Day of the month")
plt.ylabel("Number of cigarettes")
plt.title("Cigarettes by day of the month")
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "cigarettes_by_day_of_month.png"))
plt.close()

# 5️⃣ Distribuzione per mese - boxplot
plt.figure(figsize=(12,6))
sns.boxplot(
	x='month_name', y='cigarettes_numeric', data=df,
	order=[
		'January','February','March','April','May','June',
		'July','August','September','October','November','December'
	],
	showmeans=True,
	meanprops={"marker":"D","markerfacecolor":"red","markeredgecolor":"black"}
)
plt.axhline(6, color='red', linestyle='--', label='Cutoff: 6 cigarettes')
plt.xlabel("Month")
plt.ylabel("Number of cigarettes")
plt.title("Cigarettes by month")
plt.xticks(rotation=45)
plt.legend()
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "cigarettes_by_month.png"))
plt.close()



# Autocorrelation plot
plt.figure(figsize=(10,4))
plot_acf(df["cigarettes_numeric"], lags=30)
plt.title("Autocorrelation of Cigarettes per Day")
plt.tight_layout()
plt.savefig(os.path.join(OUTPUT_DIR, "cigarettes_autocorrelation.png"))
plt.close()
