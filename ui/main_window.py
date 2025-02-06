# ui/main_window.py
from PyQt5.QtWidgets import (
    QMainWindow, QHBoxLayout, QWidget, QVBoxLayout, QPushButton, QAction,
    QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QPointF

from ui.dxf_view import CustomGraphicsView
from ui.parameter_manager import ParameterManager
from ui.segment_manager import SegmentManager


class MainWindow(QMainWindow):
    def __init__(self, data, model, matrix_config_editor, data_editor):
        super().__init__()
        self.setWindowTitle("Kalkulator Ubytku Materiału BD")
        self.data = data
        self.model = model
        self.matrix_config_editor = matrix_config_editor
        self.data_editor = data_editor

        self.init_ui()
        self.create_menus()

        # Uruchamiamy na pełnym ekranie
        self.showMaximized()

    def init_ui(self):
        self.statusBar().showMessage("X: 0.00, Y: 0.00")

        self.main_widget = QWidget()
        self.main_layout = QHBoxLayout()

        # Lewa część: parametry + segmenty
        left_widget = QWidget()
        left_layout = QVBoxLayout()

        # Parameter Manager – zarządzanie polami combo
        self.parameter_manager = ParameterManager(self)
        left_layout.addLayout(self.parameter_manager.layout)

        # Segment Manager – tabela z segmentami
        self.segment_manager = SegmentManager(self, self.model)
        left_layout.addWidget(self.segment_manager.table)
        left_layout.addWidget(self.segment_manager.calculate_button)
        left_layout.addWidget(self.segment_manager.result_label)

        left_widget.setLayout(left_layout)
        left_widget.setFixedWidth(400)

        # Prawa część: widok DXF + przycisk wczytywania
        right_widget = QWidget()
        right_layout = QVBoxLayout()

        load_dxf_button = QPushButton("Wczytaj Plik DXF")
        load_dxf_button.clicked.connect(self.load_dxf_file)
        right_layout.addWidget(load_dxf_button)

        self.dxf_view = CustomGraphicsView()
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
        matrix_config_action.triggered.connect(self.open_matrix_config_editor)
        konfiguracja_menu.addAction(matrix_config_action)

        data_editor_action = QAction("Edycja danych treningowych", self)
        data_editor_action.triggered.connect(self.open_data_editor)
        konfiguracja_menu.addAction(data_editor_action)

    def open_matrix_config_editor(self):
        self.matrix_config_editor.exec_()
        self.parameter_manager.update_v_input()

    def open_data_editor(self):
        self.data_editor.exec_()

    def load_dxf_file(self):
        """Wywoływane po kliknięciu przycisku 'Wczytaj Plik DXF'."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz Plik DXF", "", "Pliki DXF (*.dxf)")
        if not file_path:
            return
        try:
            # Czyścimy tabelę (np. przy nowym DXF)
            self.segment_manager.table.setRowCount(0)
            self.segment_manager.remove_all_plus_rows()
            self.segment_manager.ensure_plus_row()

            # Oddajemy wczytywanie do dxf_view
            self.dxf_view.load_dxf(file_path)

        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie udało się wczytać pliku DXF:\n{e}")

    def handle_bending_line_click(self, item, clicked_point):
        """Wywoływane z dxf_view, gdy klikniemy w linię gięcia."""
        self.segment_manager.handle_bending_line_click_in_segment_table(item, clicked_point)

    def update_status_bar(self, pos: QPointF):
        msg = f"X: {pos.x():.2f}, Y: {pos.y():.2f}"
        self.statusBar().showMessage(msg)

    # Wywoływane z main.py, aby wypełnić combo boksy (grubość, V)
    def populate_comboboxes(self):
        self.parameter_manager.populate_comboboxes(self.data)
