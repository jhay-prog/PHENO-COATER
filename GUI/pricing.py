from decimal import Decimal, ROUND_HALF_UP

from PySide6.QtCore import QLocale, Qt, Signal
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
    calibration_continue_requested = Signal()

    def __init__(self, permission_check=None):
        super().__init__()
        self.setObjectName("pricing_settings_page")
        self.permission_check = permission_check
        self.total_price_unlocked = False
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
        moisture_contribution = (
            Decimal(str(moisture_score)) * moisture_weight / Decimal(100)
        )
        pns_contribution = (
            Decimal(str(pns_score)) * pns_weight / Decimal(100)
        )
        price_per_kilo_result = (
            base_price * quality_score / Decimal(100)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total_price = None
        if weight_kg is not None:
            total_price = (
                base_price
                * Decimal(str(weight_kg))
                * quality_score
                / Decimal(100)
            ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return {
            "moisture_contribution": moisture_contribution.quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            ),
            "pns_contribution": pns_contribution.quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            ),
            "quality_score": quality_score.quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            ),
            "price_per_kilo": price_per_kilo_result,
            "total_price": total_price,
        }

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)

        header = QVBoxLayout()
        header.setSpacing(4)
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
        panels.setSpacing(8)
        controls_panel = self._create_panel("Pricing controls")
        controls_layout = controls_panel.layout()
        controls_layout.setSpacing(0)
        controls_layout.addSpacing(50)

        base_form = QFormLayout()
        base_form.setHorizontalSpacing(10)
        base_form.setVerticalSpacing(8)
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
        controls_layout.addSpacing(50)

        effect_title = QLabel("Score effect")
        effect_title.setObjectName("pricing_section_title")

        effect_section = QVBoxLayout()
        effect_section.setSpacing(0)
        effect_section.addWidget(effect_title)
        effect_section.addSpacing(12)

        moisture_effect_row = QHBoxLayout()
        moisture_effect_label = QLabel("Moisture Content Price Percent Effect")
        moisture_effect_label.setObjectName("pricing_control_label")
        self.moisture_effect_label = QLabel("50%")
        self.moisture_effect_label.setObjectName("pricing_effect_value")
        moisture_effect_row.addWidget(moisture_effect_label)
        moisture_effect_row.addStretch()
        moisture_effect_row.addWidget(self.moisture_effect_label)
        effect_section.addLayout(moisture_effect_row)
        effect_section.addSpacing(45)

        self.moisture_effect_slider = QSlider(Qt.Orientation.Horizontal)
        self.moisture_effect_slider.setObjectName("pricing_effect_slider")
        self.moisture_effect_slider.setRange(0, 100)
        self.moisture_effect_slider.setValue(50)
        self.moisture_effect_slider.valueChanged.connect(
            self._update_effect_labels
        )
        self.moisture_effect_slider.valueChanged.connect(self._inputs_changed)
        effect_section.addWidget(self.moisture_effect_slider)
        effect_section.addSpacing(45)

        pns_effect_row = QHBoxLayout()
        pns_effect_label = QLabel("PNS Grade Price Percent Effect")
        pns_effect_label.setObjectName("pricing_control_label")
        self.pns_effect_label = QLabel("50%")
        self.pns_effect_label.setObjectName("pricing_effect_value")
        pns_effect_row.addWidget(pns_effect_label)
        pns_effect_row.addStretch()
        pns_effect_row.addWidget(self.pns_effect_label)
        effect_section.addLayout(pns_effect_row)
        controls_layout.addLayout(effect_section)
        controls_layout.addSpacing(40)
        controls_layout.addStretch()

        self.save_inputs_button = QPushButton("Save Inputs")
        self.save_inputs_button.setObjectName("pricing_save_inputs_button")
        self.save_inputs_button.clicked.connect(self._save_inputs)
        controls_layout.addWidget(self.save_inputs_button)

        panels.addWidget(controls_panel, 1)

        result_panel = self._create_panel("Price Result")
        result_layout = result_panel.layout()
        self.arduino_status_label = QLabel(
            "Checking for Arduino serial connection..."
        )
        self.arduino_status_label.setObjectName("pricing_arduino_status")
        self.arduino_status_label.setWordWrap(True)
        result_layout.addWidget(self.arduino_status_label)
        self.calibration_prompt_label = QLabel(
            "Arduino calibration prompts will appear here."
        )
        self.calibration_prompt_label.setObjectName(
            "pricing_calibration_prompt"
        )
        self.calibration_prompt_label.setWordWrap(True)
        self.calibration_prompt_label.setVisible(False)
        result_layout.addWidget(self.calibration_prompt_label)
        self.calibration_continue_button = QPushButton(
            "Continue calibration"
        )
        self.calibration_continue_button.setObjectName(
            "pricing_calibration_continue_button"
        )
        self.calibration_continue_button.setEnabled(False)
        self.calibration_continue_button.setVisible(False)
        self.calibration_continue_button.clicked.connect(
            self._request_calibration_continue
        )
        result_layout.addWidget(self.calibration_continue_button)

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
            "Waiting for load cells",
        )
        self.weight_input.setReadOnly(True)
        self.weight_input.setAccessibleName("Current batch weight in kilograms")
        self.weight_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.moisture_score_input = self._create_numeric_input(
            "pricing_moisture_score_input",
            0,
            100,
            2,
            "Waiting for moisture score",
        )
        self.moisture_score_input.setObjectName("pricing_moisture_score_input")
        self.moisture_score_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pns_score_input = self._create_numeric_input(
            "pricing_pns_score_input",
            0,
            100,
            2,
            "Waiting for PNS grade score",
        )
        self.pns_score_input.setObjectName("pricing_pns_score_input")
        self.pns_score_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.moisture_score_input.textChanged.connect(self._inputs_changed)
        self.pns_score_input.textChanged.connect(self._inputs_changed)
        value_form.addRow(
            self._create_form_label("Current Weight (kg)"),
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
        self.moisture_contribution_result = self._add_result_row(
            result_layout,
            "Overall Moisture Score",
            initial_value="",
        )
        self.pns_contribution_result = self._add_result_row(
            result_layout,
            "Overall PNS Score",
            initial_value="",
        )
        self.unit_price_result = self._add_result_row(
            result_layout,
            "Price Per Kilo",
            initial_value="",
        )
        self.total_price_result = self._add_result_row(
            result_layout,
            "Total batch value",
            prominent=True,
            initial_value="",
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
        panel_layout.setContentsMargins(12, 10, 12, 12)
        panel_layout.setSpacing(8)
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
        initial_value="",
    ):
        if prominent:
            total_card = QFrame()
            total_card.setObjectName("pricing_total_card")
            total_layout = QVBoxLayout(total_card)
            total_layout.setContentsMargins(12, 12, 12, 12)
            total_layout.setSpacing(6)
            name = QLabel(title)
            name.setObjectName("pricing_total_label")
            value = QLabel(initial_value)
            value.setObjectName("pricing_total_result")
            value.setProperty(
                "result_state",
                (
                    "status"
                    if initial_value.startswith(("Save", "Enter", "Complete"))
                    else "value"
                ),
            )
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            total_layout.addWidget(name)
            total_layout.addWidget(value)
            layout.addWidget(total_card)
            return value

        result_row = QFrame()
        result_row.setObjectName("pricing_result_row")
        row = QHBoxLayout(result_row)
        row.setContentsMargins(10, 8, 10, 8)
        row.setSpacing(10)
        name = QLabel(title)
        name.setObjectName("pricing_result_label")
        value = QLabel(initial_value)
        value.setObjectName("pricing_result_value")
        row.addWidget(name)
        row.addStretch()
        row.addWidget(value)
        layout.addWidget(result_row)
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
            or moisture_score is None
            or not 0 <= moisture_score <= 100
            or pns_score is None
            or not 0 <= pns_score <= 100
        ):
            self.moisture_contribution_result.clear()
            self.pns_contribution_result.clear()
            self.unit_price_result.clear()
            self._set_total_price_text("")
            return
        valid_weight = (
            weight_kg is not None
            and 0 <= weight_kg <= 1_000_000_000
        )
        result = self.calculate_price(
            base_price,
            moisture_score,
            pns_score,
            weight_kg if valid_weight else None,
            self.moisture_effect_slider.value(),
        )
        if result is None:
            self.moisture_contribution_result.clear()
            self.pns_contribution_result.clear()
            self.unit_price_result.clear()
            self._set_total_price_text("")
            return

        self.moisture_contribution_result.setText(
            f"{result['moisture_contribution']:.2f}"
        )
        self.pns_contribution_result.setText(
            f"{result['pns_contribution']:.2f}"
        )
        self.unit_price_result.setText(
            f"₱ {result['price_per_kilo']:,.2f} / kg"
        )
        if not self.total_price_unlocked:
            self._set_total_price_text("")
        elif not valid_weight:
            self._set_total_price_text("")
        elif result["total_price"] is None:
            self._set_total_price_text("")
        else:
            self._set_total_price_text(f"₱ {result['total_price']:,.2f}")

    def _save_inputs(self):
        self.total_price_unlocked = True
        self._update_calculation()

    def _inputs_changed(self):
        self._update_calculation()

    def set_current_weight(self, weight_kg):
        if weight_kg is None:
            self.weight_input.clear()
        else:
            self.weight_input.setText(f"{float(weight_kg):.3f}")
        self._update_calculation()

    def set_arduino_status(self, message):
        normalized = message.casefold()
        is_not_detected = "not detected" in normalized
        display_message = (
            "Load cells connected"
            if "live load-cell reading" in normalized
            else "" if is_not_detected else message
        )
        self.arduino_status_label.setText(display_message)
        self.arduino_status_label.setVisible(not is_not_detected)
        state = (
            "connected"
            if "live load-cell reading" in normalized
            else "error"
            if any(
                word in normalized
                for word in ("not detected", "failed", "error", "could not")
            )
            else "waiting"
        )
        if self.arduino_status_label.property("status_state") != state:
            self.arduino_status_label.setProperty("status_state", state)
            self.arduino_status_label.style().unpolish(
                self.arduino_status_label
            )
            self.arduino_status_label.style().polish(
                self.arduino_status_label
            )

    def update_calibration_prompt(self, message):
        normalized = message.casefold()
        relevant_prompts = (
            "load cell 1 calibration",
            "load cell 2 calibration",
            "empty load cell",
            "place a known",
            "remove the weight",
            "send c",
            "calibration complete",
        )
        if not normalized.startswith(relevant_prompts):
            return
        self.calibration_prompt_label.setText(message)
        self.calibration_prompt_label.setVisible(True)
        can_continue = normalized.startswith("send c")
        self.calibration_continue_button.setEnabled(can_continue)
        self.calibration_continue_button.setVisible(can_continue)

    def _request_calibration_continue(self):
        self.calibration_continue_button.setEnabled(False)
        self.calibration_continue_button.setVisible(False)
        self.calibration_prompt_label.setText(
            "Continue command sent; waiting for Arduino..."
        )
        self.calibration_continue_requested.emit()

    def _set_total_price_text(self, text):
        self.total_price_result.setText(text)
        state = (
            "status"
            if text.startswith(("Enter", "Weight", "Waiting"))
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
