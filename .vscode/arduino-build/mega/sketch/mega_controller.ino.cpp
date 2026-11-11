#include <Arduino.h>
#line 1 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
// Arduino Mega 2560 sorting controller.
#include <EEPROM.h>
#include <HX711.h>
#include <Servo.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

const unsigned long BAUD_RATE = 115200;
const unsigned long IR_DEBOUNCE_MS = 40;
const unsigned long IDLE_STEP_INTERVAL_MS = 10000;
const unsigned long SERVO_STEP_INTERVAL_MS = 15;
const unsigned long BACK_SORT_SETTLE_MS = 2500;
const unsigned long WEIGHT_SAMPLE_INTERVAL_MS = 200;
const unsigned long WEIGHT_STABLE_TIMEOUT_MS = 15000;
const unsigned long NIR_SCAN_SEQUENCE_TIMEOUT_MS = 10000;
const unsigned long NIR_CLASSIFICATION_TIMEOUT_MS = 5000;
const float WEIGHT_STABILITY_TOLERANCE_GRAMS = 0.5f;
const uint16_t STEPPER_STEPS_PER_REV = 4076;
const unsigned long STEPPER_STEP_INTERVAL_US = 1466;
const uint32_t CALIBRATION_MAGIC = 0x50484331UL;

const uint8_t IR_PIN = 2;
const uint8_t SERVO1_PIN = 9;
const uint8_t SERVO2_PIN = 10;
const uint8_t MOTOR_PIN = 30;
const uint8_t LOAD_CELL_1_DATA_PIN = 6;
const uint8_t LOAD_CELL_1_CLOCK_PIN = 7;
const uint8_t LOAD_CELL_2_DATA_PIN = 4;
const uint8_t LOAD_CELL_2_CLOCK_PIN = 5;

const uint8_t STEPPER_1_PINS[4] = {22, 23, 24, 25};
const uint8_t STEPPER_2_PINS[4] = {26, 27, 28, 29};
const uint8_t STEPPER_SEQUENCE[8][4] = {
  {1, 0, 0, 0}, {1, 1, 0, 0}, {0, 1, 0, 0}, {0, 1, 1, 0},
  {0, 0, 1, 0}, {0, 0, 1, 1}, {0, 0, 0, 1}, {1, 0, 0, 1}
};

const uint8_t CALIBRATED_CELL_1 = 0x01;
const uint8_t CALIBRATED_CELL_2 = 0x02;

struct StepperMotor
{
  const uint8_t *pins;
  int8_t phase;
  bool rotating;
  bool clockwise;
  uint16_t stepsRemaining;
  unsigned long lastStepAt;
};

struct StoredCalibration
{
  uint32_t magic;
  float scale1;
  float scale2;
  int32_t offset1;
  int32_t offset2;
  uint8_t flags;
};

enum FrontState : uint8_t
{
  FRONT_STARTUP,
  FRONT_FEED,
  FRONT_SCAN,
  FRONT_CLASSIFY,
  FRONT_CHECK,
  FRONT_REJECT,
  FRONT_RELEASE,
  FRONT_NIR,
  FRONT_NIR_CLASSIFY
};

enum BackState : uint8_t
{
  BACK_IDLE,
  BACK_SORT,
  BACK_WEIGH,
  BACK_TOTAL
};

enum BeanClass : uint8_t
{
  BEAN_UNDEFINED,
  BEAN_GOOD,
  BEAN_NOT_GOOD
};

enum CalibrationStep : uint8_t
{
  CALIBRATION_IDLE,
  CALIBRATION_CELL_1_EMPTY,
  CALIBRATION_CELL_1_KNOWN_WEIGHT,
  CALIBRATION_CELL_1_REMOVE_WEIGHT,
  CALIBRATION_CELL_2_EMPTY,
  CALIBRATION_CELL_2_KNOWN_WEIGHT,
  CALIBRATION_CELL_2_REMOVE_WEIGHT
};

Servo servo1;
Servo servo2;
HX711 loadCell1;
HX711 loadCell2;
StepperMotor stepper1 = {STEPPER_1_PINS, 0, false, true, 0, 0};
StepperMotor stepper2 = {STEPPER_2_PINS, 0, false, true, 0, 0};

StoredCalibration calibration = {};
FrontState frontState = FRONT_FEED;
BackState backState = BACK_IDLE;
CalibrationStep calibrationStep = CALIBRATION_IDLE;
BeanClass frontBeanClass = BEAN_UNDEFINED;
BeanClass backBeanClass = BEAN_UNDEFINED;

