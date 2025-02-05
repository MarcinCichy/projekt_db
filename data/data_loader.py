# data/data_loader.py
import pandas as pd
import os
import json
from ui.matrix_config_editor import load_matrix_config
from dotenv import load_dotenv

# Pobierz ścieżkę do pliku data.json z zmiennych środowiskowych lub użyj domyślnej
DATA_FILE = os.getenv('DATA_FILE', 'default_data.json')
DATA_FILE_EXCEL = 'Ubytki.xlsx'
DATA_FILE_JSON = 'data.json'

def load_data():
    """Wczytuje dane z pliku JSON lub Excela."""
    if os.path.exists(DATA_FILE_JSON):
        # Wczytaj dane z JSON
        return load_data_from_json()
    elif os.path.exists(DATA_FILE_EXCEL):
        # Jeśli JSON nie istnieje, zaimportuj dane z Excela i zapisz do JSON
        data = import_data_from_excel(DATA_FILE_EXCEL)
        save_data_to_json(data)
        return data
    else:
        raise FileNotFoundError(f"Brak danych treningowych: {DATA_FILE_JSON} lub {DATA_FILE_EXCEL}.")

def load_data_from_json(file_path="data.json"):
    """Wczytuje dane treningowe z pliku JSON."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Plik {file_path} nie istnieje.")
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
            print("Wczytane dane JSON:")
            print(data)
        return pd.DataFrame(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Nie udało się wczytać danych JSON: {e}")

def save_data_to_json(data, file_path="data.json"):
    """Zapisuje dane treningowe do pliku JSON."""
    try:
        with open(file_path, "w") as file:
            json.dump(data.to_dict(orient="records"), file, indent=4)
            print(f"Dane zapisano do pliku JSON: {file_path}")
    except Exception as e:
        raise IOError(f"Nie udało się zapisać danych do JSON: {e}")

def filter_matrix_widths(grubosc, widths):
    """Filtruje szerokości matryc na podstawie konfiguracji."""
    config = load_matrix_config()
    allowed_widths = config.get(str(grubosc), widths)
    return [float(w) for w in widths if float(w) in allowed_widths]

def import_data_from_excel(file_path="Ubytki.xlsx"):
    """Importuje dane treningowe z pliku Excel."""
    try:
        data = pd.read_excel(file_path, sheet_name="Sheet1")

        # Upewnij się, że kolumna 'Szerokośc matrycy V' jest tekstowa
        if 'Szerokośc matrycy V' in data.columns:
            data['Szerokośc matrycy V'] = data['Szerokośc matrycy V'].astype(str).str.extract("(\d+)").astype(float)

        # Przekształcenie danych na poprawny format
        data = data.rename(columns={
            "Grubość": "Grubosc",
            "Szerokośc matrycy V": "V",
            "kąt": "Kat",
            "CZ": "BD_CZ",
            "N": "BD_N"
        })

        # Usuwanie wierszy z brakującymi wartościami
        data = data.dropna(subset=["Grubosc", "V", "Kat", "BD_CZ", "BD_N"])

        return data

    except Exception as e:
        raise IOError(f"Nie udało się zaimportować danych z pliku Excel: {e}")

def export_data_to_excel(data, file_path=DATA_FILE_EXCEL):
    """Eksportuje dane treningowe do pliku Excel."""
    try:
        data.to_excel(file_path, sheet_name="Sheet1", index=False)
    except Exception as e:
        raise IOError(f"Nie udało się wyeksportować danych do pliku Excel: {e}")
