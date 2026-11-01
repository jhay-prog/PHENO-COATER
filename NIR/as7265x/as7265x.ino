#include <Arduino.h>
#include <HX711.h>
#include <Servo.h>
#include <SparkFun_AS7265X.h>
#include <Wire.h>
#include <stdlib.h>
#include <string.h>

const uint8_t IR_PIN = 2;
const uint8_t SEPARATOR_MOTOR_PWM_PIN = 5;
const uint8_t ROLLER_STEPPER_PINS[4] =
{
  22, 23, 24, 25
};
const uint8_t SORT_GATE_SERVO_PIN = 9;
const uint8_t SCOOP_SERVO_PIN = 10;
const uint8_t GOOD_HX711_DATA_PIN = 6;
const uint8_t GOOD_HX711_CLOCK_PIN = 7;
const uint8_t NOT_GOOD_HX711_DATA_PIN = 4;
const uint8_t NOT_GOOD_HX711_CLOCK_PIN = 8;

const int IR_DETECTED_STATE = LOW;
const unsigned long IR_DEBOUNCE_US = 10000;
const unsigned long STEPPER_STEP_INTERVAL_MS = 2;
const unsigned long SORT_GATE_HOLD_MS = 500;
const unsigned long SCOOP_HOLD_MS = 300;
const unsigned long NIR_MEASUREMENT_TIMEOUT_MS = 1200;
const unsigned long LOAD_CELL_REPORT_INTERVAL_MS = 500;
const long ROLLER_STEPS_PER_REVOLUTION = 4096;
const int SEPARATOR_MOTOR_PWM = 160;

// Calibrate these positions against the assembled gate and scoop before use.
const int GATE_GOOD_ANGLE = 45;
const int GATE_NOT_GOOD_ANGLE = 135;
const int GATE_HOME_ANGLE = 90;
const int SCOOP_NIR_ANGLE = 90;
const int SCOOP_RELEASE_ANGLE = 45;

// Replace these placeholders with measured calibration factors before weighing.
const float GOOD_LOAD_CELL_CALIBRATION = 1.0f;
const float NOT_GOOD_LOAD_CELL_CALIBRATION = 1.0f;

const uint8_t HALF_STEP_SEQUENCE[8] =
{
  0b0001, 0b0011, 0b0010, 0b0110,
  0b0100, 0b1100, 0b1000, 0b1001
};
const size_t COMMAND_BUFFER_SIZE = 32;

enum ProcessStage
{
  PROCESS_IDLE,
  PROCESS_ROTATING,
  PROCESS_WAITING_FOR_CLASSIFICATION,
  PROCESS_GATE_HOLD,
  PROCESS_NIR_SCAN,
  PROCESS_SCOOP_HOLD
};

AS7265X nirSensor;
HX711 goodLoadCell;
HX711 notGoodLoadCell;
Servo sortGate;
Servo scoop;

bool nirSensorReady = false;
bool nirScanning = false;
bool measurementRunning = false;
bool currentBeanIsGood = false;
bool goodLoadCellTared = false;
bool notGoodLoadCellTared = false;
volatile bool sampleActive = false;
volatile unsigned long pendingIrDetections = 0;
volatile unsigned long lastIrInterruptTime = 0;

unsigned long beanCount = 0;
unsigned long measurementStartTime = 0;
unsigned long nextMeasurementTime = 0;
unsigned long nirScanDelayMs = 500;
unsigned long stageStartedAt = 0;
unsigned long lastLoadCellReport = 0;

uint8_t stepperSequenceIndex = 0;
long rollerStepsRemaining = 0;
unsigned long lastStepperStep = 0;
int separatorMotorPwm = 0;
ProcessStage processStage = PROCESS_IDLE;

char commandBuffer[COMMAND_BUFFER_SIZE];
size_t commandLength = 0;
bool commandOverflow = false;

void onIrDetected()
{
  const unsigned long now = micros();
  if (sampleActive &&
      now - lastIrInterruptTime >= IR_DEBOUNCE_US)
  {
    lastIrInterruptTime = now;
    pendingIrDetections++;
  }
}

