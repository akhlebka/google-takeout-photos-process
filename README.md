# Google Takeout data processor for later Google Photo import

## Requirements
1. Python 3.13
2. Exiftool installed on Machine 
3. Packages from requirements.txt

## Usage 

- First run `rename.py` script to clean all paths from unicode characters
- Run `update.py` script to update all images with google metadata (it prevents losing chronological order of photos)
- Run `hide_metadata.py` script to leave only images and photo in folders and move all metadata to 'metadata' folders