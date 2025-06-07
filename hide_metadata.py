import os
import shutil
from pathlib import Path

"""
This code moves all "non-image" and "non-video" files to metadata folder on the same folder level
so they won't make visual noise in the folder
"""

IMAGE_EXTENSIONS = {
    '.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tiff',
    '.heic', '.heif', '.dng', '.raw'
}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}

IMAGE_DIR = 'PASTE_YOUR_TAKEOUT_PATH'
IMAGE_DIR_PATH = Path(IMAGE_DIR)

def is_media_file(file_path: Path):
    return file_path.suffix.lower() in IMAGE_EXTENSIONS.union(VIDEO_EXTENSIONS)


def organize_metadata(root_folder: Path):
    for current_dir, _, files in os.walk(root_folder):
        current_path = Path(current_dir)
        metadata_dir = current_path / "metadata"

        for file_name in files:
            file_path = current_path / file_name

            if not is_media_file(file_path):
                metadata_dir.mkdir(exist_ok=True)
                target_path = metadata_dir / file_name
                print(f"Moving {file_path} -> {target_path}")
                shutil.move(str(file_path), str(target_path))


def move_images_back_from_metadata(root_folder: Path):
    for metadata_dir in root_folder.rglob("metadata"):
        if not metadata_dir.is_dir():
            continue

        parent_dir = metadata_dir.parent
        for file_path in metadata_dir.iterdir():
            if file_path.suffix.lower() in IMAGE_EXTENSIONS:
                target_path = parent_dir / file_path.name

                if target_path.exists():
                    print(f"⚠️ Skipping existing file: {target_path}")
                    continue  # or choose to overwrite

                print(f"🔄 Moving back: {file_path} -> {target_path}")
                shutil.move(str(file_path), str(target_path))


if __name__ == "__main__":
    organize_metadata(IMAGE_DIR_PATH)
