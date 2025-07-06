#!/usr/bin/env python3
"""
Advanced YouTube Takeout Dashboard

Requirements:
	pip install pandas plotly wordcloud matplotlib numpy tqdm hurry.filesize pillow
"""

import os
import glob
import json
import re
from collections import Counter
from datetime import datetime
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from wordcloud import WordCloud
import matplotlib.pyplot as plt
from tqdm import tqdm
from hurry.filesize import size, alternative
from PIL import Image, PngImagePlugin
import matplotlib.cm as cm
import matplotlib.colors as mcolors
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


TARGET_DIR = os.path.join(os.getenv('TARGET_DIR', 'takeout-downloaded'), "youtube-dashboard")

TAKEOUT_DIRS = eval(os.getenv('GOOGLE_BASE_DIRS'))

# -------------------------
# Functions to load Takeout data
# -------------------------

def load_view_history(takeout_dirs):
	"""
	Load viewing history from all provided Takeout directories.
	Returns a DataFrame with columns: datetime, title, channel.
	"""
	records = []
	for td in takeout_dirs:
		files = glob.glob(os.path.join(td, "**", "*YouTube*", "**", "cronologia visualizzazioni.json"), recursive=True)
		for f in files:
			print(size(os.path.getsize(f), system=alternative), "\t", f)
			with open(f, "r", encoding="utf-8") as infile:
				data = json.load(infile)
				for entry in data:
					title = entry.get("title", "")
					time = entry.get("time", "")
					m = re.match(r"(?:You watched|Hai guardato|Hai visualizzato) (.+)", title)
					if m:
						query = m.group(1)
						dt = pd.to_datetime(time, errors="coerce")
						channel = None
						if "subtitles" in entry and entry["subtitles"]:
							channel = entry["subtitles"][0].get("name")
						records.append({"datetime": dt, "title": query, "channel": channel})
					else:
						print(f"Unknown title: {title}")
						# input()
	return pd.DataFrame(records)

def load_search_history(takeout_dirs):
	"""
	Load search history from all provided Takeout directories.
	Returns a DataFrame with columns: datetime, query.
	"""
	searches = []
	for td in takeout_dirs:
		files = glob.glob(os.path.join(td, "**", "*YouTube*", "**", "cronologia delle ricerche.json"), recursive=True)
		for f in files:
			print(size(os.path.getsize(f), system=alternative), "\t", f)
			with open(f, "r", encoding="utf-8") as infile:
				data = json.load(infile)
				for entry in data:
					title = entry.get("title", "")
					time = entry.get("time", "")
					# For some reason, we sometimes find "You watched" in the search history (idk why?)
					m = re.match(r"(?:You searched for|Hai cercato|You watched|Hai guardato) (.+)", title)
					if m:
						query = m.group(1)
						dt = pd.to_datetime(time, errors="coerce")
						searches.append({"datetime": dt, "query": query})
					else:
						print(f"Unknown title: {title}")
						# input()
	return pd.DataFrame(searches)

def make_wordcloud(words, title, outpath):
	"""
	Generate a wordcloud image from a list of words.
	Embeds the words as PNG metadata.
	"""
	# print(len(words))
	words = [
		w for w in words
		if not w.startswith("https://www.youtube.com/watch")
	]
	# print(len(words))
	text = " ".join(words)
	wc = WordCloud(width=800, height=400, background_color="white").generate(text)
	wc.to_file(outpath)
	img = Image.open(outpath)
	meta = PngImagePlugin.PngInfo()
	meta.add_text("Keywords", ", ".join(list(wc.words_.keys())))
	img.save(outpath, pnginfo=meta)

# -------------------------
# Main execution
# -------------------------

os.makedirs(TARGET_DIR, exist_ok=True)

print("📥 Loading viewing history...")
views_df = load_view_history(TAKEOUT_DIRS)
print("📥 Loading search history...")
searches_df = load_search_history(TAKEOUT_DIRS)

