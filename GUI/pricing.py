from decimal import Decimal, ROUND_HALF_UP

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class PricingSettingsPage(QWidget):
    def __init__(self, permission_check=None):
        super().__init__()
        self.setObjectName("pricing_settings_page")
        self.permission_check = permission_check
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
        values = (price_per_kilo, moisture_score, pns_score, weight_kg)
        if any(value is None for value in values):
            return None
        if (
            price_per_kilo < 0
            or not 0 <= moisture_score <= 100
            or not 0 <= pns_score <= 100
            or weight_kg < 0
            or not 0 <= moisture_percent <= 100
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
        layout.setContentsMargins(32, 28, 32, 32)
        layout.setSpacing(20)

        header = QVBoxLayout()
        header.setSpacing(6)
        title = QLabel("Pricing settings")
        title.setObjectName("page_title")
        description = QLabel(
            "Configure cacao pricing and estimate a batch value from its quality scores."
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
        base_form.setVerticalSpacing(12)
        self.base_price_input = QDoubleSpinBox()
        self.base_price_input.setObjectName("pricing_base_price_input")
        self.base_price_input.setRange(0, 1_000_000_000)
        self.base_price_input.setDecimals(2)
        self.base_price_input.setSpecialValueText("Not set")
        self.base_price_input.setSuffix(" pesos/kg")
        self.base_price_input.valueChanged.connect(self._update_calculation)
        base_form.addRow(
            self._create_form_label("Base price per kilo"),
            self.base_price_input,
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
        self.moisture_effect_slider.valueChanged.connect(
            self._update_calculation
        )
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
        panels.addWidget(controls_panel, 1)

        result_panel = self._create_panel("Batch price estimate")
        result_layout = result_panel.layout()
        input_note = QLabel(
            "Enter inspection scores and the current batch weight to calculate "
            "an estimate."
        )
        input_note.setObjectName("pricing_note")
        input_note.setWordWrap(True)
        result_layout.addWidget(input_note)

        value_form = QFormLayout()
        value_form.setHorizontalSpacing(18)
        value_form.setVerticalSpacing(12)
        self.moisture_score_input = self._create_score_input()
        self.moisture_score_input.setObjectName("pricing_moisture_score_input")
        self.pns_score_input = self._create_score_input()
        self.pns_score_input.setObjectName("pricing_pns_score_input")
        self.weight_input = QDoubleSpinBox()
        self.weight_input.setObjectName("pricing_weight_input")
        self.weight_input.setRange(-1, 1_000_000_000)
        self.weight_input.setDecimals(3)
        self.weight_input.setSpecialValueText("Not entered")
        self.weight_input.setValue(-1)
        self.weight_input.setSuffix(" kg")
        self.moisture_score_input.valueChanged.connect(self._update_calculation)
        self.pns_score_input.valueChanged.connect(self._update_calculation)
        self.weight_input.valueChanged.connect(self._update_calculation)
        value_form.addRow(
            self._create_form_label("Moisture score"),
            self.moisture_score_input,
        )
        value_form.addRow(
            self._create_form_label("PNS grade score"),
            self.pns_score_input,
        )
        value_form.addRow(
            self._create_form_label("Batch weight"),
            self.weight_input,
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
    def _create_score_input():
        score_input = QDoubleSpinBox()
        score_input.setRange(-1, 100)
        score_input.setDecimals(0)
        score_input.setSpecialValueText("Not entered")
        score_input.setValue(-1)
        score_input.setSuffix(" / 100")
        return score_input

    @staticmethod
    def _create_panel(title):
        panel = QFrame()
        panel.setObjectName("pricing_panel")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(22, 20, 22, 22)
        panel_layout.setSpacing(16)
        heading = QLabel(title)
        heading.setObjectName("pricing_panel_heading")
        heading.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        panel_layout.addWidget(heading)
        return panel

    @staticmethod
    def _add_result_row(layout, title, prominent=False):
        name = QLabel(title)
        name.setObjectName("pricing_result_label")
        value = QLabel("—")
        value.setObjectName(
            "pricing_total_result" if prominent else "pricing_result_value"
        )
        if prominent:
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

    def _update_calculation(self, *_args):
        if self.permission_check is not None and not self.permission_check():
            return

        moisture_score = self._score_value(self.moisture_score_input)
        pns_score = self._score_value(self.pns_score_input)
        weight_kg = self._entered_value(self.weight_input)
        base_price = self._entered_value(self.base_price_input)
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
            self.total_price_result.setText(message)
            return

        self.quality_result.setText(
            f"{result['quality_score']:.2f}%"
        )
        self.unit_price_result.setText(
            f"P {result['price_per_kilo']:,.2f} / kg"
        )
        self.total_price_result.setText(
            f"P {result['total_price']:,.2f}"
        )

    @staticmethod
    def _entered_value(spin_box):
        return None if spin_box.value() == spin_box.minimum() else spin_box.value()

    @classmethod
    def _score_value(cls, spin_box):
        return cls._entered_value(spin_box)
