/*
  PhenoCoater - NIR Scanner + IR Bean Counter
  Board : Arduino Mega 2560

  ---------------------------- WIRING ----------------------------
  IR bean sensor (3-wire obstacle / break-beam sensor)
    VCC  -> Mega 5V
    GND  -> Mega GND
    OUT  -> Mega pin 2          (signal goes LOW when a bean is detected)
    (E18-D80NK colors: brown = 5V, blue = GND, black = OUT)

  AS7265X Spectral Triad (NIR sensor)
    SDA  -> Mega pin 20
    SCL  -> Mega pin 21
    3.3V -> Mega 3.3V
    GND  -> Mega GND
    NOTE: the Triad is 3.3 V and the Mega is 5 V. Use a bidirectional
    I2C level shifter (or a Qwiic-style shield) between them.

  All grounds must be common.
  -----------------------------------------------------------------

  Library (Arduino IDE > Library Manager):
    "SparkFun Spectral Triad AS7265X"  (SparkFun_AS7265X)

  Serial protocol (matches the PhenoCoater GUI, GUI/dashboard.py)
    PC -> Arduino (each command ends with newline):
      START_SAMPLE  reset the bean count to 0 and start counting  (Start System)
      STOP_SAMPLE   stop counting and report the final count      (Stop System)
      S             start continuous NIR scanning  (START SCAN, NIR Analysis tab)
      P             stop NIR scanning              (STOP SCANNING)
      D<ms>         pause between NIR scans in ms, 0-60000   e.g. D500
    Arduino -> PC:
      BEAN_COUNT: 12                        one line each time a bean is counted
                                            (updates TOTAL BEANS on the dashboard)
      FINAL_BEAN_COUNT: 57                  sent when STOP_SAMPLE is received
      AS7265X READY                         NIR sensor found
      410nm: 12.34, 435nm: 13.20, ... 940nm: 9.87
                                            one line per NIR scan, all 18 channels
      other status / ERROR lines            shown in the NIR serial monitor

  Serial baud rate must match Dashboard.arduino_baud_rate in GUI/dashboard.py.
*/

#include <Wire.h>
#include <SparkFun_AS7265X.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

// ======================= SETTINGS =======================
const unsigned long BAUD_RATE = 115200;            // must match the GUI

// ---- IR bean counter ----
const byte          IR_PIN            = 2;         // sensor OUT
const int           DETECTED_STATE    = LOW;       // pin level when a bean is in front of the sensor
const unsigned long DEBOUNCE_MS       = 40;        // signal must be stable this long to count
const unsigned long COUNT_COOLDOWN_MS = 1500;      // minimum time between two counted beans

// ---- NIR scanner ----
const bool    USE_CALIBRATED     = true;           // true: calibrated values, false: raw ADC counts
const bool    USE_BULB           = true;           // light the sensor's own LEDs during each scan
const uint8_t GAIN               = AS7265X_GAIN_16X;               // 1X, 37X, 16X, 64X
const uint8_t INTEGRATION_CYCLES = 49;             // time = (cycles + 1) * 2.8 ms, x2 in 18-channel mode
const uint8_t BULB_CURRENT       = AS7265X_LED_CURRENT_LIMIT_12_5MA; // 12_5MA, 25MA, 50MA, 100MA

const unsigned long MEASURE_TIMEOUT_MS = 1500;     // give up on one reading after this long
const unsigned long SENSOR_RETRY_MS    = 2000;     // how often to retry a missing sensor
const unsigned long MAX_SCAN_DELAY_MS  = 60000;
// ========================================================

// ======================= IR BEAN COUNTER =======================

unsigned long beanCount          = 0;
bool          sampleActive       = false;
bool          countCooldownActive = false;

int           lastRawState       = HIGH;
int           stableState        = HIGH;
unsigned long lastChangeTime     = 0;
unsigned long lastBeanCountTime  = 0;

void startSample()
{
  beanCount    = 0;
  sampleActive = true;

  stableState  = digitalRead(IR_PIN);
  lastRawState = stableState;
  lastChangeTime = millis();
  countCooldownActive = false;

  Serial.println(F("SAMPLE_STARTED"));
  Serial.println(F("BEAN_COUNT: 0"));
}

void stopSample()
{
  if (!sampleActive) return;
  sampleActive = false;

  Serial.print(F("FINAL_BEAN_COUNT: "));
  Serial.println(beanCount);
  Serial.println(F("SAMPLE_COMPLETE"));
}