bool parseLongList(char *text, long *values, size_t count)
{
  char *cursor = text;
  for (size_t index = 0; index < count; index++)
  {
    char *end = nullptr;
    values[index] = strtol(cursor, &end, 10);
    if (end == cursor)
    {
      return false;
    }
    if (index + 1 < count)
    {
      if (*end != ',')
      {
        return false;
      }
      cursor = end + 1;
    }
    else if (*end != '\0')
    {
      return false;
    }
  }
  return true;
}

void setSeparatorMotor(int pwm)
{
  separatorMotorPwm = constrain(pwm, 0, 255);
  analogWrite(
    SEPARATOR_MOTOR_PWM_PIN,
    sampleActive && processStage == PROCESS_IDLE
      ? separatorMotorPwm
      : 0
  );
}

void pauseSeparatorMotor()
{
  analogWrite(SEPARATOR_MOTOR_PWM_PIN, 0);
}

void releaseRollerStepper()
{
  for (uint8_t pin = 0; pin < 4; pin++)
  {
    digitalWrite(ROLLER_STEPPER_PINS[pin], LOW);
  }
}

void startRollerRotation()
{
  rollerStepsRemaining = ROLLER_STEPS_PER_REVOLUTION;
  lastStepperStep = millis();
  processStage = PROCESS_ROTATING;
  Serial.println("BEAN_ROTATION_STARTED");
}

void updateRollerStepper()
{
  if (processStage != PROCESS_ROTATING || rollerStepsRemaining == 0)
  {
    return;
  }

  const unsigned long now = millis();
  if (now - lastStepperStep < STEPPER_STEP_INTERVAL_MS)
  {
    return;
  }
  lastStepperStep = now;

  stepperSequenceIndex = (stepperSequenceIndex + 1) % 8;
  const uint8_t pattern = HALF_STEP_SEQUENCE[stepperSequenceIndex];
  for (uint8_t coil = 0; coil < 4; coil++)
  {
    digitalWrite(
      ROLLER_STEPPER_PINS[coil],
      (pattern & (1 << coil)) ? HIGH : LOW
    );
  }

  rollerStepsRemaining--;
  if (rollerStepsRemaining == 0)
  {
    releaseRollerStepper();
    processStage = PROCESS_WAITING_FOR_CLASSIFICATION;
    Serial.println("BEAN_READY_FOR_CLASSIFICATION");
  }
}

void startSample()
{
  if (sampleActive)
  {
    Serial.println("SAMPLE_STARTED");
    Serial.print("BEAN_COUNT: ");
    Serial.println(beanCount);
    return;
  }

  stopNirMeasurement();
  beanCount = 0;
  noInterrupts();
  pendingIrDetections = 0;
  lastIrInterruptTime = micros() - IR_DEBOUNCE_US;
  if (digitalRead(IR_PIN) == IR_DETECTED_STATE)
  {
    pendingIrDetections = 1;
  }
  sampleActive = true;
  interrupts();
  processStage = PROCESS_IDLE;
  rollerStepsRemaining = 0;
  releaseRollerStepper();
  setSeparatorMotor(separatorMotorPwm == 0
    ? SEPARATOR_MOTOR_PWM
    : separatorMotorPwm);
  Serial.println("SAMPLE_STARTED");
  Serial.println("BEAN_COUNT: 0");
}

void stopNirMeasurement()
{
  if (!measurementRunning)
  {
    return;
  }
  nirSensor.disableBulb(AS7265x_LED_WHITE);
  nirSensor.disableBulb(AS7265x_LED_IR);
  nirSensor.disableBulb(AS7265x_LED_UV);
  measurementRunning = false;
}

void updateIrCounter();

void stopSample()
{
  if (!sampleActive)
  {
    return;
  }
  updateIrCounter();
  sampleActive = false;
  pauseSeparatorMotor();
  rollerStepsRemaining = 0;
  releaseRollerStepper();
  stopNirMeasurement();
  processStage = PROCESS_IDLE;
  sortGate.write(GATE_HOME_ANGLE);
  scoop.write(SCOOP_RELEASE_ANGLE);
  Serial.print("FINAL_BEAN_COUNT: ");
  Serial.println(beanCount);
  Serial.println("SAMPLE_COMPLETE");
}

