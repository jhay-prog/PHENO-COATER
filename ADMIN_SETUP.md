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
controls, inspection results, and system settings are available only in the
authenticated Admin Control Panel. Logout returns to the dashboard and revokes
the in-memory administrator session; it does not close the shared camera or
Arduino connections.

Pricing Settings calculates an estimate from a base price, moisture score, PNS
score, and batch weight. The two score-effect percentages always total 100%.
Because the application does not currently receive these validated scores and
batch weight from its hardware, the fields are manual and are not prefilled
with example values.

The Admin Control Panel shares the existing dashboard hardware controller.
Camera preview and AS7265X serial data are reused rather than opening another
camera or serial port. Readings that are not received or calculated are shown as
unavailable; a missing load cell, classification model, or moisture-calibration
algorithm is not represented by made-up measurements.

## Tests

Run the targeted test suite from the repository root:

```text
python -m unittest discover -s tests
```

The tests cover first-time setup, password verification, logout/permission
revocation, Arduino port recognition, AS7265X parsing, and the admin panel's
reuse of the existing hardware controller. Hardware tests use a fake controller
and do not open physical devices.