unsigned long beanCount = 0;
unsigned long lastIrChangeAt = 0;
unsigned long lastFeedAt = 0;
unsigned long frontStateStartedAt = 0;
unsigned long backStateStartedAt = 0;
unsigned long lastWeightSampleAt = 0;
int lastRawIrState = HIGH;
int stableIrState = HIGH;
int servoAngles[2] = {79, 70};
int sweepMinimum[2] = {0, 0};
int sweepMaximum[2] = {90, 90};
int sweepSpeed[2] = {1, 1};
int sweepDirection[2] = {1, 1};
unsigned long lastServoStepAt[2] = {0, 0};
unsigned int stableWeightSamples = 0;
float lastGoodWeightGrams = NAN;
float lastBadWeightGrams = NAN;
float measuredGoodWeightGrams = 0.0f;
float measuredBadWeightGrams = 0.0f;
uint8_t frontNirScanCount = 0;
bool sampleActive = false;
bool backFree = true;
bool userNirScanning = false;
bool nirScanning = false;
bool nirConnected = false;
bool classificationReceived = false;
bool weightErrorReported = false;
bool servoSweepEnabled[2] = {false, false};
bool idleStepperPending = false;
bool rejectStepperPending = false;
char commandBuffer[48];
size_t commandLength = 0;
char nanoMessageBuffer[360];
size_t nanoMessageLength = 0;

#line 151 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void printCalibrationPrompt(const __FlashStringHelper *message);
#line 156 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
bool cellIsCalibrated(uint8_t cell);
#line 161 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void saveCalibration();
#line 167 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void loadCalibration();
#line 215 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void writeStepperPhase(StepperMotor &motor);
#line 223 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void releaseStepper(StepperMotor &motor);
#line 233 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
bool startStepperTurn(StepperMotor &motor);
#line 242 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void updateStepper(StepperMotor &motor);
#line 270 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void updateServoSweeps();
#line 296 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void setFrontState(FrontState state);
#line 341 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void setBackState(BackState state);
#line 367 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void completeFrontNirScans();
#line 379 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void completeBeanClassification(bool nirGood, bool classifierAvailable);
#line 398 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void handleNanoMessage(char *message);
#line 420 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void readNanoMessages();
#line 444 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void rejectForeignObject();
#line 457 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void FrontProcess();
#line 546 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
bool readWeightGrams( HX711 &loadCell, float scale, int32_t offset, float &weightGrams );
#line 561 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void printWeightReadings();
#line 570 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void BackProcess();
#line 663 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void handleIrDetection();
#line 679 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void updateIrSensor();
#line 698 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void startSample();
#line 738 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void stopSample();
#line 755 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void beginLoadCellCalibration();
#line 784 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void tareLoadCell(HX711 &loadCell, int32_t &offset, float &scale);
#line 792 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void advanceCalibration();
#line 838 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void calibrateLoadCell(uint8_t cell, float knownWeightGrams);
#line 878 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void sendNirCommand(bool enabled);
#line 884 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void handleServoCommand(char *command);
#line 931 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void handleCommand(char *command);
#line 1004 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void readCommands();
#line 1028 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void setup();
#line 1064 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void loop();
#line 151 "C:\\Users\\JHON JHAY\\Documents\\PHENO-COATER\\NIR\\mega_controller\\mega_controller.ino"
void printCalibrationPrompt(const __FlashStringHelper *message)
{
  Serial.println(message);
}

bool cellIsCalibrated(uint8_t cell)
{
  return (calibration.flags & cell) != 0;
}

void saveCalibration()
{
  calibration.magic = CALIBRATION_MAGIC;
  EEPROM.put(0, calibration);
}

void loadCalibration()
{
  EEPROM.get(0, calibration);
  if (calibration.magic != CALIBRATION_MAGIC)
  {
    memset(&calibration, 0, sizeof(calibration));
    calibration.magic = CALIBRATION_MAGIC;
  }
  if (cellIsCalibrated(CALIBRATED_CELL_1) &&
      isfinite(calibration.scale1) && fabs(calibration.scale1) > 0.000001f)
  {
    loadCell1.set_scale(calibration.scale1);
    loadCell1.set_offset(calibration.offset1);
  }
  else
  {
    calibration.flags &= static_cast<uint8_t>(~CALIBRATED_CELL_1);
    loadCell1.set_scale(1.0f);
  }
  if (cellIsCalibrated(CALIBRATED_CELL_2) &&
      isfinite(calibration.scale2) && fabs(calibration.scale2) > 0.000001f)
  {
    loadCell2.set_scale(calibration.scale2);
    loadCell2.set_offset(calibration.offset2);
  }
  else
  {
    calibration.flags &= static_cast<uint8_t>(~CALIBRATED_CELL_2);
    loadCell2.set_scale(1.0f);
  }
  if (!cellIsCalibrated(CALIBRATED_CELL_1))
  {
    printCalibrationPrompt(
      F("LOAD CELL 1 CALIBRATION: Empty load cell 1 and send C to start.")
    );
  }
  else if (!cellIsCalibrated(CALIBRATED_CELL_2))
  {
    printCalibrationPrompt(
      F("LOAD CELL 2 CALIBRATION: Empty load cell 2 and send C to start.")
    );
  }
  else
  {
    printCalibrationPrompt(F("Calibration complete: both load cells are ready."));
  }
}