# Clean data
views_df = views_df.dropna(subset=["datetime"])
searches_df = searches_df.dropna(subset=["datetime"])

# Extract time fields
views_df["date"] = views_df["datetime"].dt.date
views_df["year"] = views_df["datetime"].dt.year
views_df["month_num"] = views_df["datetime"].dt.month
views_df["month_name"] = views_df["datetime"].dt.month_name()
views_df["day_of_week"] = views_df["datetime"].dt.day_name()
views_df["hour"] = views_df["datetime"].dt.hour

# -------------------------
# Visualizations
# -------------------------

# Daily timeline
timeline = views_df.groupby("date").size().reset_index(name="views")
fig_timeline = px.line(timeline, x="date", y="views", title="Daily Viewing Timeline")

# Monthly trend
views_df["month"] = views_df["datetime"].dt.to_period("M").dt.to_timestamp().dt.date
monthly_trend = views_df.groupby("month").size().reset_index(name="views")
fig_monthly = px.line(monthly_trend, x="month", y="views", title="Monthly Viewing Trend")

# Annual trend
annual_trend = views_df.groupby("year").size().reset_index(name="views")
fig_annual = px.bar(annual_trend, x="year", y="views", title="Annual Viewing Counts")

# Seasonality by year with consistent colors
month_order = [
	"January","February","March","April","May","June",
	"July","August","September","October","November","December"
]
years_sorted = np.sort(views_df["year"].unique())
norm = plt.Normalize(vmin=years_sorted.min(), vmax=years_sorted.max())
cmap = plt.get_cmap("viridis")

fig_seasonality = go.Figure()
for year in years_sorted:
	df_year = views_df[views_df["year"] == year].groupby("month_num").size().reindex(range(1,13), fill_value=0)
	color = mcolors.to_hex(cmap(norm(year)))
	fig_seasonality.add_trace(
		go.Scatter(
			x=list(range(1,13)),
			y=df_year.values,
			mode="lines+markers",
			name=str(year),
			line=dict(color=color),
			marker=dict(color=color)
		)
	)
fig_seasonality.update_layout(
	title="Monthly Seasonality per Year",
	xaxis=dict(
		tickmode="array",
		tickvals=list(range(1,13)),
		ticktext=month_order
	),
	yaxis=dict(title="Views")
)

# Aggregated monthly counts
aggregate_counts = (
	views_df.groupby("month_num").size().reset_index(name="views")
)
aggregate_counts["month_name"] = aggregate_counts["month_num"].apply(lambda x: month_order[x-1])
fig_aggregate = px.bar(
	aggregate_counts,
	x="month_name",
	y="views",
	title="Aggregate Monthly Views"
)

# Day-of-week distribution
categories = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
dow_counts = views_df["day_of_week"].value_counts().reindex(categories)
fig_dow = px.bar(
	x=dow_counts.index,
	y=dow_counts.values,
	title="Day-of-Week Distribution"
)

# Overall heatmap
heatmap_data = views_df.groupby(["day_of_week","hour"]).size().reset_index(name="count")
heatmap_data["day_of_week"] = pd.Categorical(heatmap_data["day_of_week"], categories)
fig_heatmap = px.density_heatmap(
	heatmap_data,
	x="hour",
	y="day_of_week",
	z="count",
	color_continuous_scale="Viridis",
	title="Hourly Viewing Heatmap (All Years)"
)

# Heatmaps per year
for y in years_sorted:
	df_y = views_df[views_df["year"]==y]
	heatmap_y = df_y.groupby(["day_of_week","hour"]).size().reset_index(name="count")
	heatmap_y["day_of_week"] = pd.Categorical(heatmap_y["day_of_week"], categories)
	fig_y = px.density_heatmap(
		heatmap_y,
		x="hour",
		y="day_of_week",
		z="count",
		color_continuous_scale="Viridis",
		title=f"Hourly Heatmap - {y}"
	)
	fig_y.write_image(os.path.join(TARGET_DIR, f"heatmap_views_{y}.png"))

