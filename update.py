import hashlib
from datetime import datetime, UTC
from typing import List
import json
import os
from pathlib import Path
import logging
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

import exiftool
import difflib

"""
Updates metadata for each image from google supplemental data
"""

log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "metadata_changes.log"

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding='utf-8'
)

DB_PATH = 'data/takeout.db'
IMAGE_DIR = 'PASTE_YOUR_TAKEOUT_PATH'
IMAGE_DIR_PATH = Path(IMAGE_DIR)
IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.heic']

WORKER_POOL = 5

def to_exif_datetime(timestamp):
    return datetime.fromtimestamp(int(timestamp), UTC).strftime('%Y:%m:%d %H:%M:%S')


def get_image_metadata(image_path: str) -> List:
    try:
        with exiftool.ExifToolHelper() as et:
            return et.get_metadata(image_path)
    except:
        print(f'Failed to get image metadata for {image_path}')
        logging.exception(f'Failed to get image metadata for {image_path}')
        return []


def set_image_metadata(image_path: str, metadata_json: dict):
    with exiftool.ExifToolHelper() as et:
        args = [f"-{k}={v}" for k, v in metadata_json.items()]
        args.append(image_path)
        et.execute(*args)


def convert_google_takeout_to_exif_tags(json_metadata: dict):
    tags = {
        "XMP:Title": json_metadata["title"],
        "XMP:Description": json_metadata["description"],
        "EXIF:DateTimeOriginal": to_exif_datetime(json_metadata["photoTakenTime"]["timestamp"]),
        "XMP:CreateDate": to_exif_datetime(json_metadata["creationTime"]["timestamp"]),
        "EXIF:GPSLatitude": json_metadata["geoData"]["latitude"],
        "EXIF:GPSLongitude": json_metadata["geoData"]["longitude"],
        "EXIF:GPSAltitude": json_metadata["geoData"]["altitude"],

        # presented in some images
        "XMP:ImageViews": json_metadata["imageViews"]
    }
    return tags


def serialize(metadata):
    return json.dumps(metadata, indent=2, sort_keys=True)


def init_database():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS updated_files
            (
                filename TEXT PRIMARY KEY,
                updated_at TEXT,
                metadata_hash TEXT
            )
            '''
        )


def compute_data_hash(data: dict) -> str:
    return hashlib.sha256(serialize(data).encode()).hexdigest()


def was_already_updated(filename: str, current_hash: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT metadata_hash FROM updated_files WHERE filename = ?",
            (filename,)
        ).fetchone()
        return row is not None and row[0] == current_hash


def mark_as_updated(filename: str, metadata_hash: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "REPLACE INTO updated_files (filename, updated_at, metadata_hash) VALUES (?, ?, ?)",
            (filename, datetime.now(UTC).isoformat(), metadata_hash)
        )


def update_metadata(image_metadata_map: dict):
    if not os.path.exists(DB_PATH):
        init_database()

    images = [(IMAGE_DIR_PATH / file_name, meta_path)
              for file_name, meta_path in image_metadata_map.items()]

    with ThreadPoolExecutor(max_workers=WORKER_POOL) as executor:
        futures = [executor.submit(process_image, path, meta_path)
                   for path, meta_path in images]
        for future in as_completed(futures):
            future.result()


def process_image(image_path: Path, path_to_metadata: str):
    data: dict = {}
    if os.path.exists(path_to_metadata):
        with open(path_to_metadata, encoding="utf-8") as json_file:
            data = json.load(json_file)

    if len(list(data)) == 0:
        return

    tags = convert_google_takeout_to_exif_tags(data)

    metadata_hash = compute_data_hash(tags)
    if was_already_updated(str(image_path), metadata_hash):
        logging.info(f"Skipped (already updated): {image_path}")
        return

    try:
        with exiftool.ExifTool() as et:
            metadata_before = get_image_metadata(str(image_path))

            if metadata_before is None:
                return

            args = [f"-{k}={v}" for k, v in tags.items()]
            args.append(str(image_path))
            et.execute(*args)
            metadata_after = get_image_metadata(str(image_path))

        before_str = serialize(metadata_before)
        after_str = serialize(metadata_after)

        diff = "\n".join(difflib.unified_diff(
            before_str.splitlines(),
            after_str.splitlines(),
            fromfile='before.json',
            tofile='after.json',
            lineterm=''
        ))

        logging.info(f"Updated: {image_path}")
        logging.info("=== Metadata Diff ===\n" + diff)
        logging.info("=== New Metadata ===\n" + after_str)

        mark_as_updated(str(image_path), metadata_hash)

    except Exception as e:
        logging.error(f"Failed to update {image_path}: {e}")

def find_image_json_pairs():
    image_json_map = {}

    all_images = [p for p in IMAGE_DIR_PATH.rglob("*") if p.suffix.lower() in IMAGE_EXTS]

    def find_image_metadata_pair(image_path: Path):
        parent_dir = image_path.parent
        image_filename = image_path.name

        json_candidates = list(parent_dir.glob(f"{image_filename}*.json")) + list(parent_dir.glob(f"{image_path.stem}*.json"))

        if not json_candidates:
            logging.warning(f"No metadata files for {image_path}")
            return None

        return str(image_path), str(json_candidates[0])

    with ThreadPoolExecutor(max_workers=WORKER_POOL) as executor:
        futures = [executor.submit(find_image_metadata_pair, img) for img in all_images]
        for future in as_completed(futures):
            result = future.result()
            if result and result[1] is not None:
                image_json_map[result[0]] = result[1]

    return image_json_map

if __name__ == "__main__":
    initial_list = {}

    logging.info("Starting metadata scan and update...")
    image_metadata_map = find_image_json_pairs()
    update_metadata(image_metadata_map=image_metadata_map)
    logging.info("Finish metadata scan and update.")