void writeStepperPhase(StepperMotor &motor)
{
  for (uint8_t index = 0; index < 4; index++)
  {
    digitalWrite(motor.pins[index], STEPPER_SEQUENCE[motor.phase][index] ? HIGH : LOW);
  }
}

void releaseStepper(StepperMotor &motor)
{
  motor.rotating = false;
  motor.stepsRemaining = 0;
  for (uint8_t index = 0; index < 4; index++)
  {
    digitalWrite(motor.pins[index], LOW);
  }
}

bool startStepperTurn(StepperMotor &motor)
{
  if (motor.rotating) return false;
  motor.stepsRemaining = STEPPER_STEPS_PER_REV;
  motor.rotating = true;
  motor.lastStepAt = micros();
  return true;
}

void updateStepper(StepperMotor &motor)
{
  if (!motor.rotating) return;
  unsigned long now = micros();
  if (now - motor.lastStepAt < STEPPER_STEP_INTERVAL_US) return;
  motor.lastStepAt = now;
  motor.phase += motor.clockwise ? 1 : -1;
  if (motor.phase > 7) motor.phase = 0;
  else if (motor.phase < 0) motor.phase = 7;
  writeStepperPhase(motor);
  motor.stepsRemaining--;
  if (motor.stepsRemaining == 0) releaseStepper(motor);
}

void setServoAngle(uint8_t servoNumber, int angle, bool report = true)
{
  if (servoNumber > 1) return;
  angle = constrain(angle, 0, 180);
  servoAngles[servoNumber] = angle;
  if (servoNumber == 0) servo1.write(angle);
  else servo2.write(angle);
  if (report)
  {
    Serial.print(servoNumber == 0 ? F("SV1,") : F("SV2,"));
    Serial.println(angle);
  }
}

void updateServoSweeps()
{
  if (sampleActive) return;
  unsigned long now = millis();
  for (uint8_t index = 0; index < 2; index++)
  {
    if (!servoSweepEnabled[index]) continue;
    if (now - lastServoStepAt[index] < SERVO_STEP_INTERVAL_MS) continue;
    lastServoStepAt[index] = now;
    int nextAngle = servoAngles[index] + sweepDirection[index] * sweepSpeed[index];
    if (nextAngle >= sweepMaximum[index])
    {
      nextAngle = sweepMaximum[index];
      sweepDirection[index] = -1;
    }
    else if (nextAngle <= sweepMinimum[index])
    {
      nextAngle = sweepMinimum[index];
      sweepDirection[index] = 1;
    }
    setServoAngle(index, nextAngle);
  }
}

void updateNirScanning();

void setFrontState(FrontState state)
{
  frontState = state;
  frontStateStartedAt = millis();
  if (state == FRONT_FEED)
  {
    digitalWrite(MOTOR_PIN, HIGH);
    setServoAngle(0, 79);
    lastFeedAt = millis();
  }
  else if (state == FRONT_SCAN)
  {
    digitalWrite(MOTOR_PIN, LOW);
    Serial.println(F("BEAN_ROTATION_STARTED"));
    if (!startStepperTurn(stepper2))
    {
      Serial.println(F("ERROR: Stepper 2 is still rotating."));
    }
  }
  else if (state == FRONT_CLASSIFY)
  {
    Serial.println(F("BEAN_READY_FOR_CLASSIFICATION"));
  }
  else if (state == FRONT_NIR)
  {
    frontNirScanCount = 0;
    Serial.println(F("NIR_CLASSIFICATION_SCANS_STARTED"));
    updateNirScanning();
  }
  else if (state == FRONT_NIR_CLASSIFY)
  {
    Serial.println(F("NIR_CLASSIFICATION_READY"));
  }
  else if (state == FRONT_RELEASE)
  {
    if (backFree)
    {
      backFree = false;
      setServoAngle(0, 180);
      setServoAngle(1, 70);
      setFrontState(FRONT_NIR);
    }
  }
}

