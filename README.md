# Media EXIF Updater

A Python script that updates media files (images and videos) with EXIF metadata from corresponding JSON files.

I needed a quick way to re-associate the EXIF metadata to media files I had on Google Photos. Turns out that downloading files removes all the metadata, which is quite unconvenient. Using Google Takeout though you can get the files along with a separate .json file with the EXIF data, so here we are :)

## Disclaimer

**This tool has been created almost entirely by vibe-coding, as a thought experiment.**


## Features

- Recursively scans folders for media files
- Supports images: `.jpg`, `.jpeg`, `.png`, `.tiff`, `.tif`
- Supports videos: `.mp4`, `.mov`, `.avi`, `.mkv`, `.m4v`
- Reads metadata from JSON files (`.json`, `.suppl.json`, `.supplemental-metadata.json`)
- Updates EXIF data including:
  - DateTime (from Unix timestamp)
  - Title
  - Description
  - People/Tags
  - GPS coordinates
- Creates a separate output folder (non-destructive)
- Preserves directory structure

## Installation

Install required Python packages:

```bash
pip install Pillow piexif
```

For video support, install exiftool:

```bash
# macOS
brew install exiftool

# Linux
apt-get install exiftool
```

## Usage

Basic usage:
```bash
python main.py ./media
```

This will create a `./media-exif/` folder with updated files.

### Options

```bash
# Dry run (preview without making changes)
python main.py ./media --dry-run

# Custom output folder suffix
python main.py ./media --output-suffix "-updated"
```

## JSON Format

The script expects JSON files with the following structure:

```json
{
  "photoTakenTime": {
    "timestamp": "1628265600"
  },
  "title": "Photo Title",
  "description": "Photo description",
  "people": [
    {"name": "John Doe"},
    {"name": "Jane Smith"}
  ],
  "geoData": {
    "latitude": 37.7749,
    "longitude": -122.4194
  }
}
```

## How It Works

1. Scans the specified folder recursively for media files
2. For each media file, looks for a corresponding JSON file
3. Loads metadata from the JSON file
4. Creates a copy of the media file in the output folder
5. Updates the copy with EXIF metadata from the JSON
6. Preserves the original directory structure in the output folder

## Output

The script creates a new folder with your specified suffix (default: `-exif`) and saves all updated files there, maintaining the same directory structure as the source folder.

Original files are never modified.
