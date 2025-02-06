# ui/segment_manager.py
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QPushButton, QLabel, QMessageBox
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QPen, QColor

class SegmentManager:
    def __init__(self, parent, model):
        self.parent = parent
        self.model = model

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Długość [mm]", "Kąt gięcia [°]", "BD [mm]", ""])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(3, 30)

        self.result_label = QLabel()
        self.result_label.setAlignment(Qt.AlignCenter)

        self.calculate_button = QPushButton("Oblicz Łączną Długość")
        self.calculate_button.clicked.connect(self.calculate_total_bd)

        self.remove_all_plus_rows()
        self.ensure_plus_row()

    def remove_all_plus_rows(self):
        for row in range(self.table.rowCount() - 1, -1, -1):
            widget = self.table.cellWidget(row, 0)
            if widget is not None and getattr(widget, 'plus_row', False):
                self.table.removeRow(row)

    def ensure_plus_row(self):
        row_count = self.table.rowCount()
        if row_count > 0:
            widget = self.table.cellWidget(row_count - 1, 0)
            if widget is not None and getattr(widget, 'plus_row', False):
                return
        self.add_plus_row()

    def add_plus_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        plus_button = QPushButton("+")
        plus_button.setStyleSheet(
            "QPushButton { background-color: green; color: white; font-weight: bold; max-width: 30px; }"
        )
        plus_button.plus_row = True
        plus_button.clicked.connect(self.add_segment_via_plus)
        self.table.setCellWidget(row, 0, plus_button)
        for col in range(1, 4):
            self.table.setItem(row, col, QTableWidgetItem(""))

    def add_segment_via_plus(self):
        self.remove_all_plus_rows()
        self.insert_segment_row(self.table.rowCount(), absolute_x=100.0)
        self.add_plus_row()
        self.recalc_segments()

    def insert_segment_row(self, row, absolute_x, default_angle=90, line_id=None):
        self.table.insertRow(row)

        dlugosc_item = QTableWidgetItem(f"{absolute_x:.2f}")
        dlugosc_item.setData(Qt.UserRole + 1, absolute_x)
        if line_id is not None:
            dlugosc_item.setData(Qt.UserRole, line_id)
        self.table.setItem(row, 0, dlugosc_item)

        kat_item = QTableWidgetItem(str(default_angle))
        self.table.setItem(row, 1, kat_item)

        bd_item = QTableWidgetItem("")
        bd_item.setFlags(Qt.ItemIsEnabled)
        self.table.setItem(row, 2, bd_item)

        remove_button = QPushButton("-")
        remove_button.setStyleSheet(
            "QPushButton { background-color: red; color: white; font-weight: bold; max-width: 30px; }"
        )
        remove_button.clicked.connect(self.remove_segment_by_button)
        self.table.setCellWidget(row, 3, remove_button)

    def insert_segment_sorted(self, new_x, line_id):
        insertion_index = self.table.rowCount() - 1
        for row in range(self.table.rowCount() - 1):
            item = self.table.item(row, 0)
            if item is not None:
                existing_x = item.data(Qt.UserRole + 1)
                if existing_x is None:
                    existing_x = 0.0
                if new_x < existing_x:
                    insertion_index = row
                    break
        self.insert_segment_row(insertion_index, absolute_x=new_x, default_angle=90, line_id=line_id)
        self.recalc_segments()

    def recalc_segments(self):
        n = self.table.rowCount() - 1
        if n <= 0:
            return
        segments = []
        for row in range(self.table.rowCount() - 1):
            item = self.table.item(row, 0)
            if item:
                absolute_x = item.data(Qt.UserRole + 1)
                segments.append((row, absolute_x))
        segments.sort(key=lambda x: x[1])

        prev_x = None
        for (row, absolute_x) in segments:
            if prev_x is None:
                segment_value = absolute_x
            else:
                segment_value = absolute_x - prev_x
            prev_x = absolute_x
            self.table.item(row, 0).setText(f"{segment_value:.2f}")

    def remove_segment_by_button(self):
        button = self.table.sender()
        if not button:
            return

        # Szukamy wiersza
        row_to_remove = None
        for row in range(self.table.rowCount()):
            widget = self.table.cellWidget(row, 3)
            if widget == button:
                row_to_remove = row
                break
        if row_to_remove is None:
            return

        # Sprawdzamy identyfikator linii gięcia
        item = self.table.item(row_to_remove, 0)
        if item is not None:
            line_id = item.data(Qt.UserRole)
            if line_id is not None:
                from PyQt5.QtWidgets import QGraphicsLineItem
                # Iterujemy po TEJ SAMEJ scenie:
                for scene_item in list(self.parent.dxf_view.scene().items()):
                    if (isinstance(scene_item, QGraphicsLineItem) and
                        scene_item.data(1) == "selected" and
                        id(scene_item) == line_id):
                        pen = QPen(QColor("yellow"))
                        scene_item.setPen(pen)
                        scene_item.setData(1, None)
                        print("Minus clicked: Unselected bending line with id", line_id)
                        break

        self.table.removeRow(row_to_remove)
        if self.table.rowCount() == 0:
            self.add_plus_row()
        else:
            self.recalc_segments()

    def calculate_total_bd(self):
        try:
            material = self.parent.parameter_manager.material_input.currentText()
            total_length = 0.0
            total_bd = 0.0
            for row in range(self.table.rowCount() - 1):
                dlugosc_item = self.table.item(row, 0)
                kat_item = self.table.item(row, 1)
                if dlugosc_item and kat_item:
                    dlugosc = float(dlugosc_item.text())
                    kat = float(kat_item.text())
                    grubosc = float(self.parent.parameter_manager.grubosc_input.currentText())
                    V = float(self.parent.parameter_manager.V_input.currentText())
                    bd_value = 0.0 if kat == 0 else self.model.oblicz_bd(grubosc, V, kat, material)
                    total_length += dlugosc
                    total_bd += bd_value
                    bd_item = QTableWidgetItem(f"{bd_value:.2f}")
                    bd_item.setFlags(Qt.ItemIsEnabled)
                    self.table.setItem(row, 2, bd_item)

            self.parent.segment_result_label.setText(
                f"Łączna Długość: {total_length:.2f} mm\nŁączny Ubytek (BD): {total_bd:.2f} mm"
            )
        except Exception as e:
            QMessageBox.warning(self.parent, "Błąd", f"Wystąpił błąd podczas obliczania BD:\n{e}")

    def find_segment_row_by_line_id(self, line_id):
        for row in range(self.table.rowCount() - 1):
            item = self.table.item(row, 0)
            if item and item.data(Qt.UserRole) == line_id:
                return row
        return None

    def handle_bending_line_click_in_segment_table(self, item, clicked_point):
        """Metoda wywoływana z main_window.handle_bending_line_click."""
        from PyQt5.QtGui import QPen

        # Sprawdzamy, czy linia jest "selected"
        if item.data(1) == "selected":
            row_index = self.find_segment_row_by_line_id(id(item))
            if row_index is not None:
                self.table.removeRow(row_index)
            item.setData(1, None)
            pen = QPen(QColor("yellow"))
            item.setPen(pen)
            self.recalc_segments()
            print("Unselected bending line. Segment removed.")
            return
        # Inaczej – zaznaczamy
        item.setData(1, "selected")
        pen = QPen(QColor("magenta"))
        pen.setWidth(2)
        item.setPen(pen)
        self.insert_segment_sorted(clicked_point.x(), line_id=id(item))
        print("Selected bending line. New segment inserted.")
