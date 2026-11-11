#include <Wire.h>
#include <SparkFun_AS7265X.h>
#include <math.h>
#include <string.h>

const unsigned long BAUD_RATE = 115200;
const unsigned long SCAN_INTERVAL_MS = 1000;
const unsigned long MEASURE_TIMEOUT_MS = 1500;
const unsigned long SENSOR_RETRY_MS = 2000;
const uint8_t CHANNEL_COUNT = 18;
const size_t COMMAND_BUFFER_SIZE = 8;

const bool USE_CALIBRATED = true;
const bool USE_BULB = true;
const uint8_t GAIN = AS7265X_GAIN_16X;
const uint8_t INTEGRATION_CYCLES = 49;
const uint8_t BULB_CURRENT = AS7265X_LED_CURRENT_LIMIT_12_5MA;

const uint16_t WAVELENGTHS[CHANNEL_COUNT] = 
{
  410, 435, 460, 485, 510, 535, 560, 585, 610,
  645, 680, 705, 730, 760, 810, 860, 900, 940
};

AS7265X sensor;
bool sensorReady = false;
bool scanning = false;
bool measuring = false;
unsigned long nextScanAt = 0;
unsigned long measureStartedAt = 0;
unsigned long nextSensorAttemptAt = 0;
char commandBuffer[COMMAND_BUFFER_SIZE];
size_t commandLength = 0;

bool connectSensor()
{
  if (!sensor.begin())
  {
    sensorReady = false;
    return false;
  }
  sensor.disableIndicator();
  sensor.setGain(GAIN);
  sensor.setIntegrationCycles(INTEGRATION_CYCLES);
  sensor.setBulbCurrent(BULB_CURRENT, AS7265x_LED_WHITE);
  sensor.setBulbCurrent(BULB_CURRENT, AS7265x_LED_IR);
  sensor.setBulbCurrent(BULB_CURRENT, AS7265x_LED_UV);
  sensorReady = true;
  Serial.println(F("AS7265X READY"));
  return true;
}

void setBulbs(bool enabled)
{
  if (!USE_BULB || !sensorReady) return;
  if (enabled)
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

#define CHANNEL(letter) \
  (USE_CALIBRATED ? sensor.getCalibrated##letter() : \
                    static_cast<float>(sensor.get##letter()))

void readChannels(float *values)
{
  values[0] = CHANNEL(A);
  values[1] = CHANNEL(B);
  values[2] = CHANNEL(C);
  values[3] = CHANNEL(D);
  values[4] = CHANNEL(E);
  values[5] = CHANNEL(F);
  values[6] = CHANNEL(G);
  values[7] = CHANNEL(H);
  values[8] = CHANNEL(R);
  values[9] = CHANNEL(I);
  values[10] = CHANNEL(S);
  values[11] = CHANNEL(J);
  values[12] = CHANNEL(T);
  values[13] = CHANNEL(U);
  values[14] = CHANNEL(V);
  values[15] = CHANNEL(W);
  values[16] = CHANNEL(K);
  values[17] = CHANNEL(L);
}

void printSpectrum(const float *values)
{
  bool first = true;
  for (uint8_t index = 0; index < CHANNEL_COUNT; index++)
  {
    if (isnan(values[index]) || isinf(values[index])) continue;
    if (!first) Serial.print(F(", "));
    Serial.print(WAVELENGTHS[index]);
    Serial.print(F("nm: "));
    Serial.print(values[index], 2);
    first = false;
  }
  if (first)
  {
    Serial.println(F("ERROR: AS7265X returned no valid data."));
    return;
  }
  Serial.println();
  Serial.println(F("NIR_SCAN_COMPLETE"));
}

void startScan()
{
  if (scanning) return;
  scanning = true;
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

void handleCommand(const char *command)
{
  if (strcmp(command, "S") == 0) startScan();
  else if (strcmp(command, "P") == 0) stopScan();
}

void readCommands()
{
  while (Serial.available() > 0)
  {
    char value = static_cast<char>(Serial.read());
    if (value == '\r') continue;
    if (value == '\n')
    {
      commandBuffer[commandLength] = '\0';
      if (commandLength > 0) handleCommand(commandBuffer);
      commandLength = 0;
    }
    else if (commandLength < COMMAND_BUFFER_SIZE - 1)
    {
      commandBuffer[commandLength++] = value;
    }
    else
    {
      commandLength = 0;
    }
  }
}

void updateScanner()
{
  if (!scanning) return;
  unsigned long now = millis();
  if (!sensorReady)
  {
    if (static_cast<long>(now - nextSensorAttemptAt) >= 0)
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
    if (static_cast<long>(now - nextScanAt) >= 0) beginMeasurement();
    return;
  }

  if (sensor.dataAvailable())
  {
    float values[CHANNEL_COUNT];
    readChannels(values);
    endMeasurement();
    printSpectrum(values);
    nextScanAt = measureStartedAt + SCAN_INTERVAL_MS;
  }
  else if (now - measureStartedAt > MEASURE_TIMEOUT_MS)
  {
    endMeasurement();
    sensorReady = false;
    nextSensorAttemptAt = now;
    Serial.println(F("ERROR: AS7265X measurement timed out."));
  }
}

void setup()
{
  Serial.begin(BAUD_RATE);
  if (!connectSensor())
  {
    Serial.println(F("ERROR: AS7265X not detected. Check SDA/SCL wiring and power."));
  }
}

void loop()
{
  readCommands();
  updateScanner();
}
