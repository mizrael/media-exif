#!/usr/bin/env python3
"""
Script to update media files (images and videos) with EXIF metadata from JSON files.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, List, Optional
import subprocess
from datetime import datetime
import shutil

try:
    from PIL import Image
    import piexif
except ImportError:
    print("Error: Required packages not found. Please install them:")
    print("pip install Pillow piexif")
    sys.exit(1)


# Supported file extensions
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.tiff', '.tif'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.m4v'}
ALL_MEDIA_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS


def find_media_files(folder: Path) -> List[Path]:
    """
    Recursively find all media files in the given folder.
    
    Args:
        folder: Path to the folder to scan
        
    Returns:
        List of Path objects for media files
    """
    media_files = []
    for root, _, files in os.walk(folder):
        for file in files:
            file_path = Path(root) / file
            if file_path.suffix.lower() in ALL_MEDIA_EXTENSIONS:
                media_files.append(file_path)
    return media_files


def find_json_file(media_file: Path) -> Optional[Path]:
    """
    Find the corresponding JSON file for a media file.
    
    Args:
        media_file: Path to the media file
        
    Returns:
        Path to JSON file if found, None otherwise
    """
    json_file = media_file.with_suffix(media_file.suffix + '.suppl.json')
    if json_file.exists():
        return json_file
    
    json_file = media_file.with_suffix(media_file.suffix + '.supplemental-metadata.json')
    if json_file.exists():
        return json_file
    
    json_file = media_file.with_suffix(media_file.suffix + '.json')
    if json_file.exists():
        return json_file

    # Also try without the original extension (e.g., file.json instead of file.jpg.json)
    json_file_alt = media_file.with_suffix('.json')
    if json_file_alt.exists():
        return json_file_alt
    
    return None


def load_json_metadata(json_file: Path) -> Optional[Dict]:
    """
    Load metadata from JSON file.
    
    Args:
        json_file: Path to the JSON file
        
    Returns:
        Dictionary containing metadata, or None if error
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {json_file}: {e}")
        return None


def convert_timestamp_to_exif(timestamp: int) -> str:
    """
    Convert Unix timestamp to EXIF datetime format (YYYY:MM:DD HH:MM:SS).
    
    Args:
        timestamp: Unix timestamp (seconds since epoch)
        
    Returns:
        Date string in EXIF format
    """
    # check if timestamp is int or str
    if isinstance(timestamp, str):
        timestamp = int(timestamp)

    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime("%Y:%m:%d %H:%M:%S")


