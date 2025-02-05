# data/data_editor.py
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem, QHBoxLayout, QPushButton, QMessageBox
)
from PyQt5.QtGui import QIcon
import pandas as pd
from data.data_loader import save_data_to_json
from utils.utils import parse_decimal_input

def safe_to_numeric(value):
    """Bezpieczna konwersja wartości na liczbę dziesiętną."""
    try:
        value = parse_decimal_input(value)
        return pd.to_numeric(value)
    except ValueError:
        return value

DATA_FILE = 'Ubytki.xlsx'

class DataEditorDialog(QDialog):
    """Okno dialogowe do edycji danych treningowych."""
    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edycja Danych Treningowych")
        self.data = data.copy()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Tabela danych
        self.table = QTableWidget(len(self.data), len(self.data.columns))
        self.table.setHorizontalHeaderLabels(self.data.columns)

        for row, (_, row_data) in enumerate(self.data.iterrows()):
            for col, value in enumerate(row_data):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

        self.table.resizeColumnsToContents()

        total_column_width = sum(self.table.columnWidth(col) for col in range(self.table.columnCount()))
        total_column_width += self.table.verticalHeader().width() + 20

        row_height = self.table.rowHeight(0) if self.table.rowCount() > 0 else 30
        header_height = self.table.horizontalHeader().height()
        total_height = header_height + (row_height * 15) + 40

        self.resize(total_column_width, total_height)
        layout.addWidget(self.table)

        button_layout = QHBoxLayout()

        add_button = QPushButton("Dodaj Wiersz")
        add_button.setIcon(QIcon("resources/icons/add.png"))
        add_button.clicked.connect(self.add_row)
        button_layout.addWidget(add_button)

        remove_button = QPushButton("Usuń Wiersz")
        remove_button.setIcon(QIcon("resources/icons/remove.png"))
        remove_button.clicked.connect(self.remove_row)
        button_layout.addWidget(remove_button)

        up_button = QPushButton("Góra")
        up_button.setIcon(QIcon("resources/icons/up.png"))
        up_button.clicked.connect(self.move_row_up)
        button_layout.addWidget(up_button)

        down_button = QPushButton("Dół")
        down_button.setIcon(QIcon("resources/icons/down.png"))
        down_button.clicked.connect(self.move_row_down)
        button_layout.addWidget(down_button)

        save_button = QPushButton("Zapisz Zmiany")
        save_button.setIcon(QIcon("resources/icons/save.png"))
        save_button.clicked.connect(self.save_changes)
        button_layout.addWidget(save_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def add_row(self):
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)

    def remove_row(self):
        selected_rows = set(idx.row() for idx in self.table.selectionModel().selectedIndexes())
        for row in sorted(selected_rows, reverse=True):
            self.table.removeRow(row)

    def move_row_up(self):
        current_row = self.table.currentRow()
        if current_row > 0:
            self.swap_rows(current_row, current_row - 1)
            self.table.selectRow(current_row - 1)

    def move_row_down(self):
        current_row = self.table.currentRow()
        if current_row < self.table.rowCount() - 1:
            self.swap_rows(current_row, current_row + 1)
            self.table.selectRow(current_row + 1)

    def swap_rows(self, row1, row2):
        for col in range(self.table.columnCount()):
            item1 = self.table.item(row1, col)
            item2 = self.table.item(row2, col)
            value1 = item1.text() if item1 else ""
            value2 = item2.text() if item2 else ""
            self.table.setItem(row1, col, QTableWidgetItem(value2))
            self.table.setItem(row2, col, QTableWidgetItem(value1))

    def save_changes(self):
        try:
            rows = self.table.rowCount()
            cols = self.table.columnCount()
            new_data = []

            for row in range(rows):
                row_data = []
                for col in range(cols):
                    item = self.table.item(row, col)
                    value = item.text() if item else ""
                    row_data.append(value)
                new_data.append(row_data)

            new_data = pd.DataFrame(new_data, columns=self.data.columns)
            new_data = new_data.apply(lambda x: x.map(safe_to_numeric))

            save_data_to_json(new_data)
            self.parent().data = new_data

            print(f"Model przekazany z obiektu nadrzędnego: {getattr(self.parent(), 'model', None)}")
            if hasattr(self.parent(), "model") and self.parent().model is not None:
                self.parent().model.train_models(new_data, force_retrain=True)
                print("Model przetrenowano na nowych danych.")
            else:
                print("Nie znaleziono modelu w obiekcie nadrzędnym.")

            QMessageBox.information(self, "Sukces", "Dane zapisano i modele przetrenowano.")
            self.accept()

        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie udało się zapisać danych: {e}")
