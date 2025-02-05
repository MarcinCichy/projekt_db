# ui/main_window.py
from PyQt5.QtWidgets import (
    QMainWindow, QVBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QMessageBox, QComboBox, QHBoxLayout, QWidget,
    QGraphicsView, QGraphicsScene, QFileDialog, QGraphicsLineItem, QAction
)
from PyQt5.QtCore import Qt, QPoint, QPointF, QRectF, QLineF
from PyQt5.QtGui import QPainter, QPen, QColor, QPainterPath
import ezdxf


class CustomGraphicsView(QGraphicsView):
    """QGraphicsView z manualnym panningiem i obsługą kursora:
       - Domyślnie kursor to strzałka (Qt.ArrowCursor)
       - Podczas przytrzymania lewego przycisku – kursor zmienia się na rączkę (Qt.ClosedHandCursor)
       - Po puszczeniu – kursor wraca do strzałki.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setRenderHint(QPainter.Antialiasing)
        # Wyłączamy automatyczny tryb dragowania – używamy własnego panningu
        self.setDragMode(QGraphicsView.NoDrag)
        self.setInteractive(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self._mouse_pressed_position = QPoint()
        self._panStart = QPoint()
        self._isPanning = False
        self.padding = 500
        self.setCursor(Qt.ArrowCursor)
        self.main_window = None

    def set_scene_padding(self):
        if self.scene() is not None:
            original_rect = self.scene().itemsBoundingRect()
            padded_rect = original_rect.adjusted(-self.padding, -self.padding, self.padding, self.padding)
            self.scene().setSceneRect(padded_rect)

    def _distance_to_point(self, line: QLineF, point: QPointF) -> float:
        A = line.p1()
        B = line.p2()
        P = point
        AB = B - A
        AP = P - A
        ab2 = AB.x() ** 2 + AB.y() ** 2
        if ab2 == 0:
            return (AP.x() ** 2 + AP.y() ** 2) ** 0.5
        t = (AP.x() * AB.x() + AP.y() * AB.y()) / ab2
        if t < 0:
            closest = A
        elif t > 1:
            closest = B
        else:
            closest = QPointF(A.x() + t * AB.x(), A.y() + t * AB.y())
        dx = P.x() - closest.x()
        dy = P.y() - closest.y()
        return (dx * dx + dy * dy) ** 0.5

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._mouse_pressed_position = event.pos()
            self._panStart = event.pos()
            self._isPanning = True
            self.viewport().setCursor(Qt.ClosedHandCursor)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._isPanning:
            # Obliczamy przesunięcie delta w widoku i stosujemy translate() do GUW
            delta = event.pos() - self._panStart
            self._panStart = event.pos()
            self.translate(delta.x(), delta.y())
        if self.main_window is not None:
            scene_pos = self.mapToScene(event.pos())
            self.main_window.update_status_bar(scene_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.viewport().setCursor(Qt.ArrowCursor)
            if (event.pos() - self._mouse_pressed_position).manhattanLength() < 10:
                try:
                    pos = self.mapToScene(event.pos())
                    print("Mouse released at scene pos:", pos)
                    tolerance = 20.0
                    search_rect = QRectF(pos.x() - tolerance, pos.y() - tolerance, tolerance * 2, tolerance * 2)
                    items = self.scene().items(search_rect, Qt.IntersectsItemShape)
                    closest_item = None
                    closest_distance = tolerance
                    for item in items:
                        if isinstance(item, QGraphicsLineItem) and item.data(0) == "bending":
                            p1 = item.mapToScene(item.line().p1())
                            p2 = item.mapToScene(item.line().p2())
                            qline = QLineF(p1, p2)
                            distance = self._distance_to_point(qline, pos)
                            print("Found bending line with distance:", distance)
                            if distance < closest_distance:
                                closest_distance = distance
                                closest_item = item
                    if closest_item is not None:
                        p1 = closest_item.mapToScene(closest_item.line().p1())
                        p2 = closest_item.mapToScene(closest_item.line().p2())
                        qline = QLineF(p1, p2)
                        clicked_point = QPointF((qline.x1() + qline.x2()) / 2, (qline.y1() + qline.y2()) / 2)
                        print("Closest bending line found. Center at:", clicked_point)
                        if self.main_window:
                            self.main_window.handle_bending_line_click(closest_item, clicked_point)
                    else:
                        print("No bending line found within tolerance.")
                except Exception as e:
                    print("Exception in mouseReleaseEvent:", e)
            self._isPanning = False
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        zoom_in_factor = 1.1
        zoom_out_factor = 1 / zoom_in_factor
        if event.angleDelta().y() > 0:
            self.scale(zoom_in_factor, zoom_in_factor)
        else:
            self.scale(zoom_out_factor, zoom_out_factor)


class MainWindow(QMainWindow):
    def __init__(self, data, model, matrix_config_editor, data_editor):
        super().__init__()
        self.setWindowTitle("Kalkulator Ubytku Materiału BD")
        self.data = data
        self.model = model
        self.matrix_config_editor = matrix_config_editor
        self.data_editor = data_editor
        self.last_selected_x = None
        self.dxf_scene = QGraphicsScene()
        self.init_ui()
        self.create_menus()
        self.showMaximized()

    def init_ui(self):
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("X: 0.00, Y: 0.00")
        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout()

        # Lewa sekcja – parametry i tabela segmentów
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        params_layout = QHBoxLayout()
        self.grubosc_input = QComboBox()
        self.grubosc_input.currentIndexChanged.connect(self.update_v_input)
        params_layout.addWidget(QLabel("Grubość [mm]:"))
        params_layout.addWidget(self.grubosc_input)
        self.V_input = QComboBox()
        params_layout.addWidget(QLabel("V [mm]:"))
        params_layout.addWidget(self.V_input)
        self.material_input = QComboBox()
        self.material_input.addItems(["CZ", "N"])
        params_layout.addWidget(QLabel("Materiał:"))
        params_layout.addWidget(self.material_input)
        left_layout.addLayout(params_layout)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Długość [mm]", "Kąt gięcia [°]", "BD [mm]", ""])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setColumnWidth(3, 30)
        left_layout.addWidget(self.table)
        self.table.setRowCount(0)
        self.last_selected_x = None
        self.remove_all_plus_rows()
        self.ensure_plus_row()
        self.calculate_button = QPushButton("Oblicz Łączną Długość")
        self.calculate_button.clicked.connect(self.calculate_total_bd)
        left_layout.addWidget(self.calculate_button)
        self.result_label = QLabel()
        self.result_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.result_label)
        left_widget.setLayout(left_layout)
        left_widget.setFixedWidth(400)

        # Prawa sekcja – widok DXF
        right_widget = QWidget()
        right_layout = QVBoxLayout()
        load_dxf_button = QPushButton("Wczytaj Plik DXF")
        load_dxf_button.clicked.connect(self.load_dxf_file)
        right_layout.addWidget(load_dxf_button)
        self.dxf_view = CustomGraphicsView()
        self.dxf_view.setScene(self.dxf_scene)
        # Ustawiamy alignment na środek – GUW początkowo wycentrowany
        self.dxf_view.setAlignment(Qt.AlignCenter)
        self.dxf_view.setDragMode(QGraphicsView.NoDrag)
        self.dxf_view.main_window = self
        right_layout.addWidget(self.dxf_view)
        right_widget.setLayout(right_layout)
        self.main_layout.addWidget(left_widget, stretch=1)
        self.main_layout.addWidget(right_widget, stretch=3)
        self.main_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.main_widget)

    def create_menus(self):
        menubar = self.menuBar()
        konfiguracja_menu = menubar.addMenu("Konfiguracja")
        matrix_config_action = QAction("Konfiguracja matryc", self)
        matrix_config_action.triggered.connect(self.openMatrixConfigEditor)
        konfiguracja_menu.addAction(matrix_config_action)
        data_editor_action = QAction("Edycja danych treningowych", self)
        data_editor_action.triggered.connect(self.openDataEditor)
        konfiguracja_menu.addAction(data_editor_action)

    def openMatrixConfigEditor(self):
        self.matrix_config_editor.exec_()
        self.update_v_input()

    def openDataEditor(self):
        self.data_editor.exec_()

    def update_status_bar(self, pos: QPointF):
        msg = f"X: {pos.x():.2f}, Y: {pos.y():.2f}"
        self.status_bar.showMessage(msg)

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
            "QPushButton { background-color: green; color: white; font-weight: bold; max-width: 30px; }")
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
        kat_item = QTableWidgetItem(f"{default_angle}")
        self.table.setItem(row, 1, kat_item)
        bd_item = QTableWidgetItem("")
        bd_item.setFlags(Qt.ItemIsEnabled)
        self.table.setItem(row, 2, bd_item)
        remove_button = QPushButton("-")
        remove_button.setStyleSheet(
            "QPushButton { background-color: red; color: white; font-weight: bold; max-width: 30px; }")
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
            if item is not None:
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

    def find_segment_row_by_line_id(self, line_id):
        for row in range(self.table.rowCount() - 1):
            item = self.table.item(row, 0)
            if item is not None and item.data(Qt.UserRole) == line_id:
                return row
        return None

    def remove_segment_by_button(self):
        button = self.sender()
        if button:
            for row in range(self.table.rowCount()):
                widget = self.table.cellWidget(row, 3)
                if widget is button:
                    item = self.table.item(row, 0)
                    if item is not None:
                        line_id = item.data(Qt.UserRole)
                        if line_id is not None:
                            for scene_item in list(self.dxf_scene.items()):
                                if (isinstance(scene_item, QGraphicsLineItem) and
                                        scene_item.data(1) == "selected" and
                                        id(scene_item) == line_id):
                                    pen = QPen(QColor("yellow"))
                                    scene_item.setPen(pen)
                                    scene_item.setData(1, None)
                                    print("Minus clicked: Unselected bending line with id", line_id)
                                    break
                    self.table.removeRow(row)
                    break
        if self.table.rowCount() == 0:
            self.add_plus_row()
        else:
            self.recalc_segments()

    def load_dxf_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz Plik DXF", "", "Pliki DXF (*.dxf)")
        if not file_path:
            return
        try:
            self.table.setRowCount(0)
            self.last_selected_x = None
            self.remove_all_plus_rows()
            self.ensure_plus_row()
            doc = ezdxf.readfile(file_path)
            self.dxf_scene.clear()
            for entity in doc.modelspace():
                if entity.dxftype() == 'LINE':
                    start = entity.dxf.start
                    end = entity.dxf.end
                    if hasattr(entity.dxf, 'color') and entity.dxf.color == 2:
                        pen = QPen(QColor("yellow"))
                        bending_line = QGraphicsLineItem(start.x, start.y, end.x, end.y)
                        bending_line.setPen(pen)
                        bending_line.setData(0, "bending")
                        self.dxf_scene.addItem(bending_line)
                    else:
                        self.dxf_scene.addLine(start.x, start.y, end.x, end.y)
                elif entity.dxftype() == 'CIRCLE':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    self.dxf_scene.addEllipse(center.x - radius, center.y - radius, 2 * radius, 2 * radius)
                elif entity.dxftype() == 'ARC':
                    center = entity.dxf.center
                    radius = entity.dxf.radius
                    start_angle = entity.dxf.start_angle
                    end_angle = entity.dxf.end_angle
                    rect = QRectF(center.x - radius, center.y - radius, 2 * radius, 2 * radius)
                    path = QPainterPath()
                    path.arcMoveTo(rect, start_angle)
                    path.arcTo(rect, start_angle, (end_angle - start_angle))
                    self.dxf_scene.addPath(path)
                elif entity.dxftype() == 'POLYLINE':
                    points = list(entity.points())
                    for i in range(len(points) - 1):
                        self.dxf_scene.addLine(points[i][0], points[i][1],
                                               points[i + 1][0], points[i + 1][1])
                elif entity.dxftype() == 'LWPOLYLINE':
                    points = list(entity.points())
                    for i in range(len(points)):
                        start_point = points[i]
                        end_point = points[(i + 1) % len(points)]
                        bulge = start_point[4] if len(start_point) > 4 else 0
                        if bulge == 0:
                            self.dxf_scene.addLine(start_point[0], start_point[1],
                                                   end_point[0], end_point[1])
                        else:
                            self.draw_bulge_arc(start_point, end_point, bulge)
                else:
                    print(f"Nieobsługiwany typ: {entity.dxftype()}")
            # Ustalamy LUW: przesuwamy elementy sceny, aby lewy dolny róg geometrii (LUW) był w (0,0)
            self.adjust_scene_origin()
            # GUW: Reset transformacji, odwrócenie osi Y, wycentrowanie rysunku
            self.dxf_view.resetTransform()
            self.dxf_view.scale(1, -1)
            self.center_dxf_in_view()
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie udało się wczytać pliku DXF:\n{e}")

    def draw_bulge_arc(self, start_point, end_point, bulge):
        import math
        chord_length = math.sqrt((end_point[0] - start_point[0]) ** 2 + (end_point[1] - start_point[1]) ** 2)
        radius = abs(chord_length / (2 * math.sin(2 * math.atan(bulge))))
        center_x = (start_point[0] + end_point[0]) / 2
        center_y = (start_point[1] + end_point[1]) / 2
        angle_start = math.degrees(math.atan2(start_point[1] - center_y, start_point[0] - center_x))
        angle_end = math.degrees(math.atan2(end_point[1] - center_y, end_point[0] - center_x))
        rect = QRectF(center_x - radius, -center_y - radius, 2 * radius, 2 * radius)
        path = QPainterPath()
        path.arcMoveTo(rect, angle_start)
        path.arcTo(rect, angle_start, angle_end - angle_start)
        self.dxf_scene.addPath(path)

    def adjust_scene_origin(self):
        """Przesuwa rysunek tak, aby LUW miało (0,0) w lewym dolnym rogu geometrii.
           Dla rysunków AutoCada przyjmujemy:
             min_x = bounding_rect.left()
             min_y = bounding_rect.top()
        """
        bounding_rect = self.dxf_scene.itemsBoundingRect()
        print("Before adjust_scene_origin, bounding_rect:", bounding_rect)
        min_x = bounding_rect.left()
        min_y = bounding_rect.top()
        dx = -min_x
        dy = -min_y
        print(f"Przesuwam rysunek o dx={dx}, dy={dy}, aby LUW (0,0) był w lewym dolnym rogu.")
        for item in list(self.dxf_scene.items()):
            item.moveBy(dx, dy)
        new_rect = self.dxf_scene.itemsBoundingRect()

        # Dodajemy margines, aby scena była większa niż sama geometria rysunku –
        # to umożliwi panning nawet, gdy rysunek mieści się w oknie.
        margin = 5000  # Możesz dostosować tę wartość
        new_rect = new_rect.adjusted(-margin, -margin, margin, margin)

        self.dxf_scene.setSceneRect(new_rect)
        print("After adjust_scene_origin, sceneRect:", self.dxf_scene.sceneRect())

    def center_dxf_in_view(self):
        """GUW: Centruje rysunek (bez modyfikacji LUW) przy pomocy transformacji widoku."""
        # Resetujemy transformację, a następnie obliczamy przesunięcie,
        # aby środek sceny (LUW) znalazł się w środku widoku (GUW).
        self.dxf_view.resetTransform()
        self.dxf_view.scale(1, -1)
        view_center = self.mapToScene(self.dxf_view.viewport().rect().center())
        scene_center = self.dxf_scene.sceneRect().center()
        offset = scene_center - view_center
        self.dxf_view.translate(offset.x(), offset.y())

    def handle_bending_line_click(self, item, clicked_point):
        new_line_x = clicked_point.x()
        print("handle_bending_line_click - clicked_point:", clicked_point)
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
        print("Selecting bending line with x =", new_line_x)
        item.setData(1, "selected")
        pen = QPen(QColor("magenta"))
        pen.setWidth(2)
        item.setPen(pen)
        self.insert_segment_sorted(new_line_x, line_id=id(item))
        print("Selected bending line. New segment inserted.")

    def update_v_input(self):
        selected_grubosc = self.grubosc_input.currentText()
        if self.data is not None:
            try:
                V_values = sorted(set(self.data.loc[self.data['Grubosc'] == float(selected_grubosc), 'V']))
            except ValueError:
                V_values = []
            self.V_input.clear()
            self.V_input.addItems([str(x) for x in V_values])

    def recalc_segments(self):
        n = self.table.rowCount() - 1
        if n <= 0:
            return
        segments = []
        for row in range(self.table.rowCount() - 1):
            item = self.table.item(row, 0)
            if item is not None:
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

    def find_segment_row_by_line_id(self, line_id):
        for row in range(self.table.rowCount() - 1):
            item = self.table.item(row, 0)
            if item is not None and item.data(Qt.UserRole) == line_id:
                return row
        return None

    def remove_segment_by_button(self):
        button = self.sender()
        if button:
            for row in range(self.table.rowCount()):
                widget = self.table.cellWidget(row, 3)
                if widget is button:
                    item = self.table.item(row, 0)
                    if item is not None:
                        line_id = item.data(Qt.UserRole)
                        if line_id is not None:
                            for scene_item in list(self.dxf_scene.items()):
                                if (isinstance(scene_item, QGraphicsLineItem) and
                                        scene_item.data(1) == "selected" and
                                        id(scene_item) == line_id):
                                    pen = QPen(QColor("yellow"))
                                    scene_item.setPen(pen)
                                    scene_item.setData(1, None)
                                    print("Minus clicked: Unselected bending line with id", line_id)
                                    break
                    self.table.removeRow(row)
                    break
        if self.table.rowCount() == 0:
            self.add_plus_row()
        else:
            self.recalc_segments()

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

    def add_segment_via_plus_with_defaults(self, default_length=100, default_angle=90, line_id=None):
        self.remove_all_plus_rows()
        plus_row_index = self.table.rowCount()
        self.insert_segment_row(plus_row_index, absolute_x=default_length, default_angle=default_angle, line_id=line_id)
        self.add_plus_row()
        self.recalc_segments()

    def calculate_total_bd(self):
        try:
            material = self.material_input.currentText()
            total_length = 0.0
            total_bd = 0.0
            for row in range(self.table.rowCount() - 1):
                dlugosc_item = self.table.item(row, 0)
                kat_item = self.table.item(row, 1)
                if not dlugosc_item or not kat_item:
                    continue
                dlugosc = float(dlugosc_item.text())
                kat = float(kat_item.text())
                grubosc = float(self.grubosc_input.currentText())
                V = float(self.V_input.currentText())
                bd_value = 0.0 if kat == 0 else self.model.oblicz_bd(grubosc, V, kat, material)
                total_length += dlugosc
                total_bd += bd_value
                bd_item = QTableWidgetItem(f"{bd_value:.2f}")
                bd_item.setFlags(Qt.ItemIsEnabled)
                self.table.setItem(row, 2, bd_item)
            self.result_label.setText(
                f"Łączna Długość: {total_length:.2f} mm\nŁączny Ubytek (BD): {total_bd:.2f} mm"
            )
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Wystąpił błąd podczas obliczania BD:\n{e}")

    def populate_comboboxes(self):
        if self.data is not None:
            grubosc_values = sorted(self.data['Grubosc'].unique())
            self.grubosc_input.clear()
            self.grubosc_input.addItems([str(x) for x in grubosc_values])
            if grubosc_values:
                self.update_v_input()

    def center_dxf_in_view(self):
        """GUW: Centruje rysunek (bez modyfikacji LUW) przy pomocy transformacji widoku.
           Oblicza przesunięcie między środkiem sceny a środkiem widoku i stosuje translate().
        """
        # Reset transformacji, zachowując ustawienie LUW (transformacja LUW pozostaje)
        self.dxf_view.resetTransform()
        # Najpierw odwracamy oś Y, aby współrzędne rosnęły w górę
        self.dxf_view.scale(1, -1)
        # Obliczamy środek widoku (w punktach widoku) i przeliczamy na współrzędne sceny
        view_center = self.dxf_view.mapToScene(self.dxf_view.viewport().rect().center())
        scene_center = self.dxf_scene.sceneRect().center()
        offset = scene_center - view_center
        self.dxf_view.translate(offset.x(), offset.y())


# Koniec pliku
