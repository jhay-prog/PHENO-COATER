#include <Wire.h>
#include <Servo.h>
#include <SparkFun_AS7265X.h>
#include <math.h>
#include <stdlib.h>
#include <string.h>

// ======================= SETTINGS =======================
unsigned long BAUD_RATE = 115200;            

// ---- IR  ----
byte IR_PIN            = 2;         
int  DETECTED_STATE    = LOW;       
unsigned long DEBOUNCE_MS       = 40;       
unsigned long COUNT_COOLDOWN_MS = 1500;     

// ---- Servo  ----
byte SERVO1_PIN             = 9;
byte SERVO2_PIN             = 10;
int  SERVO_MIN_PULSE_US     = 500;      
int  SERVO_MAX_PULSE_US     = 2400;   
int  SERVO_MIN_ANGLE        = 0;
int  SERVO_MAX_ANGLE        = 90;
int           SERVO_STEP_DEGREES     = 1;
unsigned long SERVO_STEP_INTERVAL_MS = 15;  

// ---- Stepper  ----
byte STEPPER_IN1_PIN = 22;
byte STEPPER_IN2_PIN = 23;
byte STEPPER_IN3_PIN = 24;
byte STEPPER_IN4_PIN = 25;
bool STEPPER_CLOCKWISE = true;    
unsigned int  STEPPER_RPM = 10;       
unsigned int  STEPPER_STEPS_PER_REV = 4076;    
unsigned long STEPPER_DELAY_AFTER_DETECT_MS = 2000; 
bool          STEPPER_RELEASE_WHEN_IDLE = true;      
unsigned long STEPPER_STEP_INTERVAL_US = 60000000UL / ((unsigned long)STEPPER_STEPS_PER_REV * STEPPER_RPM);

const uint8_t STEPPER_QUEUE_SIZE   = 20;     
const uint8_t CHANNEL_COUNT        = 18;    
const size_t  COMMAND_BUFFER_SIZE  = 24;    

// ---- NIR ----
bool USE_CALIBRATED = true;          
bool USE_BULB = true;          
uint8_t GAIN = AS7265X_GAIN_16X;         
uint8_t INTEGRATION_CYCLES = 49;           
uint8_t BULB_CURRENT = AS7265X_LED_CURRENT_LIMIT_12_5MA; 

unsigned long MEASURE_TIMEOUT_MS = 1500;     
unsigned long SENSOR_RETRY_MS = 2000;    
unsigned long MAX_SCAN_DELAY_MS  = 60000;

// ======================= IR =======================

void stepperQueueDetection();     

unsigned long beanCount = 0;
bool sampleActive = false;
bool countCooldownActive = false;

int lastRawState = HIGH;
int stableState = HIGH;
unsigned long lastChangeTime = 0;
unsigned long lastBeanCountTime = 0;

void startSample()
{
  beanCount = 0;
  sampleActive = true;

  stableState = digitalRead(IR_PIN);
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

void irUpdate()
{
  if (!sampleActive) return;

  int rawState = digitalRead(IR_PIN);

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

      stepperQueueDetection();      
    }
  }

  if (countCooldownActive &&
      stableState != DETECTED_STATE &&
      millis() - lastBeanCountTime >= COUNT_COOLDOWN_MS)
  {
    countCooldownActive = false;
  }
}

// ======================= SERVO MOTORS =======================

Servo servo1;
Servo servo2;

int servoAngle = SERVO_MIN_ANGLE;
int servoDirection = 1;               // 1 = towards max angle, -1 = towards min angle
unsigned long lastServoStepTime = 0;


void servoUpdate()
{
  unsigned long now = millis();
  if (now - lastServoStepTime < SERVO_STEP_INTERVAL_MS) return;
  lastServoStepTime = now;

  servoAngle += servoDirection * SERVO_STEP_DEGREES;

  if (servoAngle >= SERVO_MAX_ANGLE)
  {
    servoAngle = SERVO_MAX_ANGLE;
    servoDirection = -1;
  }
  else if (servoAngle <= SERVO_MIN_ANGLE)
  {
    servoAngle = SERVO_MIN_ANGLE;
    servoDirection = 1;
  }

  servo1.write(servoAngle);
  servo2.write(servoAngle);
}

// ======================= STEPPER  =======================

byte STEPPER_PINS[4] = { STEPPER_IN1_PIN, STEPPER_IN2_PIN, STEPPER_IN3_PIN, STEPPER_IN4_PIN };