def update_image_exif(image_file: Path, output_file: Path, metadata: Dict) -> bool:
    """
    Update EXIF metadata for an image file using piexif.
    
    Args:
        image_file: Path to the source image file
        output_file: Path to save the updated image file
        metadata: Dictionary containing EXIF metadata
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Load existing EXIF data
        try:
            exif_dict = piexif.load(str(image_file))
        except Exception:
            # If no EXIF data exists, create empty structure
            exif_dict = {"0th": {}, "Exif": {}, "GPS": {}, "1st": {}}
        
        # Update EXIF data from metadata
        # This is a basic implementation - you may need to customize based on your JSON structure
        if 'photoTakenTime' in metadata :
            timestamp = metadata.get('photoTakenTime', {}).get('timestamp')
            if timestamp is not None:
                print (f"Setting DateTime EXIF data: {timestamp}")
                date_time = convert_timestamp_to_exif(timestamp)
                print (f"Setting DateTime EXIF data: {date_time} (from timestamp: {timestamp})")
                exif_dict['0th'][piexif.ImageIFD.DateTime] = date_time.encode('utf-8')
                exif_dict['Exif'][piexif.ExifIFD.DateTimeOriginal] = date_time.encode('utf-8')
                exif_dict['Exif'][piexif.ExifIFD.DateTimeDigitized] = date_time.encode('utf-8')
            
        if 'title' in metadata or 'Title' in metadata:
            title = metadata.get('title') or metadata.get('Title')
            if title is not None:
                print (f"Setting XPTitle EXIF data: {title}")
                exif_dict['0th'][piexif.ImageIFD.XPTitle] = title.encode('utf-16le')

        if 'description' in metadata or 'Description' in metadata:
            desc = metadata.get('description') or metadata.get('Description')
            if desc is not None:
                print (f"Setting ImageDescription EXIF data: {desc}")
                exif_dict['0th'][piexif.ImageIFD.ImageDescription] = desc.encode('utf-8')
        
        if 'people' in metadata:
            people = metadata['people']
            if people is not None and isinstance(people, list):
                # extract the names
                people_names = [p.get('name') for p in people if 'name' in p]
                people_str = ', '.join(people_names)
                print(f"Setting XPComment EXIF data: {people_str}")
                exif_dict['0th'][piexif.ImageIFD.XPComment] = people_str.encode('utf-16le')
        
        # GPS data
        if 'geoData' in metadata:
            geo = metadata['geoData']
            if geo is not None:
                if 'latitude' in geo and 'longitude' in geo:
                    lat = geo['latitude']
                    lon = geo['longitude']
                    if lat is not None and lon is not None:
                        print(f"Setting GPS EXIF data: lat={lat}, lon={lon}")
                        exif_dict['GPS'] = create_gps_exif(lat, lon)
            
        # Convert EXIF dict to bytes
        exif_bytes = piexif.dump(exif_dict)
        
        # Create output directory if it doesn't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Save image with new EXIF data to output file
        img = Image.open(image_file)
        img.save(str(output_file), exif=exif_bytes, quality=95)
        
        return True
    except Exception as e:
        print(f"Error updating EXIF for {image_file}: {e}")
        return False


def create_gps_exif(lat: float, lon: float) -> Dict:
    """
    Create GPS EXIF data from latitude and longitude.
    
    Args:
        lat: Latitude in decimal degrees
        lon: Longitude in decimal degrees
        
    Returns:
        Dictionary with GPS EXIF data
    """
    def to_degrees(value: float) -> tuple:
        """Convert decimal degrees to degrees, minutes, seconds."""
        value = abs(value)
        degrees = int(value)
        minutes = int((value - degrees) * 60)
        seconds = (value - degrees - minutes / 60) * 3600
        return ((degrees, 1), (minutes, 1), (int(seconds * 100), 100))
    
    gps_ifd = {
        piexif.GPSIFD.GPSLatitudeRef: 'N' if lat >= 0 else 'S',
        piexif.GPSIFD.GPSLatitude: to_degrees(lat),
        piexif.GPSIFD.GPSLongitudeRef: 'E' if lon >= 0 else 'W',
        piexif.GPSIFD.GPSLongitude: to_degrees(lon),
    }
    return gps_ifd


def check_exiftool_installed() -> bool:
    """
    Check if exiftool is installed on the system.
    
    Returns:
        True if exiftool is available, False otherwise
    """
    try:
        subprocess.run(['exiftool', '-ver'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def update_video_exif(video_file: Path, output_file: Path, metadata: Dict) -> bool:
    """
    Update EXIF metadata for a video file using exiftool.
    
    Args:
        video_file: Path to the source video file
        output_file: Path to save the updated video file
        metadata: Dictionary containing EXIF metadata
        
    Returns:
        True if successful, False otherwise
    """
    if not check_exiftool_installed():
        print("Warning: exiftool not installed. Skipping video file.")
        print("Install exiftool: brew install exiftool (macOS) or apt-get install exiftool (Linux)")
        return False
    
    try:
        # Create output directory if it doesn't exist
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Copy the file first
        shutil.copy2(video_file, output_file)
        
        # Build exiftool command
        cmd = ['exiftool', '-overwrite_original']
        
        # Add metadata tags
        if 'dateTime' in metadata or 'DateTime' in metadata:
            date_time = metadata.get('dateTime') or metadata.get('DateTime')
            cmd.extend([f'-CreateDate={date_time}', f'-ModifyDate={date_time}'])
        
        if 'description' in metadata or 'Description' in metadata:
            desc = metadata.get('description') or metadata.get('Description')
            cmd.append(f'-Description={desc}')
        
        if 'make' in metadata or 'Make' in metadata:
            make = metadata.get('make') or metadata.get('Make')
            cmd.append(f'-Make={make}')
        
        if 'model' in metadata or 'Model' in metadata:
            model = metadata.get('model') or metadata.get('Model')
            cmd.append(f'-Model={model}')
        
        if 'gpsLatitude' in metadata and 'gpsLongitude' in metadata:
            lat = metadata['gpsLatitude']
            lon = metadata['gpsLongitude']
            cmd.extend([f'-GPSLatitude={lat}', f'-GPSLongitude={lon}'])
        
        cmd.append(str(output_file))
        
        # Execute exiftool
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            return True
        else:
            print(f"exiftool error for {video_file}: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"Error updating metadata for {video_file}: {e}")
        return False


def process_media_file(media_file: Path, source_folder: Path, output_folder: Path, dry_run: bool = False) -> bool:
    """
    Process a single media file: find JSON, load metadata, update file.
    
    Args:
        media_file: Path to the media file
        source_folder: The original source folder
        output_folder: The output folder for updated files
        dry_run: If True, only show what would be done
        
    Returns:
        True if successful or skipped, False if error
    """
    # Find corresponding JSON file
    json_file = find_json_file(media_file)
    
    if json_file is None:
        print(f"⊘ No JSON found for: {media_file}")
        return True  # Not an error, just skip
    
    # Load metadata
    metadata = load_json_metadata(json_file)
    if metadata is None:
        return False
    
    # Calculate relative path from source folder
    relative_path = media_file.relative_to(source_folder)
    output_file = output_folder / relative_path
    
    if dry_run:
        print(f"[DRY RUN] Would update {media_file} -> {output_file} with metadata from {json_file}")
        return True
    
    # Update based on file type
    is_image = media_file.suffix.lower() in IMAGE_EXTENSIONS
    is_video = media_file.suffix.lower() in VIDEO_EXTENSIONS
    
    if is_image:
        success = update_image_exif(media_file, output_file, metadata)
        if success:
            print(f"✓ Updated image: {media_file} -> {output_file}")
        return success
    elif is_video:
        success = update_video_exif(media_file, output_file, metadata)
        if success:
            print(f"✓ Updated video: {media_file} -> {output_file}")
        return success
    
    return False


def main():
    """Main function to run the script."""
    parser = argparse.ArgumentParser(
        description='Update media files with EXIF metadata from JSON files.'
    )
    parser.add_argument(
        'folder',
        type=str,
        help='Folder to scan for media files'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be done without making changes'
    )
    parser.add_argument(
        '--output-suffix',
        type=str,
        default='-exif',
        help='Suffix to append to the output folder name (default: -exif)'
    )
    
    args = parser.parse_args()
    
    folder = Path(args.folder).resolve()
    
    if not folder.exists():
        print(f"Error: Folder '{folder}' does not exist.")
        sys.exit(1)
    
    if not folder.is_dir():
        print(f"Error: '{folder}' is not a directory.")
        sys.exit(1)
    
    # Create output folder name
    output_folder = folder.parent / (folder.name + args.output_suffix)
    
    print(f"Scanning folder: {folder}")
    print(f"Output folder: {output_folder}")
    print("-" * 60)
    
    # Find all media files
    media_files = find_media_files(folder)
    
    if not media_files:
        print("No media files found.")
        return
    
    print(f"Found {len(media_files)} media file(s)")
    print("-" * 60)
    
    # Process each file
    success_count = 0
    skipped_count = 0
    error_count = 0
    
    for media_file in media_files:
        json_file = find_json_file(media_file)
        if json_file is None:
            skipped_count += 1
        else:
            success = process_media_file(media_file, folder, output_folder, dry_run=args.dry_run)
            if success:
                success_count += 1
            else:
                error_count += 1
    
    print("-" * 60)
    print(f"Summary:")
    print(f"  Updated: {success_count}")
    print(f"  Skipped (no JSON): {skipped_count}")
    print(f"  Errors: {error_count}")
    if not args.dry_run and success_count > 0:
        print(f"\nUpdated files saved to: {output_folder}")


if __name__ == '__main__':
    main()