void setBackState(BackState state)
{
  backState = state;
  backStateStartedAt = millis();
  if (state == BACK_SORT)
  {
    setServoAngle(1, backBeanClass == BEAN_GOOD ? 0 : 140);
  }
  else if (state == BACK_WEIGH)
  {
    stableWeightSamples = 0;
    lastGoodWeightGrams = NAN;
    lastBadWeightGrams = NAN;
    weightErrorReported = false;
  }
}

void updateNirScanning()
{
  bool shouldScan = userNirScanning ||
    (sampleActive && frontState == FRONT_NIR);
  if (shouldScan == nirScanning) return;
  Serial1.println(shouldScan ? F("S") : F("P"));
  nirScanning = shouldScan;
}

void completeFrontNirScans()
{
  if (!sampleActive || frontState != FRONT_NIR) return;
  frontNirScanCount++;
  if (frontNirScanCount < 3) return;
  frontNirScanCount = 0;
  idleStepperPending = false;
  rejectStepperPending = false;
  setFrontState(FRONT_NIR_CLASSIFY);
  updateNirScanning();
}

void completeBeanClassification(bool nirGood, bool classifierAvailable)
{
  if (frontState != FRONT_NIR && frontState != FRONT_NIR_CLASSIFY) return;
  if (classifierAvailable)
  {
    backBeanClass = frontBeanClass == BEAN_GOOD && nirGood
      ? BEAN_GOOD
      : BEAN_NOT_GOOD;
  }
  else
  {
    Serial.println(F("ERROR: NIR result unavailable; using camera classification."));
    backBeanClass = frontBeanClass;
  }
  setBackState(BACK_SORT);
  setFrontState(FRONT_FEED);
  updateNirScanning();
}

void handleNanoMessage(char *message)
{
  if (strcmp(message, "AS7265X READY") == 0)
  {
    nirConnected = true;
    Serial.println(F("NIR_STATUS:CONNECTED"));
  }
  else if (strncmp(message, "ERROR: AS7265X", 14) == 0)
  {
    nirConnected = false;
    Serial.println(F("NIR_STATUS:NOT_CONNECTED"));
  }

  if (strcmp(message, "NIR_SCAN_COMPLETE") == 0)
  {
    Serial.println(message);
    completeFrontNirScans();
    return;
  }
  Serial.println(message);
}

void readNanoMessages()
{
  while (Serial1.available() > 0)
  {
    char value = static_cast<char>(Serial1.read());
    if (value == '\r') continue;
    if (value == '\n')
    {
      nanoMessageBuffer[nanoMessageLength] = '\0';
      if (nanoMessageLength > 0) handleNanoMessage(nanoMessageBuffer);
      nanoMessageLength = 0;
    }
    else if (nanoMessageLength < sizeof(nanoMessageBuffer) - 1)
    {
      nanoMessageBuffer[nanoMessageLength++] = value;
    }
    else
    {
      nanoMessageLength = 0;
      Serial.println(F("ERROR: NIR message exceeded buffer size."));
    }
  }
}

void rejectForeignObject()
{
  Serial.println(F("FOREIGN OBJECT"));
  setServoAngle(0, 0);
  if (!startStepperTurn(stepper1))
  {
    rejectStepperPending = true;
  }
  else rejectStepperPending = false;
  frontState = FRONT_REJECT;
  frontStateStartedAt = millis();
}

void FrontProcess()
{
  if (!sampleActive) return;
  unsigned long now = millis();
  switch (frontState)
  {
    case FRONT_STARTUP:
      if (!stepper1.rotating)
      {
        setFrontState(FRONT_FEED);
        if (stableIrState == LOW) handleIrDetection();
      }
      break;
    case FRONT_FEED:
      if (!stepper1.rotating && idleStepperPending)
      {
        idleStepperPending = false;
        lastFeedAt = now;
      }
      if (!stepper1.rotating && now - lastFeedAt >= IDLE_STEP_INTERVAL_MS)
      {
        startStepperTurn(stepper1);
        idleStepperPending = true;
      }
      break;
    case FRONT_SCAN:
      if (!stepper2.rotating) setFrontState(FRONT_CLASSIFY);
      break;
    case FRONT_CLASSIFY:
      if (classificationReceived)
      {
        classificationReceived = false;
        frontNirScanCount = 0;
        idleStepperPending = false;
        rejectStepperPending = false;
        setFrontState(FRONT_CHECK);
      }
      break;
    case FRONT_CHECK:
      if (frontBeanClass == BEAN_UNDEFINED)
      {
        rejectForeignObject();
      }
      else
      {
        setFrontState(FRONT_RELEASE);
      }
      break;
    case FRONT_REJECT:
      if (!stepper1.rotating)
      {
        if (rejectStepperPending)
        {
          rejectStepperPending = false;
          startStepperTurn(stepper1);
        }
        else
        {
          frontBeanClass = BEAN_UNDEFINED;
          setFrontState(FRONT_FEED);
        }
      }
      break;
    case FRONT_RELEASE:
      if (backFree)
      {
        backFree = false;
        setServoAngle(0, 180);
        setServoAngle(1, 70);
        setFrontState(FRONT_NIR);
        updateNirScanning();
      }
      break;
    case FRONT_NIR:
      if (now - frontStateStartedAt >= NIR_SCAN_SEQUENCE_TIMEOUT_MS)
      {
        Serial.println(F("NIR_CLASSIFICATION_ABORTED"));
        completeBeanClassification(false, false);
      }
      break;
    case FRONT_NIR_CLASSIFY:
      if (now - frontStateStartedAt >= NIR_CLASSIFICATION_TIMEOUT_MS)
      {
        completeBeanClassification(false, false);
      }
      break;
  }
}