byte STEPPER_SEQUENCE[8][4] =
{
  { 1, 0, 0, 0 },
  { 1, 1, 0, 0 },
  { 0, 1, 0, 0 },
  { 0, 1, 1, 0 },
  { 0, 0, 1, 0 },
  { 0, 0, 1, 1 },
  { 0, 0, 0, 1 },
  { 1, 0, 0, 1 }
};

int8_t stepperPhase = 0;
unsigned long lastStepperStepTime = 0;              


unsigned long stepperQueue[STEPPER_QUEUE_SIZE];
uint8_t       stepperQueueHead  = 0;
uint8_t       stepperQueueCount = 0;

bool          stepperRotating  = false;
unsigned int  stepperStepsLeft = 0;

void stepperWritePhase()
{
  for (uint8_t i = 0; i < 4; i++)
  {
    digitalWrite(STEPPER_PINS[i], STEPPER_SEQUENCE[stepperPhase][i] ? HIGH : LOW);
  }
}

void stepperRelease()
{
  for (uint8_t i = 0; i < 4; i++)
  {
    digitalWrite(STEPPER_PINS[i], LOW);
  }
}

void stepperQueueDetection()
{
  if (stepperQueueCount >= STEPPER_QUEUE_SIZE)
  {
    Serial.println(F("WARNING: stepper queue full, one turn skipped."));
    return;
  }

  uint8_t tail = (stepperQueueHead + stepperQueueCount) % STEPPER_QUEUE_SIZE;
  stepperQueue[tail] = millis();
  stepperQueueCount++;
}


void stepperUpdate()
{
  if (!stepperRotating)
  {
    if (stepperQueueCount == 0) return;
    if (millis() - stepperQueue[stepperQueueHead] < STEPPER_DELAY_AFTER_DETECT_MS) return;

    stepperQueueHead = (stepperQueueHead + 1) % STEPPER_QUEUE_SIZE;
    stepperQueueCount--;

    stepperStepsLeft = STEPPER_STEPS_PER_REV;
    stepperRotating = true;
    lastStepperStepTime = micros();
    return;
  }

  unsigned long now = micros();
  if (now - lastStepperStepTime < STEPPER_STEP_INTERVAL_US) return;
  lastStepperStepTime = now;

  if (STEPPER_CLOCKWISE)
  {
    stepperPhase++;
  }
  else
  {
    stepperPhase--;
  }

  if (stepperPhase > 7)
  {
    stepperPhase = 0;
  }
  else if (stepperPhase < 0)
  {
    stepperPhase = 7;
  }

  stepperWritePhase();
  stepperStepsLeft--;

  if (stepperStepsLeft == 0)
  {
    stepperRotating = false;
    if (STEPPER_RELEASE_WHEN_IDLE) stepperRelease();
  }
}

void backgroundUpdate()
{
  irUpdate();
  servoUpdate();
  stepperUpdate();
}

// ======================= NIR SCANNER =======================


uint16_t WAVELENGTHS[CHANNEL_COUNT] = 
{
  410, 435, 460, 485, 510, 535, 560, 585, 610,
  645, 680, 705, 730, 760, 810, 860, 900, 940
};

AS7265X sensor;

bool sensorReady = false;
bool scanning    = false;     
bool measuring   = false;    

unsigned long scanDelayMs = 0;
unsigned long nextScanAt = 0;
unsigned long measureStartedAt = 0;
unsigned long nextSensorAttemptAt = 0;

char   commandBuffer[COMMAND_BUFFER_SIZE];
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

#define CH(letter) (backgroundUpdate(), (USE_CALIBRATED ? sensor.getCalibrated##letter() : (float)sensor.get##letter()))

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

void printSpectrum(float *v)
{
  bool first = true;
  for (uint8_t i = 0; i < CHANNEL_COUNT; i++)
  {
    if (isnan(v[i]) || isinf(v[i])) continue;   
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
  unsigned long now = millis();

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

void handleCommand(char *cmd)
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
  // Any other command (GUI servo page, load cell...) is ignored here.
}

void readCommands()
{
  while (Serial.available() > 0)
  {
    char c = static_cast<char>(Serial.read());
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

  servo1.attach(SERVO1_PIN, SERVO_MIN_PULSE_US, SERVO_MAX_PULSE_US);
  servo2.attach(SERVO2_PIN, SERVO_MIN_PULSE_US, SERVO_MAX_PULSE_US);
  servo1.write(servoAngle);
  servo2.write(servoAngle);
  lastServoStepTime = millis();

  for (uint8_t i = 0; i < 4; i++)
  {
    pinMode(STEPPER_PINS[i], OUTPUT);
  }
  stepperRelease();

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
  backgroundUpdate();
  nirUpdate();
}