# bitsofus - takeout data enhancer utilities

A few scripts to gather & analyze bits of us from Instagram & Youtube takeouts, with scraping, metadata integration, and analytics.

## Features

### Instagram
- **Download saved/liked posts** with metadata integration
- **Export chats** to structured JSONL format
- **Activity analytics** with interactive plots and statistics
- **EXIF metadata preservation** for downloaded media

### YouTube
- **Download playlists**, including *liked* playlist (metadata, audio or video using [yt-dlp](https://github.com/yt-dlp/yt-dlp))
- **Highlights dashboard** with viewing patterns and trends (similar to [A3M4/YouTube-Report](https://github.com/A3M4/YouTube-Report))
- **Wordclouds** for searches and watched content
- **Time series & seasonal plots**

### Daylio
- **Time-series plots** of smoked cigarettes per day (this is what I use this App for 😬)

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone https://github.com/giopaglia/bitsofus.git
cd bitsofus
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your takeout data paths
```

## Usage

### Instagram

#### Download Saved Posts
```bash
python instagram-list.py saved
```

#### Download Liked Posts (excluding saved)
```bash
python instagram-list.py liked
```

#### Export Messages & Attachments
```bash
python instagram-messages.py
```

#### Analytics
```bash
python others/instagram-plot-activity.py
python others/instagram-plot-chat.py
python others/instagram-plot-comments.py
```

### YouTube

#### Generate Analytics Dashboard
This create informative plots, wordclouds and dashboards based on your searches and views
```bash
python youtube-highlights.py
```

#### Download Playlists
```bash
python youtube-playlists.py
```

#### Export Your Videos
(this plainly copies your uploaded videos to a target folder)
```bash
python youtube-myvideos.py
```

## Data Sources

### Instagram Takeout
Request your data from **Settings → Your Activity → Download Your Information** (JSON format).

Key files:
- `saved/saved_posts.json` - Your saved posts
- `likes/liked_posts.json` - Your liked posts
- `messages/` - Your conversations
- `comments/` - Your comments

### YouTube Takeout
Request it as part of your [Google Takeout](https://takeout.google.com/manage).

Key files (sorry, it's in Italian 🇮🇹):
- `YouTube e YouTube Music/cronologia/cronologia visualizzazioni.json` - Viewing history
- `YouTube e YouTube Music/cronologia/cronologia delle ricerche.json` - Search history
- `YouTube e YouTube Music/playlist` - Your playlists
- `YouTube e YouTube Music/video/` - Your uploaded videos
- `YouTube e YouTube Music/commenti*` - Your comments
- `YouTube e YouTube Music/music (library and uploads)/music library songs.csv` - Your music

##### Bonus: liked videos
The takeout does not contain the playlist of liked videos, but it can be downloaded
as `.csv` through the web UI using the following instructions:

<details>

Go to https://www.youtube.com/playlist?list=LL

Scroll down to the bottom to load the full playlist. You can use this piece of code (authored by
McBear Holden)[https://stackoverflow.com/questions/57868201/how-to-scroll-youtube-playlist-with-javascript]:
```
setInterval(() => {
	window.scrollTo(0,document.querySelector("ytd-playlist-video-list-renderer.style-scope").scrollHeight);
}, 50);
```

Then, download the playlist as csv with this:
```
(async function() {
	const saving_playlist = window.location.href.includes('/playlist?list=');
	const all_contents = saving_playlist
		? document.querySelectorAll('div#contents > ytd-playlist-video-renderer > div#content > div#container > div#meta')
		: document.querySelectorAll('#content > yt-lockup-view-model > div > div > yt-lockup-metadata-view-model > div.yt-lockup-metadata-view-model-wiz__text-container');

	function extract_video_id(url) {
		const match = url.match(/[?&]v=([^&]+)/);
		return match ? match[1] : '';
	}

	function get_title(item) {
		const el = item.querySelector('h3 > a');
		return el ? el.innerText.trim() : '[Video Unavailable]';
	}

	function get_link(item) {
		let el;
		if (saving_playlist) {
			el = item.querySelector('h3 > a');
		} else {
			el = item.querySelector('div > yt-content-metadata-view-model > div:last-child > span > span > a');
		}
		return el ? el.href : '';
	}

	function get_channel_name(item) {
		let el;
		if (saving_playlist) {
			el = item.querySelector('ytd-video-meta-block #byline-container ytd-channel-name');
		} else {
			el = item.querySelector('div > yt-content-metadata-view-model > div:nth-of-type(1) > span');
		}
		return el ? el.innerText.trim() : '';
	}

	function get_channel_link(item) {
		let el;
		if (saving_playlist) {
			el = item.querySelector('ytd-video-meta-block #byline-container ytd-channel-name a');
		} else {
			el = item.querySelector('div > yt-content-metadata-view-model > div:nth-of-type(1) > span > span > a');
		}
		return el ? el.href : '';
	}

	function get_views_and_date(item) {
		let views = '';
		let date = '';
		if (saving_playlist) {
			const spans = item.querySelectorAll('ytd-video-meta-block #video-info span');
			if (spans.length >= 3) {
				views = spans[0].innerText.trim();
				date = spans[2].innerText.trim();
			}
		} else {
			const meta = item.querySelector('div > yt-content-metadata-view-model');
			if (meta) {
				const parts = meta.innerText.split(' • ');
				if (parts.length >= 2) {
					views = parts[0].trim();
					date = parts[1].trim();
				}
			}
		}
		return { views, date };
	}

	function escapeCSV(str) {
		return `"${String(str || '').replace(/"/g, '""')}"`;
	}

	let csv = `"Title","Channel Name","Channel Link","Video Link","ID video","Views","Date Posted"\n`;

	for (const item of all_contents) {
		const link = get_link(item);
		const video_id = extract_video_id(link);
		const title = get_title(item);
		const channel_name = get_channel_name(item);
		const channel_link = get_channel_link(item);
		const { views, date } = get_views_and_date(item);

		csv += [
			escapeCSV(title),
			escapeCSV(channel_name),
			escapeCSV(channel_link),
			escapeCSV(link),
			escapeCSV(video_id),
			escapeCSV(views),
			escapeCSV(date)
		].join(',') + '\n';
	}

	// Download CSV
	const blob = new Blob([csv], { type: 'text/csv' });
	const url = URL.createObjectURL(blob);
	const a = document.createElement('a');
	a.href = url;
	a.download = 'youtube_export.csv';
	document.body.appendChild(a);
	a.click();
	document.body.removeChild(a);
	URL.revokeObjectURL(url);

	console.log('CSV export completed!');
})();

```

Thx to @evdokimovm for [a starter](https://gist.github.com/evdokimovm/cd46cf17b00c044efb3a0c2c1e5d93a7).

Other utilities:
- https://webapps.stackexchange.com/questions/72787/how-to-create-a-youtube-playlist-from-a-list-of-links
</details>

## Usage

### Daylio

#### Plots
```bash
python daylio-smoking.py
```


## Important Notes

⚠️ **Terms of Service**: This tool automates requests which may violate Instagram/YouTube TOS. Use responsibly and respect rate limits.

🔒 **Privacy**: Your takeout data contains sensitive information. Keep it secure and don't share it publicly.

📊 **Data Quality**: Takeout data format may change. Report issues if scripts stop working.

## Blacklist System

Both Instagram and YouTube scripts use a blacklist system to avoid repeatedly trying to download unavailable content:

- **Instagram**: URLs that return "410 Gone" or "400 Bad Request" errors
- **YouTube**: Video IDs that are "Private", "Unavailable", or have access restrictions

Blacklist files are stored in `cache/`:
- `cache/instagram-blacklist.json` - List of problematic Instagram URLs
- `cache/youtube-blacklist.json` - List of problematic YouTube video IDs

You can manually edit these files to remove entries if content becomes available again.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## TODO

- [ ] Improve EXIF metadata integration
- [ ] Add support for more platforms (Facebook, Spotify, WhatsApp, Last.fm, etc.)
- [ ] Create web interface for analytics
- [ ] Add data validation and integrity checks
- [ ] Implement incremental updates
- [ ] Create Docker container for easy deployment