bool readWeightGrams(
  HX711 &loadCell,
  float scale,
  int32_t offset,
  float &weightGrams
)
{
  if (!loadCell.is_ready()) return false;
  float raw = loadCell.read_average(5);
  weightGrams = (raw - static_cast<float>(offset)) / scale;
  if (!isfinite(weightGrams)) return false;
  if (weightGrams < 0.0f) weightGrams = 0.0f;
  return true;
}

void printWeightReadings()
{
  Serial.print(F("Load Cell 1: "));
  Serial.print(measuredGoodWeightGrams, 2);
  Serial.print(F(" g | Load Cell 2: "));
  Serial.print(measuredBadWeightGrams, 2);
  Serial.println(F(" g"));
}

void BackProcess()
{
  if (!sampleActive || backState == BACK_IDLE) return;
  unsigned long now = millis();
  switch (backState)
  {
    case BACK_IDLE:
      break;
    case BACK_SORT:
      if (now - backStateStartedAt >= BACK_SORT_SETTLE_MS)
      {
        setBackState(BACK_WEIGH);
      }
      break;
    case BACK_WEIGH:
      if (!cellIsCalibrated(CALIBRATED_CELL_1) ||
          !cellIsCalibrated(CALIBRATED_CELL_2))
      {
        if (!weightErrorReported)
        {
          Serial.println(F("ERROR: Both load cells must be calibrated before sorting."));
          weightErrorReported = true;
        }
        break;
      }
      if (now - lastWeightSampleAt < WEIGHT_SAMPLE_INTERVAL_MS) break;
      lastWeightSampleAt = now;
      if (now - backStateStartedAt > WEIGHT_STABLE_TIMEOUT_MS)
      {
        if (!weightErrorReported)
        {
          Serial.println(F("ERROR: Load-cell reading did not become stable."));
          weightErrorReported = true;
        }
        break;
      }
      {
        float currentGood = 0.0f;
        float currentBad = 0.0f;
        if (!readWeightGrams(
              loadCell1,
              calibration.scale1,
              calibration.offset1,
              currentGood) ||
            !readWeightGrams(
              loadCell2,
              calibration.scale2,
              calibration.offset2,
              currentBad))
        {
          if (!weightErrorReported)
          {
            Serial.println(F("ERROR: HX711 not ready."));
            weightErrorReported = true;
          }
          break;
        }
        weightErrorReported = false;
        if (isfinite(lastGoodWeightGrams) &&
            isfinite(lastBadWeightGrams) &&
            fabs(currentGood - lastGoodWeightGrams) <=
              WEIGHT_STABILITY_TOLERANCE_GRAMS &&
            fabs(currentBad - lastBadWeightGrams) <=
              WEIGHT_STABILITY_TOLERANCE_GRAMS)
        {
          stableWeightSamples++;
        }
        else
        {
          stableWeightSamples = 0;
        }
        lastGoodWeightGrams = currentGood;
        lastBadWeightGrams = currentBad;
        if (stableWeightSamples >= 3)
        {
          measuredGoodWeightGrams = currentGood;
          measuredBadWeightGrams = currentBad;
          setBackState(BACK_TOTAL);
        }
      }
      break;
    case BACK_TOTAL:
      printWeightReadings();
      Serial.print(F("TOTAL_WEIGHT: "));
      Serial.print(measuredGoodWeightGrams + measuredBadWeightGrams, 2);
      Serial.println(F(" g"));
      backBeanClass = BEAN_UNDEFINED;
      backFree = true;
      setBackState(BACK_IDLE);
      break;
  }
}

