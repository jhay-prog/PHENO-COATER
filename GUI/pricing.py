from decimal import Decimal, ROUND_HALF_UP

from PySide6.QtCore import QLocale, Qt
from PySide6.QtGui import QDoubleValidator
from PySide6.QtWidgets import (
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class PricingSettingsPage(QWidget):
    def __init__(self, permission_check=None):
        super().__init__()
        self.setObjectName("pricing_settings_page")
        self.permission_check = permission_check
        self.inputs_saved = False
        self._setup_ui()
        self._update_calculation()

    @staticmethod
    def calculate_price(
        price_per_kilo,
        moisture_score,
        pns_score,
        weight_kg,
        moisture_percent,
    ):
        values = (price_per_kilo, moisture_score, pns_score)
        if any(value is None for value in values):
            return None
        if (
            price_per_kilo < 0
            or not 0 <= moisture_score <= 100
            or not 0 <= pns_score <= 100
            or not 0 <= moisture_percent <= 100
            or (weight_kg is not None and weight_kg < 0)
        ):
            raise ValueError("Pricing inputs are outside their valid ranges.")

        base_price = Decimal(str(price_per_kilo))
        moisture_weight = Decimal(str(moisture_percent))
        pns_weight = Decimal(100) - moisture_weight
        quality_score = (
            Decimal(str(moisture_score)) * moisture_weight
            + Decimal(str(pns_score)) * pns_weight
        ) / Decimal(100)
        price_per_kilo_result = (
            base_price * quality_score / Decimal(100)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_price = None
        if weight_kg is not None:
            total_price = (
                price_per_kilo_result * Decimal(str(weight_kg))
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {
            "quality_score": quality_score.quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            ),
            "price_per_kilo": price_per_kilo_result,
            "total_price": total_price,
        }

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 30, 36, 34)
        layout.setSpacing(22)

        header = QVBoxLayout()
        header.setSpacing(8)
        title = QLabel("Pricing settings")
        title.setObjectName("page_title")
        description = QLabel(
            "Configure cacao pricing and calculate a batch result from its quality scores."
        )
        description.setObjectName("settings_description")
        header.addWidget(title)
        header.addWidget(description)
        layout.addLayout(header)

        panels = QHBoxLayout()
        panels.setSpacing(20)
        controls_panel = self._create_panel("Pricing controls")
        controls_layout = controls_panel.layout()

        base_form = QFormLayout()
        base_form.setHorizontalSpacing(18)
        base_form.setVerticalSpacing(15)
        base_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        self.base_price_input = self._create_numeric_input(
            "pricing_base_price_input",
            0,
            1_000_000_000,
            2,
            "Enter base price",
        )
        self.base_price_input.setObjectName("pricing_base_price_input")
        self.base_price_input.textChanged.connect(self._inputs_changed)
        base_form.addRow(
            self._create_form_label("Base price per kilo"),
            self._input_with_suffix(self.base_price_input, "pesos/kg"),
        )
        controls_layout.addLayout(base_form)

        effect_title = QLabel("Score effect")
        effect_title.setObjectName("pricing_section_title")
        controls_layout.addWidget(effect_title)

        moisture_effect_row = QHBoxLayout()
        moisture_effect_label = QLabel("Moisture score")
        moisture_effect_label.setObjectName("pricing_control_label")
        self.moisture_effect_label = QLabel("50%")
        self.moisture_effect_label.setObjectName("pricing_effect_value")
        moisture_effect_row.addWidget(moisture_effect_label)
        moisture_effect_row.addStretch()
        moisture_effect_row.addWidget(self.moisture_effect_label)
        controls_layout.addLayout(moisture_effect_row)

        self.moisture_effect_slider = QSlider(Qt.Orientation.Horizontal)
        self.moisture_effect_slider.setObjectName("pricing_effect_slider")
        self.moisture_effect_slider.setRange(0, 100)
        self.moisture_effect_slider.setValue(50)
        self.moisture_effect_slider.valueChanged.connect(
            self._update_effect_labels
        )
        self.moisture_effect_slider.valueChanged.connect(self._inputs_changed)
        controls_layout.addWidget(self.moisture_effect_slider)

        pns_effect_row = QHBoxLayout()
        pns_effect_label = QLabel("PNS grade score")
        pns_effect_label.setObjectName("pricing_control_label")
        self.pns_effect_label = QLabel("50%")
        self.pns_effect_label.setObjectName("pricing_effect_value")
        pns_effect_row.addWidget(pns_effect_label)
        pns_effect_row.addStretch()
        pns_effect_row.addWidget(self.pns_effect_label)
        controls_layout.addLayout(pns_effect_row)

        pns_note = QLabel(
            "Adjust the slider to set the moisture weighting. PNS receives the "
            "remaining share, so both weights always total 100%."
        )
        pns_note.setObjectName("pricing_note")
        pns_note.setWordWrap(True)
        controls_layout.addWidget(pns_note)

        self.save_inputs_button = QPushButton("Save Inputs")
        self.save_inputs_button.setObjectName("pricing_save_inputs_button")
        self.save_inputs_button.clicked.connect(self.save_inputs)
        controls_layout.addWidget(self.save_inputs_button)

        panels.addWidget(controls_panel, 1)

        result_panel = self._create_panel("Price Result")
        result_layout = result_panel.layout()
        input_note = QLabel(
            "Enter the quality scores and batch weight. Weight defaults to "
            "1 kg for testing."
        )
        input_note.setObjectName("pricing_note")
        input_note.setWordWrap(True)
        result_layout.addWidget(input_note)

        value_form = QFormLayout()
        value_form.setHorizontalSpacing(18)
        value_form.setVerticalSpacing(15)
        value_form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
        )
        self.weight_input = self._create_numeric_input(
            "pricing_weight_input",
            0,
            1_000_000_000,
            3,
            "Enter weight",
        )
        self.weight_input.setText("1.000")
        self.weight_input.setAccessibleName("Current batch weight in kilograms")
        self.weight_input.textChanged.connect(self._inputs_changed)
        self.moisture_score_input = self._create_numeric_input(
            "pricing_moisture_score_input",
            0,
            100,
            2,
            "Enter score",
        )
        self.moisture_score_input.setObjectName("pricing_moisture_score_input")
        self.pns_score_input = self._create_numeric_input(
            "pricing_pns_score_input",
            0,
            100,
            2,
            "Enter score",
        )
        self.pns_score_input.setObjectName("pricing_pns_score_input")
        self.moisture_score_input.textChanged.connect(self._inputs_changed)
        self.pns_score_input.textChanged.connect(self._inputs_changed)
        value_form.addRow(
            self._create_form_label("Current batch weight"),
            self._input_with_suffix(self.weight_input, "kg"),
        )
        value_form.addRow(
            self._create_form_label("Moisture score"),
            self._input_with_suffix(self.moisture_score_input, "/ 100"),
        )
        value_form.addRow(
            self._create_form_label("PNS grade score"),
            self._input_with_suffix(self.pns_score_input, "/ 100"),
        )
        result_layout.addLayout(value_form)

        results_divider = QFrame()
        results_divider.setObjectName("pricing_results_divider")
        results_divider.setFrameShape(QFrame.Shape.HLine)
        result_layout.addWidget(results_divider)
        self.quality_result = self._add_result_row(
            result_layout,
            "Weighted quality score",
        )
        self.unit_price_result = self._add_result_row(
            result_layout,
            "Calculated price per kilo",
        )
        self.total_price_result = self._add_result_row(
            result_layout,
            "Total batch price",
            prominent=True,
            initial_value="Save inputs to display total price",
        )
        panels.addWidget(result_panel, 1)
        layout.addLayout(panels)
        layout.addStretch()

    @staticmethod
    def _create_form_label(text):
        label = QLabel(text)
        label.setObjectName("pricing_form_label")
        return label

    @staticmethod
    def _create_panel(title):
        panel = QFrame()
        panel.setObjectName("pricing_panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(24, 22, 24, 24)
        panel_layout.setSpacing(18)
        heading = QLabel(title)
        heading.setObjectName("pricing_panel_heading")
        heading.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        panel_layout.addWidget(heading)
        return panel

    @staticmethod
    def _create_numeric_input(object_name, minimum, maximum, decimals, placeholder):
        numeric_input = QLineEdit()
        numeric_input.setObjectName(object_name)
        numeric_input.setPlaceholderText(placeholder)
        validator = QDoubleValidator(
            minimum,
            maximum,
            decimals,
            numeric_input,
        )
        validator.setLocale(QLocale.c())
        validator.setNotation(QDoubleValidator.Notation.StandardNotation)
        numeric_input.setValidator(validator)
        return numeric_input

    @staticmethod
    def _input_with_suffix(numeric_input, suffix):
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)
        row.addWidget(numeric_input, 1)
        suffix_label = QLabel(suffix)
        suffix_label.setObjectName("pricing_input_suffix")
        row.addWidget(suffix_label)
        return container

    @staticmethod
    def _add_result_row(
        layout,
        title,
        prominent=False,
        initial_value="—",
    ):
        name = QLabel(title)
        name.setObjectName("pricing_result_label")
        value = QLabel(initial_value)
        value.setObjectName(
            "pricing_total_result" if prominent else "pricing_result_value"
        )
        if prominent:
            value.setProperty(
                "result_state",
                (
                    "status"
                    if initial_value.startswith(("Save", "Enter", "Complete"))
                    else "value"
                ),
            )
            layout.addWidget(name)
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(value)
        else:
            row = QHBoxLayout()
            row.addWidget(name)
            row.addStretch()
            row.addWidget(value)
            layout.addLayout(row)
        return value

    def _update_effect_labels(self, moisture_percent):
        self.moisture_effect_label.setText(f"{moisture_percent}%")
        self.pns_effect_label.setText(f"{100 - moisture_percent}%")

    def _update_calculation(self):
        if self.permission_check is not None and not self.permission_check():
            return

        moisture_score = self._score_value(self.moisture_score_input)
        pns_score = self._score_value(self.pns_score_input)
        base_price = self._entered_value(self.base_price_input)
        weight_kg = self._entered_value(self.weight_input)
        if (
            base_price is None
            or base_price > 1_000_000_000
            or weight_kg is None
            or weight_kg > 1_000_000_000
            or moisture_score is None
            or not 0 <= moisture_score <= 100
            or pns_score is None
            or not 0 <= pns_score <= 100
        ):
            self.quality_result.setText("—")
            self.unit_price_result.setText("—")
            has_entered_values = any(
                field.text().strip()
                for field in (
                    self.base_price_input,
                    self.moisture_score_input,
                    self.pns_score_input,
                )
            )
            message = (
                "Complete all inputs to calculate"
                if has_entered_values
                else "Save inputs to display total price"
            )
            self._set_total_price_text(message)
            return
        result = self.calculate_price(
            base_price,
            moisture_score,
            pns_score,
            weight_kg,
            self.moisture_effect_slider.value(),
        )
        if result is None:
            message = "—"
            self.quality_result.setText(message)
            self.unit_price_result.setText(message)
            self._set_total_price_text("Complete all inputs to calculate")
            return

        self.quality_result.setText(
            f"{result['quality_score']:.2f}%"
        )
        self.unit_price_result.setText(
            f"₱ {result['price_per_kilo']:,.2f} / kg"
        )
        if self.inputs_saved:
            self._set_total_price_text(
                f"₱ {result['total_price']:,.2f}"
            )
        else:
            self._set_total_price_text("Save inputs to display total price")

    def _inputs_changed(self):
        self.inputs_saved = False
        self._update_calculation()

    def save_inputs(self):
        if self.permission_check is not None and not self.permission_check():
            return False
        base_price = self._entered_value(self.base_price_input)
        weight_kg = self._entered_value(self.weight_input)
        moisture_score = self._score_value(self.moisture_score_input)
        pns_score = self._score_value(self.pns_score_input)
        if (
            base_price is None
            or base_price > 1_000_000_000
            or weight_kg is None
            or weight_kg > 1_000_000_000
            or moisture_score is None
            or not 0 <= moisture_score <= 100
            or pns_score is None
            or not 0 <= pns_score <= 100
        ):
            self.inputs_saved = False
            self._set_total_price_text("Complete all inputs before saving")
            return False
        self.inputs_saved = True
        self._update_calculation()
        return True

    def _set_total_price_text(self, text):
        self.total_price_result.setText(text)
        state = (
            "status"
            if text.startswith(("Save", "Complete"))
            else "value"
        )
        if self.total_price_result.property("result_state") != state:
            self.total_price_result.setProperty("result_state", state)
            self.total_price_result.style().unpolish(
                self.total_price_result
            )
            self.total_price_result.style().polish(
                self.total_price_result
            )

    @staticmethod
    def _entered_value(numeric_input):
        text = numeric_input.text().strip()
        if not text:
            return None
        try:
            value = float(text)
        except ValueError:
            return None
        return value if value >= 0 else None

    @classmethod
    def _score_value(cls, spin_box):
        return cls._entered_value(spin_box)