void updateIrCounter()
{
  noInterrupts();
  const unsigned long detections = pendingIrDetections;
  pendingIrDetections = 0;
  interrupts();

  for (unsigned long detection = 0; detection < detections; detection++)
  {
    beanCount++;
    Serial.println("IR_SENSOR_DETECTED");
    Serial.print("BEAN_COUNT: ");
    Serial.println(beanCount);
    if (sampleActive && processStage == PROCESS_IDLE)
    {
      pauseSeparatorMotor();
      startRollerRotation();
    }
  }
}

void startNirMeasurement()
{
  if (!nirSensorReady)
  {
    Serial.println("ERROR: AS7265X is not connected; skipping NIR scan.");
    return;
  }
  nirSensor.enableBulb(AS7265x_LED_WHITE);
  nirSensor.enableBulb(AS7265x_LED_IR);
  nirSensor.enableBulb(AS7265x_LED_UV);
  nirSensor.setMeasurementMode(AS7265X_MEASUREMENT_MODE_6CHAN_ONE_SHOT);
  measurementStartTime = millis();
  measurementRunning = true;
}

void printNirMeasurement()
{
  Serial.print("410nm: "); Serial.print(nirSensor.getCalibratedA());
  Serial.print(" | 435nm: "); Serial.print(nirSensor.getCalibratedB());
  Serial.print(" | 460nm: "); Serial.print(nirSensor.getCalibratedC());
  Serial.print(" | 485nm: "); Serial.print(nirSensor.getCalibratedD());
  Serial.print(" | 510nm: "); Serial.print(nirSensor.getCalibratedE());
  Serial.print(" | 535nm: "); Serial.print(nirSensor.getCalibratedF());
  Serial.print(" | 560nm: "); Serial.print(nirSensor.getCalibratedG());
  Serial.print(" | 585nm: "); Serial.print(nirSensor.getCalibratedH());
  Serial.print(" | 610nm: "); Serial.print(nirSensor.getCalibratedI());
  Serial.print(" | 645nm: "); Serial.print(nirSensor.getCalibratedJ());
  Serial.print(" | 680nm: "); Serial.print(nirSensor.getCalibratedK());
  Serial.print(" | 705nm: "); Serial.print(nirSensor.getCalibratedL());
  Serial.print(" | 730nm: "); Serial.print(nirSensor.getCalibratedR());
  Serial.print(" | 760nm: "); Serial.print(nirSensor.getCalibratedS());
  Serial.print(" | 810nm: "); Serial.print(nirSensor.getCalibratedT());
  Serial.print(" | 860nm: "); Serial.print(nirSensor.getCalibratedU());
  Serial.print(" | 900nm: "); Serial.print(nirSensor.getCalibratedV());
  Serial.print(" | 940nm: "); Serial.println(nirSensor.getCalibratedW());
}

void updateLoadCells()
{
  const unsigned long now = millis();
  if (!goodLoadCellTared && goodLoadCell.is_ready())
  {
    goodLoadCell.tare(20);
    goodLoadCellTared = true;
  }
  if (!notGoodLoadCellTared && notGoodLoadCell.is_ready())
  {
    notGoodLoadCell.tare(20);
    notGoodLoadCellTared = true;
  }
  if (now - lastLoadCellReport < LOAD_CELL_REPORT_INTERVAL_MS)
  {
    return;
  }
  lastLoadCellReport = now;

  if (!goodLoadCellTared || !notGoodLoadCellTared ||
      !goodLoadCell.is_ready() || !notGoodLoadCell.is_ready())
  {
    Serial.println("ERROR: One or both HX711 modules are not ready.");
    return;
  }

  Serial.print("Load Cell 1: ");
  Serial.print(goodLoadCell.get_units(5), 2);
  Serial.print(" g | Load Cell 2: ");
  Serial.print(notGoodLoadCell.get_units(5), 2);
  Serial.println(" g");
}

void tareLoadCells()
{
  if (!goodLoadCell.is_ready() || !notGoodLoadCell.is_ready())
  {
    Serial.println("ERROR: One or both HX711 modules are not ready.");
    return;
  }
  goodLoadCell.tare(20);
  notGoodLoadCell.tare(20);
  goodLoadCellTared = true;
  notGoodLoadCellTared = true;
  Serial.println("Calibration complete: load-cell zero tare completed.");
}

