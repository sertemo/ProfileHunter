from pathlib import Path

FILE_TO_DOWNLOAD = 'geckodriver-v0.33.0-win64.zip'
URL_GECKO_WIN64_ZIP = 'https://github.com/mozilla/geckodriver/releases/download/v0.33.0/' + FILE_TO_DOWNLOAD
RUTA_RAIZ = Path.home() / Path("ProfileHunter")
RUTA_GECKODRIVER = RUTA_RAIZ / Path('WebDriver/bin')
RUTA_DB = RUTA_RAIZ / Path("db")
CONFIG_FILE = 'config.txt'
save_path_file_db = RUTA_DB / 'excels_path.txt'
DB_NAME = "hunts.db"
NOMBRE_DB_SQLITE = RUTA_DB / DB_NAME