void handleIrDetection()
{
  if (!sampleActive || frontState != FRONT_FEED) return;
  beanCount++;
  frontBeanClass = BEAN_UNDEFINED;
  classificationReceived = false;
  frontNirScanCount = 0;
  digitalWrite(MOTOR_PIN, LOW);
  Serial.println(F("IR_SENSOR_DETECTED"));
  Serial.print(F("BEAN_COUNT: "));
  Serial.println(beanCount);
  Serial.print(F("Object Count: "));
  Serial.println(beanCount);
  setFrontState(FRONT_SCAN);
}

void updateIrSensor()
{
  int rawState = digitalRead(IR_PIN);
  if (rawState != lastRawIrState)
  {
    lastRawIrState = rawState;
    lastIrChangeAt = millis();
  }
  if (millis() - lastIrChangeAt < IR_DEBOUNCE_MS || rawState == stableIrState)
  {
    return;
  }
  stableIrState = rawState;
  if (stableIrState == LOW)
  {
    handleIrDetection();
  }
}

void startSample()
{
  if (sampleActive) return;
  if (!cellIsCalibrated(CALIBRATED_CELL_1) ||
      !cellIsCalibrated(CALIBRATED_CELL_2))
  {
    Serial.println(F("ERROR: Calibrate both load cells before starting a sample."));
    if (!cellIsCalibrated(CALIBRATED_CELL_1))
    {
      printCalibrationPrompt(
        F("LOAD CELL 1 CALIBRATION: Empty load cell 1 and send C to start.")
      );
    }
    else
    {
      printCalibrationPrompt(
        F("LOAD CELL 2 CALIBRATION: Empty load cell 2 and send C to start.")
      );
    }
    return;
  }
  beanCount = 0;
  sampleActive = true;
  backFree = true;
  backState = BACK_IDLE;
  backBeanClass = BEAN_UNDEFINED;
  frontBeanClass = BEAN_UNDEFINED;
  classificationReceived = false;
  frontNirScanCount = 0;
  measuredGoodWeightGrams = 0.0f;
  measuredBadWeightGrams = 0.0f;
  releaseStepper(stepper1);
  releaseStepper(stepper2);
  Serial.println(F("SAMPLE_STARTED"));
  Serial.println(F("BEAN_COUNT: 0"));
  digitalWrite(MOTOR_PIN, LOW);
  frontState = FRONT_STARTUP;
  startStepperTurn(stepper1);
}

void stopSample()
{
  if (!sampleActive) return;
  sampleActive = false;
  frontState = FRONT_FEED;
  backState = BACK_IDLE;
  backFree = true;
  classificationReceived = false;
  digitalWrite(MOTOR_PIN, LOW);
  releaseStepper(stepper1);
  releaseStepper(stepper2);
  updateNirScanning();
  Serial.print(F("FINAL_BEAN_COUNT: "));
  Serial.println(beanCount);
  Serial.println(F("SAMPLE_COMPLETE"));
}

void beginLoadCellCalibration()
{
  if (sampleActive)
  {
    Serial.println(F("ERROR: Stop sorting before calibrating load cells."));
    return;
  }
  if (!loadCell1.is_ready() || !loadCell2.is_ready())
  {
    Serial.println(F("ERROR: HX711 not ready."));
    return;
  }
  if (!cellIsCalibrated(CALIBRATED_CELL_1) ||
      cellIsCalibrated(CALIBRATED_CELL_2))
  {
    calibrationStep = CALIBRATION_CELL_1_EMPTY;
    printCalibrationPrompt(
      F("LOAD CELL 1 CALIBRATION: Empty load cell 1 and send C to tare.")
    );
  }
  else
  {
    calibrationStep = CALIBRATION_CELL_2_EMPTY;
    printCalibrationPrompt(
      F("LOAD CELL 2 CALIBRATION: Empty load cell 2 and send C to tare.")
    );
  }
}

void tareLoadCell(HX711 &loadCell, int32_t &offset, float &scale)
{
  loadCell.set_scale(1.0f);
  loadCell.tare(10);
  offset = loadCell.get_offset();
  if (fabs(scale) > 0.000001f) loadCell.set_scale(scale);
}