void beginBeanSorting(bool isGood)
{
  if (processStage != PROCESS_WAITING_FOR_CLASSIFICATION)
  {
    return;
  }
  currentBeanIsGood = isGood;
  sortGate.write(isGood ? GATE_GOOD_ANGLE : GATE_NOT_GOOD_ANGLE);
  stageStartedAt = millis();
  processStage = PROCESS_GATE_HOLD;
  Serial.println(isGood ? "SORT_ROUTE:GOOD" : "SORT_ROUTE:NOT_GOOD");
}

void updateBeanProcess()
{
  const unsigned long now = millis();
  if (processStage == PROCESS_GATE_HOLD &&
      now - stageStartedAt >= SORT_GATE_HOLD_MS)
  {
    if (currentBeanIsGood)
    {
      scoop.write(SCOOP_NIR_ANGLE);
      if (nirSensorReady)
      {
        startNirMeasurement();
        processStage = PROCESS_NIR_SCAN;
      }
      else
      {
        scoop.write(SCOOP_RELEASE_ANGLE);
        stageStartedAt = now;
        processStage = PROCESS_SCOOP_HOLD;
      }
    }
    else
    {
      sortGate.write(GATE_HOME_ANGLE);
      stageStartedAt = now;
      processStage = PROCESS_SCOOP_HOLD;
    }
  }
  else if (processStage == PROCESS_NIR_SCAN)
  {
    if (measurementRunning && nirSensor.dataAvailable())
    {
      stopNirMeasurement();
      printNirMeasurement();
      scoop.write(SCOOP_RELEASE_ANGLE);
      stageStartedAt = now;
      processStage = PROCESS_SCOOP_HOLD;
    }
    else if (measurementRunning &&
             now - measurementStartTime >= NIR_MEASUREMENT_TIMEOUT_MS)
    {
      stopNirMeasurement();
      Serial.println("ERROR: NIR measurement timed out.");
      scoop.write(SCOOP_RELEASE_ANGLE);
      stageStartedAt = now;
      processStage = PROCESS_SCOOP_HOLD;
    }
  }
  else if (processStage == PROCESS_SCOOP_HOLD &&
           now - stageStartedAt >= SCOOP_HOLD_MS)
  {
    sortGate.write(GATE_HOME_ANGLE);
    processStage = PROCESS_IDLE;
    Serial.println(
      currentBeanIsGood ? "BEAN_SORTED:GOOD" : "BEAN_SORTED:NOT_GOOD"
    );
    if (sampleActive)
    {
      setSeparatorMotor(separatorMotorPwm);
    }
  }
}

void processCommand()
{
  commandBuffer[commandLength] = '\0';
  if (strcmp(commandBuffer, "START_SAMPLE") == 0)
  {
    startSample();
  }
  else if (strcmp(commandBuffer, "STOP_SAMPLE") == 0)
  {
    stopSample();
  }
  else if (strcmp(commandBuffer, "SORT_GOOD") == 0)
  {
    beginBeanSorting(true);
  }
  else if (strcmp(commandBuffer, "SORT_NOT_GOOD") == 0)
  {
    beginBeanSorting(false);
  }
  else if (strcmp(commandBuffer, "S") == 0)
  {
    nirScanning = true;
    nextMeasurementTime = millis();
  }
  else if (strcmp(commandBuffer, "P") == 0)
  {
    nirScanning = false;
    if (processStage != PROCESS_NIR_SCAN)
    {
      stopNirMeasurement();
    }
  }
  else if (strcmp(commandBuffer, "N?") == 0)
  {
    Serial.print("NIR_STATUS:");
    Serial.println(nirSensorReady ? "CONNECTED" : "NOT_CONNECTED");
  }
  else if (strcmp(commandBuffer, "C") == 0)
  {
    tareLoadCells();
  }
  else if (commandBuffer[0] == 'D')
  {
    char *end = nullptr;
    const long delayMs = strtol(commandBuffer + 1, &end, 10);
    if (*end == '\0' && delayMs >= 0 && delayMs <= 60000)
    {
      nirScanDelayMs = static_cast<unsigned long>(delayMs);
    }
  }
  else if (commandBuffer[0] == 'V')
  {
    char *end = nullptr;
    const long pwm = strtol(commandBuffer + 1, &end, 10);
    if (*end == '\0' && pwm >= 0 && pwm <= 255)
    {
      setSeparatorMotor(static_cast<int>(pwm));
    }
  }
  else if (commandBuffer[0] == 'A')
  {
    long values[2];
    if (parseLongList(commandBuffer + 1, values, 2) &&
        values[0] >= 1 && values[0] <= 2 &&
        values[1] >= 0 && values[1] <= 180)
    {
      if (values[0] == 1)
      {
        sortGate.write(static_cast<int>(values[1]));
      }
      else
      {
        scoop.write(static_cast<int>(values[1]));
      }
      Serial.print(values[0] == 1 ? "SV1," : "SV2,");
      Serial.println(values[1]);
    }
  }
  commandLength = 0;
}

