# main.py
from PyQt5.QtWidgets import QApplication
from data.data_loader import load_data
from models.bd_model import BDModel
from ui.main_window import MainWindow
from ui.matrix_config_editor import MatrixConfigEditor
from data.data_editor import DataEditorDialog

if __name__ == "__main__":
    app = QApplication([])

    # Inicjalizacja modelu
    model = BDModel()

    # Wczytanie danych
    data = load_data()

    # Próba wczytania lub przetrenowania modeli
    model.train_models(data, force_retrain=False)

    # Przygotowanie konfiguratora matryc
    grubosci = sorted(data['Grubosc'].unique())
    matryce = sorted(set(data['V'].unique()))
    matrix_config_editor = MatrixConfigEditor(grubosci, matryce)

    # Inicjalizacja edytora danych
    data_editor = DataEditorDialog(data)

    # Utworzenie głównego okna aplikacji
    window = MainWindow(data, model, matrix_config_editor, data_editor)
    window.populate_comboboxes()
    window.showMaximized()  # Uruchomienie na pełnym ekranie

    app.exec_()