void advanceCalibration()
{
  switch (calibrationStep)
  {
    case CALIBRATION_IDLE:
      beginLoadCellCalibration();
      break;
    case CALIBRATION_CELL_1_EMPTY:
      tareLoadCell(loadCell1, calibration.offset1, calibration.scale1);
      printCalibrationPrompt(
        F("LOAD CELL 1 CALIBRATION: Place a known weight on Load Cell 1 and enter grams.")
      );
      calibrationStep = CALIBRATION_CELL_1_KNOWN_WEIGHT;
      break;
    case CALIBRATION_CELL_1_REMOVE_WEIGHT:
      tareLoadCell(loadCell1, calibration.offset1, calibration.scale1);
      calibration.flags |= CALIBRATED_CELL_1;
      saveCalibration();
      printCalibrationPrompt(
        F("LOAD CELL 2 CALIBRATION: Empty load cell 2 and send C to tare.")
      );
      calibrationStep = CALIBRATION_CELL_2_EMPTY;
      break;
    case CALIBRATION_CELL_2_EMPTY:
      tareLoadCell(loadCell2, calibration.offset2, calibration.scale2);
      printCalibrationPrompt(
        F("LOAD CELL 2 CALIBRATION: Place a known weight on Load Cell 2 and enter grams.")
      );
      calibrationStep = CALIBRATION_CELL_2_KNOWN_WEIGHT;
      break;
    case CALIBRATION_CELL_2_REMOVE_WEIGHT:
      tareLoadCell(loadCell2, calibration.offset2, calibration.scale2);
      calibration.flags |= CALIBRATED_CELL_2;
      saveCalibration();
      calibrationStep = CALIBRATION_IDLE;
      printCalibrationPrompt(
        F("Calibration complete: both load cells are calibrated.")
      );
      break;
    case CALIBRATION_CELL_1_KNOWN_WEIGHT:
    case CALIBRATION_CELL_2_KNOWN_WEIGHT:
      Serial.println(F("ERROR: Enter the known calibration weight in grams."));
      break;
  }
}

void calibrateLoadCell(uint8_t cell, float knownWeightGrams)
{
  if (!isfinite(knownWeightGrams) || knownWeightGrams <= 0.0f)
  {
    Serial.println(F("ERROR: Calibration weight must be greater than zero grams."));
    return;
  }
  HX711 &loadCell = cell == 1 ? loadCell1 : loadCell2;
  int32_t offset = cell == 1 ? calibration.offset1 : calibration.offset2;
  float raw = loadCell.read_average(10);
  float scale = (raw - static_cast<float>(offset)) / knownWeightGrams;
  if (!isfinite(scale) || fabs(scale) < 0.000001f)
  {
    Serial.println(F("ERROR: Invalid load-cell calibration reading."));
    return;
  }
  loadCell.set_scale(scale);
  if (cell == 1)
  {
    calibration.scale1 = scale;
    calibration.offset1 = offset;
    calibration.flags |= CALIBRATED_CELL_1;
    calibrationStep = CALIBRATION_CELL_1_REMOVE_WEIGHT;
    printCalibrationPrompt(
      F("LOAD CELL 1 CALIBRATION: Remove the weight and send C to continue.")
    );
  }
  else
  {
    calibration.scale2 = scale;
    calibration.offset2 = offset;
    calibration.flags |= CALIBRATED_CELL_2;
    calibrationStep = CALIBRATION_CELL_2_REMOVE_WEIGHT;
    printCalibrationPrompt(
      F("LOAD CELL 2 CALIBRATION: Remove the weight and send C to finish.")
    );
  }
  saveCalibration();
}

void sendNirCommand(bool enabled)
{
  userNirScanning = enabled;
  updateNirScanning();
}

void handleServoCommand(char *command)
{
  if (command[0] == 'A')
  {
    if (sampleActive) return;
    int motor = 0;
    int angle = 0;
    if (sscanf(command + 1, "%d,%d", &motor, &angle) == 2 &&
        motor >= 1 && motor <= 2)
    {
      setServoAngle(motor - 1, angle);
    }
    return;
  }
  if (command[0] == 'R')
  {
    if (sampleActive) return;
    int motor = 0;
    int minimum = 0;
    int maximum = 0;
    int speed = 0;
    if (sscanf(command + 1, "%d,%d,%d,%d",
               &motor, &minimum, &maximum, &speed) == 4 &&
        motor >= 1 && motor <= 2)
    {
      uint8_t index = static_cast<uint8_t>(motor - 1);
      sweepMinimum[index] = constrain(minimum, 0, 175);
      sweepMaximum[index] = constrain(maximum, sweepMinimum[index] + 5, 180);
      sweepSpeed[index] = constrain(speed, 1, 180);
    }
    return;
  }
  if (command[0] == 'W')
  {
    if (sampleActive) return;
    int motor = 0;
    int enabled = 0;
    if (sscanf(command + 1, "%d,%d", &motor, &enabled) == 2 &&
        motor >= 1 && motor <= 2)
    {
      servoSweepEnabled[motor - 1] = enabled != 0;
      Serial.print(motor == 1 ? F("SW1,") : F("SW2,"));
      Serial.println(enabled ? 1 : 0);
    }
  }
}