# Top channels and searches
top_channels = views_df["channel"].dropna().value_counts().head(20)
fig_top_channels = px.bar(top_channels, x=top_channels.index, y=top_channels.values, title="Top 20 Channels")
top_searches = searches_df["query"].value_counts().head(20)
fig_top_searches = px.bar(top_searches, x=top_searches.index, y=top_searches.values, title="Top 20 Searches")

timeline.to_csv(os.path.join(TARGET_DIR, "timeline_daily.csv"), index=False)
fig_timeline.write_image(os.path.join(TARGET_DIR, "timeline_views.png"))
monthly_trend.to_csv(os.path.join(TARGET_DIR, "timeline_monthly.csv"), index=False)
annual_trend.to_csv(os.path.join(TARGET_DIR, "timeline_annual.csv"), index=False)
fig_monthly.write_image(os.path.join(TARGET_DIR, "monthly_trend.png"))
fig_annual.write_image(os.path.join(TARGET_DIR, "annual_trend.png"))
fig_seasonality.write_image(os.path.join(TARGET_DIR, "seasonality_per_year.png"))
fig_aggregate.write_image(os.path.join(TARGET_DIR, "seasonality_aggregate.png"))
fig_dow.write_image(os.path.join(TARGET_DIR, "dayofweek_distribution.png"))
fig_top_channels.write_image(os.path.join(TARGET_DIR, "top_channels.png"))
fig_top_searches.write_image(os.path.join(TARGET_DIR, "top_searches.png"))

# -------------------------
# Wordclouds
# -------------------------
make_wordcloud(searches_df["query"].values, "Searches Wordcloud", os.path.join(TARGET_DIR, "wordcloud_searches.png"))
make_wordcloud(views_df["channel"].dropna().values, "Channels Wordcloud", os.path.join(TARGET_DIR, "wordcloud_channels.png"))

for y in years_sorted:
	searchs_y = views_df.loc[views_df["year"]==y, "search"].dropna().values
	if len(searchs_y):
		make_wordcloud(searchs_y, f"Searches Wordcloud {y}", os.path.join(TARGET_DIR, f"wordcloud_searches_{y}.png"))

# -------------------------
# HTML Dashboard
# -------------------------
print("🖼 Generating HTML dashboard...")

from plotly.subplots import make_subplots

# Create a large dashboard
dashboard = make_subplots(
	rows=3, cols=3,
	subplot_titles=[
		"Daily Timeline",
		"Monthly Trend",
		"Annual Trend",
		"Monthly Seasonality",
		"Aggregate Seasonality",
		"Hourly Heatmap",
		"Day-of-Week Distribution",
		"Top Channels",
		"Top Searches"
	],
	specs=[
		[{"type": "xy"}, {"type": "xy"}, {"type": "xy"}],
		[{"type": "xy"}, {"type": "xy"}, {"type": "heatmap"}],
		[{"type": "xy"}, {"type": "xy"}, {"type": "xy"}]
	]
)

dashboard.add_trace(fig_timeline.data[0], row=1, col=1)
dashboard.add_trace(fig_monthly.data[0], row=1, col=2)
dashboard.add_trace(fig_annual.data[0], row=1, col=3)
for trace in fig_seasonality.data:
	dashboard.add_trace(trace, row=2, col=1)
dashboard.add_trace(fig_aggregate.data[0], row=2, col=2)
for trace in fig_heatmap.data:
	dashboard.add_trace(trace, row=2, col=3)
dashboard.add_trace(fig_dow.data[0], row=3, col=1)
dashboard.add_trace(fig_top_channels.data[0], row=3, col=2)
dashboard.add_trace(fig_top_searches.data[0], row=3, col=3)

dashboard.update_layout(
	height=1800,
	title_text="Advanced YouTube Takeout Dashboard",
	showlegend=False
)

dashboard.write_html(os.path.join(TARGET_DIR, "dashboard.html"))

print(f"✅ Done! Dashboard and charts saved in '{TARGET_DIR}'")

