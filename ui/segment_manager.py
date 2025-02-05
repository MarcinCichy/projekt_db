# ui/segment_manager.py
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt

class SegmentManager:
    def __init__(self, parent):
        self.parent = parent
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Długość [mm]", "Kąt gięcia [°]", "BD [mm]"])

    def calculate_total_bd(self, params, model):
        """Oblicza całkowity ubytek materiału."""
        total_length, total_bd = 0.0, 0.0

        for row in range(self.table.rowCount()):
            length_item = self.table.item(row, 0)
            angle_item = self.table.item(row, 1)

            if not length_item or not angle_item:
                continue

            length = float(length_item.text())
            angle = float(angle_item.text())
            bd = model.oblicz_bd(float(params["grubosc"]), float(params["V"]), angle, params["material"])

            total_length += length
            total_bd += bd

            bd_item = QTableWidgetItem(f"{bd:.2f}")
            bd_item.setFlags(Qt.ItemIsEnabled)
            self.table.setItem(row, 2, bd_item)

        return f"Łączna długość: {total_length} mm\nUbytek: {total_bd} mm"
