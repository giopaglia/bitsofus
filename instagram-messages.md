## 📂 Folder Structure Description

This directory contains processed Instagram messages, structured for machine-readability and efficient retrieval of content and metadata.

**Top-level directories and files:**

```
/OUTPUT_DIR/
├── messages/
│   ├── anna/
│   │   ├── messages.jsonl
│   │   └── attachments/
│   │       ├── <renamed files>
│   ├── giovannino/
│   │   ├── messages.jsonl
│   │   └── attachments/
│   └── ...
└── ...
```

---

## 📘 How to Parse

### 1️⃣ **Conversations**

* Each conversation (thread) has its **own folder** named after the contact or group.

	* Example: `anna/`, `giovannino/`, etc.

---

### 2️⃣ **Messages File**

* Each conversation folder contains **one `messages.jsonl` file**.
* This is a [JSON Lines](https://jsonlines.org/) file: **each line is a standalone JSON object** representing a single message.

**Example line in `messages.jsonl`:**

```json
{
	"sender": "giovannino",
	"timestamp": "2023-06-27T15:30:00",
	"text": "Hi there!",
	"photos": ["attachments/giovannino__2023-06-27T15:30:00__photo.jpg"],
	"videos": [],
	"audios": [],
	"gifs": [],
	"reactions": []
}
```

**Field descriptions:**

* `sender` – Who sent the message.
* `timestamp` – ISO 8601 timestamp.
* `text` – Text content, or empty if none.
* `photos`, `videos`, `audios`, `gifs` – Lists of relative paths to **renamed attachments** (may be empty).
* `reactions` – Optional reactions to this message (if present).
* All attachments have been **copied and renamed** to include:

	* **Thread name**
	* **Sender name**
	* **Timestamp**
	* **Original filename**

Example filename:

```
anna__giovannino__2023-06-27T15:30:00__IMG_1234.jpg
```

---

### 3️⃣ **Attachments Directory**

* All non-text content lives in the `attachments/` subfolder.
* Files are renamed consistently (see above).
* **Last modified timestamp** of each file is set to the message timestamp.

---

## 🧭 How to Retrieve Data

✅ **To reconstruct all messages in order:**

1. Open the `messages.jsonl`.
2. Read all lines.
3. Parse each line as JSON.
4. Sort by `timestamp`.

✅ **To retrieve attachments:**

* For each message, look up the relevant lists (`photos`, `videos`, etc.).
* Each list contains relative paths to the corresponding files in `attachments/`.

✅ **To filter by sender, date, or type:**

* Use the `sender` field.
* Use `timestamp` (ISO format) for filtering by date.
* Use non-empty `photos`, `videos`, `audios`, `gifs` lists to detect attachment types.

✅ **To get the original filename:**

* Extract it after the final `__` in the renamed attachment filename.

	* Example:

		* `anna__giovannino__2023-06-27T15:30:00__IMG_1234.jpg`
		* Original filename: `IMG_1234.jpg`

---

✅ **Example prompt to an LLM agent:**

> Given this folder structure, read `messages.jsonl` files, parse each line as JSON, and create a chronological list of all messages (including text and media). For each attachment, construct the full filesystem path by joining the conversation folder, `attachments/`, and the filename in the relevant list.

---

If you’d like, I can help you craft additional retrieval instructions or sample parsing scripts!
