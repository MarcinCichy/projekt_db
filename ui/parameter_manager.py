# ui/parameter_manager.py
from PyQt5.QtWidgets import QHBoxLayout, QComboBox, QLabel
import pandas as pd
from data.data_loader import filter_matrix_widths

class ParameterManager:
    def __init__(self, parent):
        self.parent = parent
        self.layout = QHBoxLayout()
        self.data = None

        self.grubosc_input = QComboBox()
        # WAŻNE: sygnał zmiany – w oryginale było np. self.grubosc_input.currentIndexChanged.connect(self.update_v_input)
        # Upewnij się, że nie zostało to usunięte
        self.grubosc_input.currentIndexChanged.connect(self.update_v_input)

        self.layout.addWidget(QLabel("Grubość [mm]:"))
        self.layout.addWidget(self.grubosc_input)

        self.V_input = QComboBox()
        self.layout.addWidget(QLabel("V [mm]:"))
        self.layout.addWidget(self.V_input)

        self.material_input = QComboBox()
        self.material_input.addItems(["CZ", "N"])
        self.layout.addWidget(QLabel("Materiał:"))
        self.layout.addWidget(self.material_input)

    def populate_comboboxes(self, data: pd.DataFrame):
        self.data = data
        grubosc_values = sorted(data['Grubosc'].unique())
        self.grubosc_input.clear()
        self.grubosc_input.addItems([str(x) for x in grubosc_values])
        if grubosc_values:
            self.update_v_input()  # wywołanie "ręcznie" na starcie

    def update_v_input(self):
        print("DEBUG: update_v_input() wywołane.")
        selected_grubosc_str = self.grubosc_input.currentText()
        if not selected_grubosc_str:
            print("DEBUG: Brak wybranej grubości w comboboxie.")
            return

        try:
            selected_grubosc_float = float(selected_grubosc_str)
        except ValueError:
            print(f"DEBUG: Nie można skonwertować '{selected_grubosc_str}' na float.")
            return

        # Wyciągamy z DataFrame wszystkie szerokości V odpowiadające wybranej grubości
        widths_from_data = sorted(set(self.data.loc[self.data['Grubosc'] == selected_grubosc_float, 'V']))
        print("DEBUG: widths_from_data dla grubości =", selected_grubosc_float, "to:", widths_from_data)

        # Filtrowanie przez config
        allowed_widths = filter_matrix_widths(selected_grubosc_float, widths_from_data)
        print("DEBUG: allowed_widths po filtrze =", allowed_widths)

        self.V_input.clear()
        if not allowed_widths:
            print("DEBUG: Brak szerokości w configu dla tej grubości. Dodam cokolwiek albo zostawię puste.")
            return
        self.V_input.addItems([str(v) for v in allowed_widths])
        print("DEBUG: Combobox V_input wypełniony:", [str(v) for v in allowed_widths])