// Call as often as possible. It is also called between NIR channel reads
// so a bean is never missed while the NIR sensor is being read.
void irUpdate()
{
  if (!sampleActive) return;

  const int rawState = digitalRead(IR_PIN);

  if (rawState != lastRawState)
  {
    lastRawState = rawState;
    lastChangeTime = millis();
  }

  if (millis() - lastChangeTime >= DEBOUNCE_MS && rawState != stableState)
  {
    stableState = rawState;

    if (stableState == DETECTED_STATE && !countCooldownActive)
    {
      beanCount++;
      lastBeanCountTime = millis();
      countCooldownActive = true;

      Serial.print(F("BEAN_COUNT: "));
      Serial.println(beanCount);
    }
  }

  if (countCooldownActive &&
      stableState != DETECTED_STATE &&
      millis() - lastBeanCountTime >= COUNT_COOLDOWN_MS)
  {
    countCooldownActive = false;
  }
}

// ======================= NIR SCANNER =======================

const uint8_t CHANNEL_COUNT = 18;
// Wavelength order of the Triad's channels: A B C D E F G H R I S J T U V W K L
const uint16_t WAVELENGTHS[CHANNEL_COUNT] = {
  410, 435, 460, 485, 510, 535, 560, 585, 610,
  645, 680, 705, 730, 760, 810, 860, 900, 940
};

AS7265X sensor;

bool sensorReady = false;
bool scanning    = false;     // requested by the GUI (S / P)
bool measuring   = false;     // a one-shot reading is in progress

unsigned long scanDelayMs         = 0;
unsigned long nextScanAt          = 0;
unsigned long measureStartedAt    = 0;
unsigned long nextSensorAttemptAt = 0;

const size_t COMMAND_BUFFER_SIZE = 24;
char   commandBuffer[COMMAND_BUFFER_SIZE];
size_t commandLength = 0;

bool connectSensor()
{
  if (!sensor.begin())          // uses Wire (Mega: SDA 20, SCL 21)
  {
    sensorReady = false;
    return false;
  }
  sensor.disableIndicator();      // blue status LED off
  sensor.setGain(GAIN);
  sensor.setIntegrationCycles(INTEGRATION_CYCLES);
  sensor.setBulbCurrent(BULB_CURRENT, AS7265x_LED_WHITE);
  sensor.setBulbCurrent(BULB_CURRENT, AS7265x_LED_IR);
  sensor.setBulbCurrent(BULB_CURRENT, AS7265x_LED_UV);
  sensorReady = true;
  Serial.println(F("AS7265X READY"));
  return true;
}

void setBulbs(bool on)
{
  if (!USE_BULB || !sensorReady) return;
  if (on)
  {
    sensor.enableBulb(AS7265x_LED_WHITE);
    sensor.enableBulb(AS7265x_LED_IR);
    sensor.enableBulb(AS7265x_LED_UV);
  }
  else
  {
    sensor.disableBulb(AS7265x_LED_WHITE);
    sensor.disableBulb(AS7265x_LED_IR);
    sensor.disableBulb(AS7265x_LED_UV);
  }
}

// Starts one 18-channel reading and returns immediately (non-blocking),
// so a "P" command from the GUI is handled within milliseconds.
void beginMeasurement()
{
  setBulbs(true);
  sensor.setMeasurementMode(AS7265X_MEASUREMENT_MODE_6CHAN_ONE_SHOT);
  measureStartedAt = millis();
  measuring = true;
}

void endMeasurement()
{
  setBulbs(false);
  measuring = false;
}

// Reads one channel, then lets the bean counter check its sensor.
#define CH(letter) (irUpdate(), (USE_CALIBRATED ? sensor.getCalibrated##letter() : (float)sensor.get##letter()))

void readChannels(float *v)
{
  v[0]  = CH(A);  // 410
  v[1]  = CH(B);  // 435
  v[2]  = CH(C);  // 460
  v[3]  = CH(D);  // 485
  v[4]  = CH(E);  // 510
  v[5]  = CH(F);  // 535
  v[6]  = CH(G);  // 560
  v[7]  = CH(H);  // 585
  v[8]  = CH(R);  // 610
  v[9]  = CH(I);  // 645
  v[10] = CH(S);  // 680
  v[11] = CH(J);  // 705
  v[12] = CH(T);  // 730
  v[13] = CH(U);  // 760
  v[14] = CH(V);  // 810
  v[15] = CH(W);  // 860
  v[16] = CH(K);  // 900
  v[17] = CH(L);  // 940
}

