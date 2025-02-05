# ui/matrix_config_editor.py
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QPushButton, QMessageBox
from PyQt5.QtCore import Qt
import json
import os

CONFIG_FILE = "config/matrix_config.json"

def load_matrix_config():
    """Wczytuje konfigurację matryc z pliku JSON."""
    try:
        with open(CONFIG_FILE, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        print(f"Błąd wczytywania konfiguracji matryc: {e}")
        return {}

def save_matrix_config(config):
    """Zapisuje konfigurację matryc do pliku JSON."""
    try:
        with open(CONFIG_FILE, "w") as file:
            json.dump(config, file, indent=4)
            print(f"Zapisano konfigurację matryc w {CONFIG_FILE}")
    except Exception as e:
        print(f"Błąd zapisu konfiguracji matryc: {e}")

class MatrixConfigEditor(QDialog):
    """Okno przypisywania matryc do grubości materiału."""
    def __init__(self, grubosci, matryce, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Przypisz Matryce")
        self.grubosci = grubosci
        self.matryce = matryce
        self.config = load_matrix_config()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.table = QTableWidget(len(self.grubosci), len(self.matryce))
        self.table.setHorizontalHeaderLabels([str(m) for m in self.matryce])
        self.table.setVerticalHeaderLabels([str(g) for g in self.grubosci])

        for row, grubosc in enumerate(self.grubosci):
            for col, matryca in enumerate(self.matryce):
                item = QTableWidgetItem()
                item.setCheckState(Qt.Checked if str(grubosc) in self.config and matryca in self.config[str(grubosc)] else Qt.Unchecked)
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()

        total_column_width = sum(self.table.columnWidth(col) for col in range(self.table.columnCount()))
        total_column_width += self.table.verticalHeader().width() + 40

        row_height = self.table.rowHeight(0) if self.table.rowCount() > 0 else 30
        header_height = self.table.horizontalHeader().height()
        total_height = header_height + (row_height * len(self.grubosci)) + 60

        self.resize(total_column_width, total_height)
        layout.addWidget(self.table)

        save_button = QPushButton("Zapisz")
        save_button.clicked.connect(self.save_config)
        layout.addWidget(save_button)

        self.setLayout(layout)

    def save_config(self):
        """Zapisuje nową konfigurację."""
        new_config = {}
        for row, grubosc in enumerate(self.grubosci):
            selected_matryce = []
            for col, matryca in enumerate(self.matryce):
                item = self.table.item(row, col)
                if item and item.checkState() == Qt.Checked:
                    selected_matryce.append(matryca)
            new_config[str(grubosc)] = selected_matryce

        save_matrix_config(new_config)
        QMessageBox.information(self, "Sukces", "Konfiguracja matryc została zapisana.")
        self.accept()
