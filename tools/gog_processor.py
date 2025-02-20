import os
import sys
import shutil
import subprocess
import requests
import json
import tempfile
import time
from pathlib import Path
import zipfile
import configparser

class GOGProcessor:
    def __init__(self, config_path='config.ini'):
        print("GOGProcessor initialized")
        self.config = configparser.ConfigParser()
        self.config.read(config_path)
        
        self.watch_dir = Path(self.config.get('folders', 'watch_dir', fallback="/WATCHED"))
        self.dest_dir = Path(self.config.get('folders', 'dest_dir', fallback="/DEST"))
        self.processed_json = self.watch_dir / "processed_files.json"
        self.processed_dir = Path(self.config.get('folders', 'processed_dir', fallback="processed"))
        
        self.innoextract_path = Path(__file__).parent / ("bin/innoextract.exe" if sys.platform == "win32" else "bin/innoextract")
        
        self.dest_dir.mkdir(parents=True, exist_ok=True)
        (self.watch_dir / self.processed_dir).mkdir(parents=True, exist_ok=True)
        
        self.processed_files = self.load_processed_files()
    
    def load_processed_files(self):
        if self.processed_json.exists():
            with open(self.processed_json, "r") as f:
                return set(json.load(f))
        return set()
    
    def save_processed_files(self):
        with open(self.processed_json, "w") as f:
            json.dump(list(self.processed_files), f)
    
    def fetch_metadata(self, game_id):
        api_url = f"https://api.gog.com/products/{game_id}"
        print(f"Fetching metadata for game ID {game_id} from GOG API...")
        response = requests.get(api_url)
        
        if response.status_code != 200:
            print("Error: Unable to fetch data from GOG API.")
            return "Unknown Game", "0000"

        data = response.json()
        game_title = data.get("title", "Unknown Game")
        release_date = data.get("release_date", "0000")
        year = release_date.split("-")[0] if release_date else "0000"
        
        return game_title, year
    
    def process_installer(self, installer):
        print(f"Extracting GOG game ID from {installer}...")
        try:
            result = subprocess.run([str(self.innoextract_path), "--gog-game-id", str(installer)], capture_output=True, text=True)
            gog_game_id = next((line.split("ID is ")[-1] for line in result.stdout.splitlines() if "ID is " in line), None)
            
            if not gog_game_id:
                raise ValueError("No game ID found")
        except Exception as e:
            print(f"Error: Unable to extract GOG game ID: {e}")
            return
        
        game_name, year = self.fetch_metadata(gog_game_id)
        folder_name = f"{game_name} (W_P) ({year})" if year != "0000" else f"{game_name} (W_P)"
        folder_name = folder_name.replace(":", "")
        
        game_folder = self.watch_dir / self.processed_dir / folder_name
        game_folder.mkdir(parents=True, exist_ok=True)
        
        temp_dir = Path(tempfile.mkdtemp())
        
        try:
            print(f"Extracting {installer}...")
            subprocess.run([str(self.innoextract_path), "--gog", "--exclude-temp", "--output-dir", str(temp_dir), str(installer)], check=True)
            
            zip_name = f"{folder_name}.zip"
            with zipfile.ZipFile(self.dest_dir / zip_name, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        file_path = Path(root) / file
                        zipf.write(file_path, file_path.relative_to(temp_dir))
            
            print(f"Archive created: {self.dest_dir / zip_name}")
        finally:
            print(f"Cleaning up {temp_dir}...")
            shutil.rmtree(temp_dir)
        
        processed_path = game_folder / installer.name
        installer.rename(processed_path)
        print(f"Moved {installer} to {processed_path}.")
        
        for bin_file in self.watch_dir.glob(installer.stem + "-*.bin"):
            bin_file.rename(game_folder / bin_file.name)
            print(f"Moved {bin_file} to {game_folder / bin_file.name}.")
        
        self.processed_files.add(str(installer))
        self.save_processed_files()
    
    def watch_folder(self):
        print(f"Watching {self.watch_dir} for new EXE files...")
        while True:
            for exe_file in self.watch_dir.glob("*.exe"):
                if str(exe_file) not in self.processed_files:
                    print(f"New installer detected: {exe_file}")
                    self.process_installer(exe_file)
            time.sleep(5)
    
    def start(self):
        self.watch_folder()

if __name__ == "__main__":
    processor = GOGProcessor()
    processor.start()
