#include <Arduino.h>
#include <Wire.h>
#include <Servo.h>
#include <SparkFun_AS7265X.h>
#include <stdlib.h>
#include <string.h>

AS7265X sensor;
bool scanning = false;
bool sensorReady = false;
bool measurementInProgress = false;
unsigned long scanDelayMs = 0;
unsigned long measurementStartedAt = 0;
unsigned long nextMeasurementAt = 0;
uint8_t serialCommandLength = 0;
Servo servoMotors[2];
const uint8_t servoPins[2] = {9, 10};
float servoPositions[2] = {90.0f, 90.0f};
int servoDirections[2] = {1, 1};
int lastReportedAngles[2] = {90, 90};
int servoMinimumAngles[2] = {20, 20};
int servoMaximumAngles[2] = {160, 160};
int servoSweepSpeeds[2] = {45, 45};
bool servoSweeping[2] = {false, false};
unsigned long lastServoUpdate[2] = {0, 0};
char serialCommand[20];

void reportServoStatus(uint8_t index) {
  int angle = (int)(servoPositions[index] + 0.5f);
  if (angle == lastReportedAngles[index]) {
    return;
  }
  lastReportedAngles[index] = angle;
  Serial.print("SV");
  Serial.print(index + 1);
  Serial.print(',');
  Serial.println(angle);
}

void writeServoPosition(uint8_t index) {
  int angle = (int)(servoPositions[index] + 0.5f);
  angle = constrain(angle, 0, 180);
  servoMotors[index].write(angle);
  reportServoStatus(index);
}

void reportSweepStatus(uint8_t index) {
  Serial.print("SW");
  Serial.print(index + 1);
  Serial.print(',');
  Serial.println(servoSweeping[index] ? 1 : 0);
}

void stopNirMeasurement() {
  if (!measurementInProgress) {
    return;
  }
  sensor.disableBulb(AS7265x_LED_WHITE);
  sensor.disableBulb(AS7265x_LED_IR);
  sensor.disableBulb(AS7265x_LED_UV);
  measurementInProgress = false;
}

void startNirMeasurement() {
  sensor.enableBulb(AS7265x_LED_WHITE);
  sensor.enableBulb(AS7265x_LED_IR);
  sensor.enableBulb(AS7265x_LED_UV);
  sensor.setMeasurementMode(AS7265X_MEASUREMENT_MODE_6CHAN_ONE_SHOT);
  measurementStartedAt = millis();
  measurementInProgress = true;
}

void reportNirMeasurements() {
  Serial.print("410nm: ");
  Serial.print(sensor.getCalibratedA());
  Serial.print(" | 435nm: ");
  Serial.print(sensor.getCalibratedB());
  Serial.print(" | 460nm: ");
  Serial.print(sensor.getCalibratedC());
  Serial.print(" | 485nm: ");
  Serial.print(sensor.getCalibratedD());
  Serial.print(" | 510nm: ");
  Serial.print(sensor.getCalibratedE());
  Serial.print(" | 535nm: ");
  Serial.print(sensor.getCalibratedF());
  Serial.print(" | 560nm: ");
  Serial.print(sensor.getCalibratedG());
  Serial.print(" | 585nm: ");
  Serial.print(sensor.getCalibratedH());
  Serial.print(" | 610nm: ");
  Serial.print(sensor.getCalibratedI());
  Serial.print(" | 645nm: ");
  Serial.print(sensor.getCalibratedJ());
  Serial.print(" | 680nm: ");
  Serial.print(sensor.getCalibratedK());
  Serial.print(" | 705nm: ");
  Serial.print(sensor.getCalibratedL());
  Serial.print(" | 730nm: ");
  Serial.print(sensor.getCalibratedR());
  Serial.print(" | 760nm: ");
  Serial.print(sensor.getCalibratedS());
  Serial.print(" | 810nm: ");
  Serial.print(sensor.getCalibratedT());
  Serial.print(" | 860nm: ");
  Serial.print(sensor.getCalibratedU());
  Serial.print(" | 900nm: ");
  Serial.print(sensor.getCalibratedV());
  Serial.print(" | 940nm: ");
  Serial.println(sensor.getCalibratedW());
}

