# Administrator access

The normal PhenoCoater dashboard remains the startup screen and does not require
administrator login. Use the small gear button in the dashboard header to open
administrator access.

## First-time setup

1. Start PhenoCoater using `RunPhenocoater.vbs` or `python main.py`.
2. Select the gear button.
3. On first use, enter and confirm a non-empty password. There is no minimum
   password length. There is no built-in or default administrator password.
4. After setup, enter that password on later visits to open the Admin Control
   Panel.

The password is stored only as a random-salt PBKDF2-HMAC-SHA256 hash
(600,000 iterations). On Windows the credential file is located at
`%APPDATA%\PhenoCoater\admin_credentials.json`. Keep the Windows account secure;
this application-level role gate is not a substitute for operating-system access
controls.

To deliberately reset a forgotten administrator password, close PhenoCoater and
remove that credential file. The next gear-button visit will run initial setup
again. Anyone able to remove the file and use this Windows account can reset
access, so protect the account and its profile.

## Roles and hardware

Standard users have access to the normal dashboard and Pricing Settings without
an administrator login. Camera inspection, NIR analysis/scanning, servo
controls, Weight Analysis, and system settings are available only in the
authenticated Admin Control Panel. Logout returns to the dashboard and revokes
the in-memory administrator session; it does not close the shared camera or
Arduino connections.

Pricing Settings calculates weighted moisture/PNS scores and the total batch
price automatically from the entered base price and scores, the two effect
percentages (which always total 100%), and a batch weight in kilograms. Live
dual load-cell readings are available after both cells have been calibrated.
Moisture/PNS scores remain manual.

The Admin Control Panel shares the existing dashboard hardware controller.
The Mega runs `NIR/mega_controller/mega_controller.ino`; the Nano runs
`NIR/nano_scanner/nano_scanner.ino` and forwards AS7265X spectra to the Mega
over Serial1. The dashboard's existing camera stream supplies each bean's
classification. See [ARDUINO_SETUP.md](./ARDUINO_SETUP.md) for pin assignments,
upload steps, and the required load-cell calibration.

To enable live AI detections, open **System Settings**, enter the path to the
folder containing the model weights (for example, the `PHENO AI` folder with
`my_model.pt`) or enter the `.pt` file path directly, then select **SAVE
SETTINGS**. The model is loaded into the shared camera stream, annotated
detections appear on the main dashboard's **Live Camera**, and the selected
model path is remembered for later launches. If a folder contains multiple
`.pt` files, use the full path to the intended model file. An invalid or
unloadable model is reported in System Settings and the admin process log.

NIR bean classification uses the bundled
`NIR/models/svm_lda_nir_model.pkl`; it averages three AS7265X scans and displays
the predicted class and confidence on **NIR Analysis**. The NIR model recognizes
`good`, `moldy`, `slaty`, and `void`. A bean is sent to the good platform only
when both the camera and NIR model say good; if the NIR model cannot run, the
system reports the problem and uses the camera result. The model was saved with
scikit-learn 1.6.1, so a runtime version mismatch is reported and should be
validated against known samples before use.

## Tests

Run the targeted test suite from the repository root:

```text
python -m unittest discover -s tests
```

The tests cover first-time setup, password verification, logout/permission
revocation, Arduino port recognition, AS7265X parsing, and the admin panel's
reuse of the existing hardware controller. Hardware tests use a fake controller
and do not open physical devices.
