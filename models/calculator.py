# models/calculator.py
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt

class BDUbytkiCalculator:
    def __init__(self, model):
        self.model = model

    def calculate(self, grubosc, V, material, table):
        """Oblicza łączną długość, całkowity ubytek materiału i efektywną długość."""
        total_length = 0.0
        total_bd = 0.0
        total_effective_length = 0.0

        for row in range(table.rowCount()):
            dlugosc_item = table.item(row, 0)
            kat_item = table.item(row, 1)

            if not dlugosc_item or not kat_item:
                raise ValueError(f"Puste pola w wierszu {row + 1}.")

            dlugosc = float(dlugosc_item.text())
            kat = float(kat_item.text())
            grubosc = float(grubosc)
            V = float(V.strip("[]"))

            if kat == 0:
                bd_value = 0.0
            else:
                bd_value = self.model.oblicz_bd(grubosc, V, kat, material)

            total_length += dlugosc
            total_bd += bd_value
            total_effective_length += max(dlugosc - bd_value, 0)

            bd_item = table.item(row, 2) or QTableWidgetItem()
            bd_item.setText(f"{bd_value:.2f}")
            bd_item.setFlags(Qt.ItemIsEnabled)
            table.setItem(row, 2, bd_item)

        return total_length, total_bd, total_effective_length
