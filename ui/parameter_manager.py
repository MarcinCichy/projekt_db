# ui/parameter_manager.py
from PyQt5.QtWidgets import QVBoxLayout, QLabel, QComboBox, QHBoxLayout
from ui.matrix_config_editor import load_matrix_config

class ParameterManager:
    def __init__(self, parent):
        self.parent = parent
        self.layout = QHBoxLayout()

        self.grubosc_input = QComboBox()
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

    def populate_comboboxes(self, data):
        """Wypełnia listy rozwijalne na podstawie danych."""
        grubosc_values = sorted(data['Grubosc'].unique())
        self.grubosc_input.addItems([str(x) for x in grubosc_values])

    def update_v_input(self):
        """Aktualizuje listę V na podstawie wybranej grubości."""
        selected_grubosc = self.grubosc_input.currentText()
        config = load_matrix_config()
        self.V_input.clear()
        if selected_grubosc in config:
            self.V_input.addItems([str(x) for x in config[selected_grubosc]])

    def get_selected_parameters(self):
        """Zwraca wybrane parametry."""
        return {
            "grubosc": self.grubosc_input.currentText(),
            "V": self.V_input.currentText(),
            "material": self.material_input.currentText(),
        }
