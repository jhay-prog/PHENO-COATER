# Arduino setup

The sorting controller uses two separate Arduino sketches:

- **Mega 2560:** `NIR/mega_controller/mega_controller.ino` handles the IR sensor,
  motors, servos, load cells, calibration, and sorter state machine.
- **Classic 5 V Nano:** `NIR/nano_scanner/nano_scanner.ino` handles the AS7265X
  sensor and sends spectra to the Mega.

## Connections

| Component | Mega 2560 pins |
|---|---|
| IR bean sensor output | D2 |
| Load Cell 1 / HX711 DT, SCK | D6, D7 |
| Load Cell 2 / HX711 DT, SCK | D4, D5 |
| Servo 1, Servo 2 signal | D9, D10 |
| Stepper Motor 1 / ULN2003 IN1-IN4 | D22-D25 |
| Stepper Motor 2 / ULN2003 IN1-IN4 | D26-D29 |
| Vibrator motor transistor base | D30 through 1 kΩ |
| Nano TX D1 to Mega RX1 | D19 |
| Mega TX1 D18 to Nano RX D0 | D0 on Nano |

Connect the AS7265X to the Nano using A4 (SDA) and A5 (SCL). Join the Nano
ground, Mega ground, sensor grounds, and external motor/servo supply grounds.
Use the voltage supported by the exact AS7265X breakout board. Power servos
and motors from the external regulated supplies in the wiring guide; do not
power them from the Mega's 5 V pin. The vibrator motor requires its transistor
and flyback diode. The Nano sketch uses its hardware UART at 115200 baud. Remove
the Mega UART wires while uploading to the Nano, then reconnect TX-to-RX and
RX-to-TX. Keep the Nano connected to the computer by USB for power and upload;
the Mega is the only board connected to the dashboard's serial port.

## Startup and calibration

1. Upload `NIR/mega_controller/mega_controller.ino` to the Mega 2560.
2. Leave the Nano-to-Mega UART wires disconnected while uploading
   `NIR/nano_scanner/nano_scanner.ino` to the classic Nano.
3. Connect Nano D1 (TX) to Mega D19 (RX1), Mega D18 (TX1) to Nano D0 (RX),
   and connect the grounds. Connect the Mega to the dashboard PC.
4. Before starting a sorting run, open Pricing Settings and follow the Arduino
   calibration prompts. Empty each load cell to tare it, then place a known
   weight on that cell and submit its weight in grams. Remove the weight when
   prompted before proceeding to the other cell.
5. Calibration factors and tare offsets are stored in the Mega's EEPROM. The
   firmware will not start a sorting sample until both cells are calibrated.
6. Install the Python packages in `requirements.txt` and start the dashboard
   system. It detects a bean with the IR sensor, performs camera classification,
   takes three NIR scans, and waits for the dashboard's NIR model before sorting
   and weighing the bean.

The dashboard loads `NIR/models/svm_lda_nir_model.pkl`. It averages three
18-channel spectra in wavelength order before classifying. The provided model
returns `good`, `moldy`, `slaty`, or `void`; only `good` is an NIR pass. A bean
is routed to the good platform only when both the camera and NIR model classify
it as good. If NIR inference is unavailable, the dashboard reports the issue
and the sorter falls back to the camera classification. An incompatible
scikit-learn model version is also reported; validate model predictions with
known samples before relying on physical sorting.

Load-cell values are only meaningful after calibrating each assembled
load-cell platform with a known mass. The displayed cell readings are the
current stable totals on the good and not-good platforms.