void readSerialCommands()
{
  while (Serial.available() > 0)
  {
    const char incoming = static_cast<char>(Serial.read());
    if (incoming == '\r')
    {
      continue;
    }
    if (incoming == '\n')
    {
      if (!commandOverflow)
      {
        processCommand();
      }
      else
      {
        commandLength = 0;
        commandOverflow = false;
      }
    }
    else if (!commandOverflow)
    {
      if (commandLength < COMMAND_BUFFER_SIZE - 1)
      {
        commandBuffer[commandLength++] = incoming;
      }
      else
      {
        commandLength = 0;
        commandOverflow = true;
      }
    }
  }
}

void updateManualNirScan()
{
  if (!nirScanning || sampleActive || processStage != PROCESS_IDLE ||
      !nirSensorReady)
  {
    return;
  }
  const unsigned long now = millis();
  if (!measurementRunning)
  {
    if (static_cast<long>(now - nextMeasurementTime) >= 0)
    {
      nirSensor.enableBulb(AS7265x_LED_WHITE);
      nirSensor.enableBulb(AS7265x_LED_IR);
      nirSensor.enableBulb(AS7265x_LED_UV);
      nirSensor.setMeasurementMode(AS7265X_MEASUREMENT_MODE_6CHAN_ONE_SHOT);
      measurementStartTime = now;
      measurementRunning = true;
    }
  }
  else if (nirSensor.dataAvailable())
  {
    stopNirMeasurement();
    printNirMeasurement();
    nextMeasurementTime = millis() + nirScanDelayMs;
  }
  else if (now - measurementStartTime >= NIR_MEASUREMENT_TIMEOUT_MS)
  {
    stopNirMeasurement();
    Serial.println("ERROR: NIR measurement timed out.");
    nextMeasurementTime = millis() + nirScanDelayMs;
  }
}

void setup()
{
  Serial.begin(115200);
  Wire.begin();

  pinMode(IR_PIN, INPUT_PULLUP);
  attachInterrupt(
    digitalPinToInterrupt(IR_PIN),
    onIrDetected,
    FALLING
  );
  pinMode(SEPARATOR_MOTOR_PWM_PIN, OUTPUT);
  analogWrite(SEPARATOR_MOTOR_PWM_PIN, 0);
  for (uint8_t pin = 0; pin < 4; pin++)
  {
    pinMode(ROLLER_STEPPER_PINS[pin], OUTPUT);
    digitalWrite(ROLLER_STEPPER_PINS[pin], LOW);
  }

  sortGate.attach(SORT_GATE_SERVO_PIN);
  scoop.attach(SCOOP_SERVO_PIN);
  sortGate.write(GATE_HOME_ANGLE);
  scoop.write(SCOOP_RELEASE_ANGLE);

  goodLoadCell.begin(GOOD_HX711_DATA_PIN, GOOD_HX711_CLOCK_PIN);
  notGoodLoadCell.begin(
    NOT_GOOD_HX711_DATA_PIN,
    NOT_GOOD_HX711_CLOCK_PIN
  );
  goodLoadCell.set_scale(GOOD_LOAD_CELL_CALIBRATION);
  notGoodLoadCell.set_scale(NOT_GOOD_LOAD_CELL_CALIBRATION);

  nirSensorReady = nirSensor.begin();
  Serial.println("PHENOCOATER_BEAN_COUNTER_READY");
  Serial.print("NIR_STATUS:");
  Serial.println(nirSensorReady ? "CONNECTED" : "NOT_CONNECTED");
  if (!nirSensorReady)
  {
    Serial.println("ERROR: AS7265X not detected.");
  }
}

void loop()
{
  readSerialCommands();
  updateIrCounter();
  updateRollerStepper();
  updateBeanProcess();
  updateManualNirScan();
  updateLoadCells();

}
