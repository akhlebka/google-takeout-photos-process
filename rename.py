import os
from pathlib import Path

import unidecode
import re
from PIL import Image

"""
Removes unicode from paths so Exiftool can work correctly
"""

IMAGE_DIR = 'PASTE_YOUR_TAKEOUT_PATH'
IMAGE_DIR_PATH = Path(IMAGE_DIR)

def transliterate_path(path):
    dirname = os.path.dirname(path)
    basename = os.path.basename(path)
    transliterated = unidecode.unidecode(basename)
    re.sub(r'[^\w_. -]', '_', transliterated)
    return os.path.join(dirname, transliterated)


def rename_all(root_dir):
    for root, dirs, files in os.walk(root_dir, topdown=False):
        for name in files:
            if not Image.isImageType(os.path.join(root, name)):
                continue
            old_path = os.path.join(root, name)
            new_path = transliterate_path(old_path)
            if old_path != new_path:
                os.rename(old_path, new_path)
                print(f"Renamed file: {old_path} -> {new_path}")

        # Rename directories
        for name in dirs:
            old_path = os.path.join(root, name)
            new_path = transliterate_path(old_path)
            if old_path != new_path:
                os.rename(old_path, new_path)
                print(f"Renamed dir:  {old_path} -> {new_path}")


# Usage

rename_all(IMAGE_DIR_PATH)