void setServoSweepState(uint8_t index, bool enabled) {
  servoSweeping[index] = enabled;
  if (enabled) {
    if (servoPositions[index] < servoMinimumAngles[index]) {
      servoPositions[index] = servoMinimumAngles[index];
      servoDirections[index] = 1;
      writeServoPosition(index);
    } else if (servoPositions[index] > servoMaximumAngles[index]) {
      servoPositions[index] = servoMaximumAngles[index];
      servoDirections[index] = -1;
      writeServoPosition(index);
    } else if (servoPositions[index] <= servoMinimumAngles[index]) {
      servoDirections[index] = 1;
    } else if (servoPositions[index] >= servoMaximumAngles[index]) {
      servoDirections[index] = -1;
    }
    lastServoUpdate[index] = millis();
  }
  reportSweepStatus(index);
}

void updateServoSweep() {
  for (uint8_t index = 0; index < 2; index++) {
    unsigned long now = millis();
    if (!servoSweeping[index]) {
      lastServoUpdate[index] = now;
      continue;
    }

    unsigned long elapsed = now - lastServoUpdate[index];
    if (elapsed < 20) {
      continue;
    }
    lastServoUpdate[index] = now;

    float remainingDistance =
        servoSweepSpeeds[index] * (float)elapsed / 1000.0f;
    while (remainingDistance > 0.0f) {
      float distanceToLimit = servoDirections[index] > 0
          ? servoMaximumAngles[index] - servoPositions[index]
          : servoPositions[index] - servoMinimumAngles[index];

      if (remainingDistance < distanceToLimit) {
        servoPositions[index] += servoDirections[index] * remainingDistance;
        remainingDistance = 0.0f;
      } else {
        servoPositions[index] = servoDirections[index] > 0
            ? servoMaximumAngles[index]
            : servoMinimumAngles[index];
        remainingDistance -= distanceToLimit;
        servoDirections[index] *= -1;
      }
    }

    writeServoPosition(index);
  }
}

void setServoAngle(uint8_t index, int angle) {
  setServoSweepState(index, false);
  servoPositions[index] = constrain((float)angle, 0.0f, 180.0f);
  writeServoPosition(index);
}

void setServoSweep(uint8_t index, int minimumAngle, int maximumAngle, int speed) {
  servoMinimumAngles[index] = constrain(minimumAngle, 0, 180);
  servoMaximumAngles[index] = constrain(maximumAngle, servoMinimumAngles[index] + 5, 180);
  servoSweepSpeeds[index] = constrain(speed, 1, 180);

  servoPositions[index] = constrain(
      servoPositions[index], servoMinimumAngles[index], servoMaximumAngles[index]
  );

  if (servoPositions[index] <= servoMinimumAngles[index]) {
    servoDirections[index] = 1;
  } else if (servoPositions[index] >= servoMaximumAngles[index]) {
    servoDirections[index] = -1;
  }

  writeServoPosition(index);
}