void handleCommand(char *command)
{
  if (strcmp(command, "START_SAMPLE") == 0)
  {
    startSample();
  }
  else if (strcmp(command, "STOP_SAMPLE") == 0)
  {
    stopSample();
  }
  else if (strcmp(command, "SORT_GOOD") == 0 && frontState == FRONT_CLASSIFY)
  {
    frontBeanClass = BEAN_GOOD;
    classificationReceived = true;
  }
  else if (strcmp(command, "SORT_NOT_GOOD") == 0 && frontState == FRONT_CLASSIFY)
  {
    frontBeanClass = BEAN_NOT_GOOD;
    classificationReceived = true;
  }
  else if (strcmp(command, "SORT_UNDEFINED") == 0 && frontState == FRONT_CLASSIFY)
  {
    frontBeanClass = BEAN_UNDEFINED;
    classificationReceived = true;
  }
  else if (strcmp(command, "NIR_CLASS_GOOD") == 0 &&
           frontState == FRONT_NIR_CLASSIFY)
  {
    completeBeanClassification(true, true);
  }
  else if (strcmp(command, "NIR_CLASS_NOT_GOOD") == 0 &&
           frontState == FRONT_NIR_CLASSIFY)
  {
    completeBeanClassification(false, true);
  }
  else if (strcmp(command, "NIR_CLASS_UNAVAILABLE") == 0 &&
           frontState == FRONT_NIR_CLASSIFY)
  {
    completeBeanClassification(false, false);
  }
  else if (strcmp(command, "S") == 0)
  {
    sendNirCommand(true);
  }
  else if (strcmp(command, "P") == 0)
  {
    sendNirCommand(false);
  }
  else if (strcmp(command, "C") == 0)
  {
    advanceCalibration();
  }
  else if (strncmp(command, "K1,", 3) == 0 &&
           calibrationStep == CALIBRATION_CELL_1_KNOWN_WEIGHT)
  {
    calibrateLoadCell(1, static_cast<float>(atof(command + 3)));
  }
  else if (strncmp(command, "K2,", 3) == 0 &&
           calibrationStep == CALIBRATION_CELL_2_KNOWN_WEIGHT)
  {
    calibrateLoadCell(2, static_cast<float>(atof(command + 3)));
  }
  else if (strcmp(command, "N?") == 0)
  {
    Serial.println(nirConnected ?
      F("NIR_STATUS:CONNECTED") : F("NIR_STATUS:NOT_CONNECTED"));
  }
  else if (command[0] == 'A' || command[0] == 'R' || command[0] == 'W')
  {
    handleServoCommand(command);
  }
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
    else if (commandLength < sizeof(commandBuffer) - 1)
    {
      commandBuffer[commandLength++] = value;
    }
    else
    {
      commandLength = 0;
      Serial.println(F("ERROR: Serial command exceeded buffer size."));
    }
  }
}

void setup()
{
  pinMode(IR_PIN, INPUT_PULLUP);
  pinMode(MOTOR_PIN, OUTPUT);
  digitalWrite(MOTOR_PIN, LOW);
  for (uint8_t index = 0; index < 4; index++)
  {
    pinMode(STEPPER_1_PINS[index], OUTPUT);
    pinMode(STEPPER_2_PINS[index], OUTPUT);
  }
  releaseStepper(stepper1);
  releaseStepper(stepper2);

  servo1.attach(SERVO1_PIN, 500, 2400);
  servo2.attach(SERVO2_PIN, 500, 2400);
  servo1.write(servoAngles[0]);
  servo2.write(servoAngles[1]);

  loadCell1.begin(LOAD_CELL_1_DATA_PIN, LOAD_CELL_1_CLOCK_PIN);
  loadCell2.begin(LOAD_CELL_2_DATA_PIN, LOAD_CELL_2_CLOCK_PIN);
  loadCell1.set_scale(1.0f);
  loadCell2.set_scale(1.0f);

  Serial.begin(BAUD_RATE);
  Serial1.begin(BAUD_RATE);
  lastRawIrState = digitalRead(IR_PIN);
  stableIrState = lastRawIrState;
  lastIrChangeAt = millis();
  Serial.println(F("PHENOCOATER_BEAN_COUNTER_READY"));
  if (!loadCell1.is_ready() || !loadCell2.is_ready())
  {
    Serial.println(F("ERROR: One or both HX711 modules are not ready."));
  }
  loadCalibration();
}

void loop()
{
  readCommands();
  readNanoMessages();
  updateIrSensor();
  updateStepper(stepper1);
  updateStepper(stepper2);
  updateServoSweeps();
  FrontProcess();
  BackProcess();
  updateNirScanning();
}