// One line per scan: "410nm: 12.34, 435nm: 13.20, ..."
void printSpectrum(const float *v)
{
  bool first = true;
  for (uint8_t i = 0; i < CHANNEL_COUNT; i++)
  {
    if (isnan(v[i]) || isinf(v[i])) continue;   // GUI shows NO DATA for a missing channel
    if (!first) Serial.print(F(", "));
    Serial.print(WAVELENGTHS[i]);
    Serial.print(F("nm: "));
    Serial.print(v[i], 2);
    first = false;
  }
  if (first)
  {
    Serial.println(F("ERROR: AS7265X returned no valid data."));
  }
  else
  {
    Serial.println();
  }
}

void startScan()
{
  if (scanning) return;
  scanning  = true;
  measuring = false;
  nextScanAt = millis();
  nextSensorAttemptAt = millis();
  Serial.println(F("SCAN_STARTED"));
}

void stopScan()
{
  if (!scanning) return;
  if (measuring) endMeasurement();
  scanning = false;
  Serial.println(F("SCAN_STOPPED"));
}

void nirUpdate()
{
  if (!scanning) return;
  const unsigned long now = millis();

  // Sensor missing or lost: keep retrying while a scan is requested.
  if (!sensorReady)
  {
    if ((long)(now - nextSensorAttemptAt) >= 0)
    {
      nextSensorAttemptAt = now + SENSOR_RETRY_MS;
      if (!connectSensor())
      {
        Serial.println(F("ERROR: AS7265X not detected. Check SDA/SCL wiring and power."));
      }
    }
    return;
  }

  if (!measuring)
  {
    if ((long)(now - nextScanAt) >= 0) beginMeasurement();
    return;
  }

  if (sensor.dataAvailable())
  {
    float values[CHANNEL_COUNT];
    readChannels(values);
    endMeasurement();
    printSpectrum(values);
    nextScanAt = millis() + scanDelayMs;
  }
  else if (now - measureStartedAt > MEASURE_TIMEOUT_MS)
  {
    endMeasurement();
    sensorReady = false;           // force a clean re-init on the next pass
    nextSensorAttemptAt = now;
    Serial.println(F("ERROR: AS7265X measurement timed out."));
  }
}

// ======================= SERIAL COMMANDS =======================

void handleCommand(const char *cmd)
{
  if (strcmp(cmd, "START_SAMPLE") == 0)
  {
    startSample();
  }
  else if (strcmp(cmd, "STOP_SAMPLE") == 0)
  {
    stopSample();
  }
  else if (strcmp(cmd, "S") == 0)
  {
    startScan();
  }
  else if (strcmp(cmd, "P") == 0)
  {
    stopScan();
  }
  else if (cmd[0] == 'D' && cmd[1] != '\0')
  {
    char *end = nullptr;
    unsigned long value = strtoul(cmd + 1, &end, 10);
    if (*end == '\0')
    {
      scanDelayMs = value > MAX_SCAN_DELAY_MS ? MAX_SCAN_DELAY_MS : value;
      Serial.print(F("SCAN_DELAY_MS: "));
      Serial.println(scanDelayMs);
    }
  }
  // Any other command (servo, load cell...) is ignored here.
}

void readCommands()
{
  while (Serial.available() > 0)
  {
    const char c = static_cast<char>(Serial.read());
    if (c == '\r') continue;
    if (c == '\n')
    {
      commandBuffer[commandLength] = '\0';
      if (commandLength > 0) handleCommand(commandBuffer);
      commandLength = 0;
    }
    else if (commandLength < COMMAND_BUFFER_SIZE - 1)
    {
      commandBuffer[commandLength++] = c;
    }
    else
    {
      commandLength = 0;           // overlong line: discard
    }
  }
}

// ======================= ARDUINO ENTRY POINTS =======================

void setup()
{
  pinMode(IR_PIN, INPUT_PULLUP);
  Serial.begin(BAUD_RATE);

  stableState  = digitalRead(IR_PIN);
  lastRawState = stableState;
  lastChangeTime = millis();

  Serial.println(F("PHENOCOATER_BEAN_COUNTER_READY"));

  if (!connectSensor())
  {
    Serial.println(F("ERROR: AS7265X not detected. Check SDA/SCL wiring and power."));
  }
}

void loop()
{
  readCommands();
  irUpdate();
  nirUpdate();
}