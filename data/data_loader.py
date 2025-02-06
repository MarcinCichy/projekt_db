# data_loader.py
import os
import json
import pandas as pd
from ui.matrix_config_editor import load_matrix_config

# Domyślne ścieżki plików (przykład)
DATA_FILE_JSON = "data.json"
DATA_FILE_EXCEL = "Ubytki.xlsx"


def load_data():
    """Wczytuje dane z pliku JSON lub Excela."""
    if os.path.exists(DATA_FILE_JSON):
        return load_data_from_json(DATA_FILE_JSON)
    elif os.path.exists(DATA_FILE_EXCEL):
        data = import_data_from_excel(DATA_FILE_EXCEL)
        save_data_to_json(data, DATA_FILE_JSON)
        return data
    else:
        raise FileNotFoundError(f"Brak pliku {DATA_FILE_JSON} lub {DATA_FILE_EXCEL}.")


def load_data_from_json(file_path="data.json"):
    """Wczytuje dane treningowe z pliku JSON."""
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Plik {file_path} nie istnieje.")
    with open(file_path, "r", encoding="utf-8") as file:
        data = json.load(file)
    return pd.DataFrame(data)


def save_data_to_json(data, file_path="data.json"):
    """Zapisuje dane treningowe do pliku JSON."""
    try:
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data.to_dict(orient="records"), file, indent=4)
            print(f"Dane zapisano do pliku JSON: {file_path}")
    except Exception as e:
        raise IOError(f"Nie udało się zapisać danych do JSON: {e}")


def import_data_from_excel(file_path="Ubytki.xlsx"):
    """Importuje dane treningowe z pliku Excel."""
    try:
        data = pd.read_excel(file_path, sheet_name="Sheet1")
        # Przykładowa nazwa kolumn
        if "Szerokośc matrycy V" in data.columns:
            # Upewniamy się, że w DataFrame wartości V są typu float
            data["Szerokośc matrycy V"] = (
                data["Szerokośc matrycy V"].astype(str).str.extract(r"(\d+(\.\d+)?)").astype(float)
            )
        data = data.rename(
            columns={
                "Grubość": "Grubosc",
                "Szerokośc matrycy V": "V",
                "kąt": "Kat",
                "CZ": "BD_CZ",
                "N": "BD_N",
            }
        )
        data = data.dropna(subset=["Grubosc", "V", "Kat"])  # i ewentualnie BD_CZ/BD_N
        return data
    except Exception as e:
        raise IOError(f"Nie udało się zaimportować danych z pliku Excel: {e}")


def filter_matrix_widths(grubosc, widths):
    """
    Filtruje szerokości matryc na podstawie konfiguracji.
    1) W pliku config/matrix_config.json klucze mogą być np. "2.0", "3.0".
    2) Ujednolicamy klucz do formatu str(float(grubosc)).
    3) Konwertujemy wartości do float, aby porównać z 'widths'.
    """
    print(f"DEBUG: filter_matrix_widths -> grubosc={grubosc}, widths={widths}")
    config = load_matrix_config()  # np. {"2.0": ["6.0","8.0"], "3.0": ["10.0","12.0"]}
    # ujednolicamy klucz – np. grubosc=2 -> "2.0"
    key = str(float(grubosc))
    print("DEBUG: klucz w configu =", key)

    # pobieramy z configa listę dozwolonych szerokości (domyślnie używamy widths)
    allowed_widths_raw = config.get(key, widths)
    print("DEBUG: allowed_widths_raw z configu =", allowed_widths_raw)

    # konwertujemy na float, bo w pliku config mogą być stringi
    allowed_widths_floats = [float(x) for x in allowed_widths_raw]

    # Teraz filtrujemy 'widths'
    # widths (z DataFrame) powinny być float, np. [6.0, 8.0, 10.0]
    # Zwracamy tylko te, które są w allowed_widths_floats
    filtered = [w for w in widths if w in allowed_widths_floats]
    print(f"DEBUG: Po filtrze zwracamy {filtered}\n")
    return filtered


def export_data_to_excel(data, file_path=DATA_FILE_EXCEL):
    """Eksportuje dane treningowe do pliku Excel."""
    try:
        data.to_excel(file_path, sheet_name="Sheet1", index=False)
        print(f"Dane wyeksportowano do {file_path}")
    except Exception as e:
        raise IOError(f"Nie udało się wyeksportować danych: {e}")