void handleSerialCommand() {
  serialCommand[serialCommandLength] = '\0';
  if (strcmp(serialCommand, "S") == 0) {
    scanning = true;
    nextMeasurementAt = millis();
  } else if (strcmp(serialCommand, "P") == 0) {
    scanning = false;
    stopNirMeasurement();
  } else if (serialCommand[0] == 'D' && serialCommand[1] != '\0') {
    char *end;
    unsigned long delayValue = strtoul(serialCommand + 1, &end, 10);
    if (*end == '\0' && delayValue <= 60000) {
      scanDelayMs = delayValue;
    }
  } else if (serialCommand[0] == 'A') {
    char *separator = strchr(serialCommand + 1, ',');
    if (separator != NULL) {
      *separator = '\0';
      char *motorEnd;
      char *angleEnd;
      long motor = strtol(serialCommand + 1, &motorEnd, 10);
      long angle = strtol(separator + 1, &angleEnd, 10);
      if (*motorEnd == '\0' && *angleEnd == '\0' &&
          motor >= 1 && motor <= 2 && angle >= 0 && angle <= 180) {
        setServoAngle(motor - 1, angle);
      }
    }
  } else if (serialCommand[0] == 'R') {
    char *motorSeparator = strchr(serialCommand + 1, ',');
    char *minimumSeparator = motorSeparator == NULL
        ? NULL
        : strchr(motorSeparator + 1, ',');
    char *maximumSeparator = minimumSeparator == NULL
        ? NULL
        : strchr(minimumSeparator + 1, ',');

    if (motorSeparator != NULL && minimumSeparator != NULL &&
        maximumSeparator != NULL) {
      *motorSeparator = '\0';
      *minimumSeparator = '\0';
      *maximumSeparator = '\0';

      char *motorEnd;
      char *minimumEnd;
      char *maximumEnd;
      char *speedEnd;
      long motor = strtol(serialCommand + 1, &motorEnd, 10);
      long minimumAngle = strtol(motorSeparator + 1, &minimumEnd, 10);
      long maximumAngle = strtol(minimumSeparator + 1, &maximumEnd, 10);
      long speed = strtol(maximumSeparator + 1, &speedEnd, 10);

      if (*motorEnd == '\0' && *minimumEnd == '\0' &&
          *maximumEnd == '\0' && *speedEnd == '\0' &&
          motor >= 1 && motor <= 2 &&
          minimumAngle >= 0 && minimumAngle <= 175 &&
          maximumAngle >= minimumAngle + 5 && maximumAngle <= 180 &&
          speed >= 1 && speed <= 180) {
        setServoSweep(motor - 1, minimumAngle, maximumAngle, speed);
      }
    }
  } else if (serialCommand[0] == 'W') {
    char *separator = strchr(serialCommand + 1, ',');
    if (separator != NULL) {
      *separator = '\0';
      char *motorEnd;
      char *stateEnd;
      long motor = strtol(serialCommand + 1, &motorEnd, 10);
      long state = strtol(separator + 1, &stateEnd, 10);
      if (*motorEnd == '\0' && *stateEnd == '\0' &&
          motor >= 1 && motor <= 2 && (state == 0 || state == 1)) {
        uint8_t index = motor - 1;
        setServoSweepState(index, state == 1);
      }
    }
  }

  serialCommandLength = 0;
}

void readSerialCommands() {
  while (Serial.available() > 0) {
    char incoming = Serial.read();
    if (incoming == '\n') {
      handleSerialCommand();
    } else if (incoming != '\r') {
      if (serialCommandLength < sizeof(serialCommand) - 1) {
        serialCommand[serialCommandLength++] = incoming;
      } else {
        serialCommandLength = 0;
      }
    }
  }
}

void setup() {
  Serial.begin(9600);
  Wire.begin();

  for (uint8_t index = 0; index < 2; index++) {
    servoMotors[index].attach(servoPins[index]);
    servoMotors[index].write(90);
  }

  Serial.println("Starting AS7265X...");

  sensorReady = sensor.begin();
  if (!sensorReady) {
    Serial.println("ERROR: Sensor not detected! Servo control remains available.");
  } else {
    Serial.println("AS7265X READY!");
    Serial.println("--------------------");
  }

  Serial.println("SV1,90");
  Serial.println("SV2,90");
  reportSweepStatus(0);
  reportSweepStatus(1);
}

void loop() {
  readSerialCommands();
  updateServoSweep();

  if (!scanning || !sensorReady) {
    stopNirMeasurement();
    delay(10);
    return;
  }

  unsigned long now = millis();
  if (!measurementInProgress) {
    if ((long)(now - nextMeasurementAt) >= 0) {
      startNirMeasurement();
    }
  } else if (sensor.dataAvailable()) {
    stopNirMeasurement();
    reportNirMeasurements();
    nextMeasurementAt = millis() + scanDelayMs;
  } else if (now - measurementStartedAt >= 1200) {
    stopNirMeasurement();
    Serial.println("ERROR: NIR measurement timed out");
    nextMeasurementAt = millis() + scanDelayMs;
  }
  delay(1);
}
