#include <Arduino.h>
#include "HX711.h"
#include <Wire.h>
#include <Servo.h>
#include <SparkFun_AS7265X.h>
#include <stdlib.h>
#include <string.h>

// ---------------------------------------------------------------------------
// Hardware & global state
// ---------------------------------------------------------------------------
AS7265X SPECTRALSENSOR;
HX711 SCALE1;
HX711 SCALE2;

const uint8_t LOADCELLDATAPIN1 = 6;
const uint8_t LOADCELLCLOCKPIN1 = 7;
const uint8_t LOADCELLDATAPIN2 = 4;
const uint8_t LOADCELLCLOCKPIN2 = 5;

bool LOADCELL1TARED = false;
bool LOADCELL2TARED = false;
unsigned long LASTWEIGHTREPORT = 0;
const uint8_t LOAD_CELL_AVERAGE_SAMPLES = 10;

// Scanning / measurement state
bool ISSCANNING = false;
bool SENSORISREADY = false;
bool MEASUREMENTRUNNING = false;
unsigned long SCANDELAYMS = 0;
unsigned long MEASUREMENTSTARTTIME = 0;
unsigned long NEXTMEASUREMENTTIME = 0;

// Serial command buffer
char COMMANDBUFFER[20];
uint8_t COMMANDLENGTH = 0;

// Servo setup --------------------------------------------------------------
Servo SERVOS[2];
const uint8_t SERVOPINS[2] = {9, 10};

float SERVOANGLE[2] = {90.0f, 90.0f};  
int SERVODIRECTION[2] = {1, 1};        
int LASTREPORTEDANGLE[2] = {90, 90};    

int SERVOMINANGLE[2] = {20, 20};
int SERVOMAXANGLE[2] = {160, 160};
int SERVOSWEEPSPEED[2] = {45, 45};      // degrees per second
bool SERVOSWEEPING[2] = {false, false};
unsigned long LASTSERVOSTEP[2] = {0, 0};


void updateLoadCellReadings() {
  if (!LOADCELL1TARED && SCALE1.is_ready()) {
    SCALE1.tare(180);
    LOADCELL1TARED = true;
    Serial.println("Load Cell 1 auto tare complete.");
  }

  if (!LOADCELL2TARED && SCALE2.is_ready()) {
    SCALE2.tare(180);
    LOADCELL2TARED = true;
    Serial.println("Load Cell 2 auto tare complete.");
  }

  if (!LOADCELL1TARED || !LOADCELL2TARED) {
    unsigned long NOW = millis();
    if (NOW - LASTWEIGHTREPORT >= 1000) {
      Serial.println("ERROR: One or both HX711 modules are not ready.");
      LASTWEIGHTREPORT = NOW;
    }
    return;
  }

  unsigned long NOW = millis();
  if (NOW - LASTWEIGHTREPORT < 500) return;
  if (!SCALE1.is_ready() || !SCALE2.is_ready()) {
    Serial.println("ERROR: One or both HX711 modules are not ready.");
    LASTWEIGHTREPORT = NOW;
    return;
  }

  float WEIGHT1 = SCALE1.get_units(LOAD_CELL_AVERAGE_SAMPLES);
  float WEIGHT2 = SCALE2.get_units(LOAD_CELL_AVERAGE_SAMPLES);
  Serial.print("Load Cell 1: ");
  Serial.print(WEIGHT1, 2);
  Serial.print(" g | Load Cell 2: ");
  Serial.print(WEIGHT2, 2);
  Serial.println(" g");
  LASTWEIGHTREPORT = millis();
}

// ---------------------------------------------------------------------------
// Servo helpers
// ---------------------------------------------------------------------------

// Only report an angle when it actually changed.
void reportServoAngle(uint8_t I) {
  int ANGLE = (int)(SERVOANGLE[I] + 0.5f);
  if (ANGLE == LASTREPORTEDANGLE[I]) return;

  LASTREPORTEDANGLE[I] = ANGLE;
  Serial.print("SV");
  Serial.print(I + 1);
  Serial.print(',');
  Serial.println(ANGLE);
}


void applyServoAngle(uint8_t I) {
  int ANGLE = (int)(SERVOANGLE[I] + 0.5f);
  ANGLE = constrain(ANGLE, 0, 180);
  SERVOS[I].write(ANGLE);
  reportServoAngle(I);
}

void reportSweepState(uint8_t I) {
  Serial.print("SW");
  Serial.print(I + 1);
  Serial.print(',');
  Serial.println(SERVOSWEEPING[I] ? 1 : 0);
}

// ---------------------------------------------------------------------------
// NIR / spectral measurement
// ---------------------------------------------------------------------------

void stopMeasurement() {
  if (!MEASUREMENTRUNNING) return;

  SPECTRALSENSOR.disableBulb(AS7265x_LED_WHITE);
  SPECTRALSENSOR.disableBulb(AS7265x_LED_IR);
  SPECTRALSENSOR.disableBulb(AS7265x_LED_UV);
  MEASUREMENTRUNNING = false;
}

void startMeasurement() {
  SPECTRALSENSOR.enableBulb(AS7265x_LED_WHITE);
  SPECTRALSENSOR.enableBulb(AS7265x_LED_IR);
  SPECTRALSENSOR.enableBulb(AS7265x_LED_UV);
  SPECTRALSENSOR.setMeasurementMode(AS7265X_MEASUREMENT_MODE_6CHAN_ONE_SHOT);

  MEASUREMENTSTARTTIME = millis();
  MEASUREMENTRUNNING = true;
}


void printMeasurement() {
  Serial.print("410nm: "); Serial.print(SPECTRALSENSOR.getCalibratedA());
  Serial.print(" | 435nm: "); Serial.print(SPECTRALSENSOR.getCalibratedB());
  Serial.print(" | 460nm: "); Serial.print(SPECTRALSENSOR.getCalibratedC());
  Serial.print(" | 485nm: "); Serial.print(SPECTRALSENSOR.getCalibratedD());
  Serial.print(" | 510nm: "); Serial.print(SPECTRALSENSOR.getCalibratedE());
  Serial.print(" | 535nm: "); Serial.print(SPECTRALSENSOR.getCalibratedF());
  Serial.print(" | 560nm: "); Serial.print(SPECTRALSENSOR.getCalibratedG());
  Serial.print(" | 585nm: "); Serial.print(SPECTRALSENSOR.getCalibratedH());
  Serial.print(" | 610nm: "); Serial.print(SPECTRALSENSOR.getCalibratedI());
  Serial.print(" | 645nm: "); Serial.print(SPECTRALSENSOR.getCalibratedJ());
  Serial.print(" | 680nm: "); Serial.print(SPECTRALSENSOR.getCalibratedK());
  Serial.print(" | 705nm: "); Serial.print(SPECTRALSENSOR.getCalibratedL());
  Serial.print(" | 730nm: "); Serial.print(SPECTRALSENSOR.getCalibratedR());
  Serial.print(" | 760nm: "); Serial.print(SPECTRALSENSOR.getCalibratedS());
  Serial.print(" | 810nm: "); Serial.print(SPECTRALSENSOR.getCalibratedT());
  Serial.print(" | 860nm: "); Serial.print(SPECTRALSENSOR.getCalibratedU());
  Serial.print(" | 900nm: "); Serial.print(SPECTRALSENSOR.getCalibratedV());
  Serial.print(" | 940nm: "); Serial.println(SPECTRALSENSOR.getCalibratedW());
}

// ---------------------------------------------------------------------------
// Servo motion
// ---------------------------------------------------------------------------

void setSweepEnabled(uint8_t I, bool ENABLED) {
  SERVOSWEEPING[I] = ENABLED;

  if (ENABLED) {
    // Snap into range and pick a sensible starting direction.
    if (SERVOANGLE[I] < SERVOMINANGLE[I]) {
      SERVOANGLE[I] = SERVOMINANGLE[I];
      SERVODIRECTION[I] = 1;
      applyServoAngle(I);
    } else if (SERVOANGLE[I] > SERVOMAXANGLE[I]) {
      SERVOANGLE[I] = SERVOMAXANGLE[I];
      SERVODIRECTION[I] = -1;
      applyServoAngle(I);
    } else if (SERVOANGLE[I] <= SERVOMINANGLE[I]) {
      SERVODIRECTION[I] = 1;
    } else if (SERVOANGLE[I] >= SERVOMAXANGLE[I]) {
      SERVODIRECTION[I] = -1;
    }
    LASTSERVOSTEP[I] = millis();
  }

  reportSweepState(I);
}


void updateSweeps() {
  for (uint8_t I = 0; I < 2; I++) {
    unsigned long NOW = millis();

    if (!SERVOSWEEPING[I]) {
      LASTSERVOSTEP[I] = NOW;
      continue;
    }

    unsigned long ELAPSED = NOW - LASTSERVOSTEP[I];
    if (ELAPSED < 20) continue;   
    LASTSERVOSTEP[I] = NOW;

   
    float DISTANCELEFT = SERVOSWEEPSPEED[I] * (float)ELAPSED / 1000.0f;

    while (DISTANCELEFT > 0.0f) {
      float TOLIMIT = (SERVODIRECTION[I] > 0)
                          ? SERVOMAXANGLE[I] - SERVOANGLE[I]
                          : SERVOANGLE[I] - SERVOMINANGLE[I];

      if (DISTANCELEFT < TOLIMIT) {
        SERVOANGLE[I] += SERVODIRECTION[I] * DISTANCELEFT;
        DISTANCELEFT = 0.0f;
      } else {
        
        SERVOANGLE[I] = (SERVODIRECTION[I] > 0) ? SERVOMAXANGLE[I]
                                                : SERVOMINANGLE[I];
        DISTANCELEFT -= TOLIMIT;
        SERVODIRECTION[I] *= -1;
      }
    }

    applyServoAngle(I);
  }
}

void setServoToAngle(uint8_t I, int ANGLE) {
  setSweepEnabled(I, false);  
  SERVOANGLE[I] = constrain((float)ANGLE, 0.0f, 180.0f);
  applyServoAngle(I);
}

void configureSweep(uint8_t I, int MINANGLE, int MAXANGLE, int SPEED) {
  SERVOMINANGLE[I] = constrain(MINANGLE, 0, 180);
  SERVOMAXANGLE[I] = constrain(MAXANGLE, SERVOMINANGLE[I] + 5, 180);
  SERVOSWEEPSPEED[I] = constrain(SPEED, 1, 180);

 
  SERVOANGLE[I] = constrain(SERVOANGLE[I], SERVOMINANGLE[I], SERVOMAXANGLE[I]);

  if (SERVOANGLE[I] <= SERVOMINANGLE[I]) SERVODIRECTION[I] = 1;
  else if (SERVOANGLE[I] >= SERVOMAXANGLE[I]) SERVODIRECTION[I] = -1;

  applyServoAngle(I);
}

// ---------------------------------------------------------------------------
// Serial command parsing
// ---------------------------------------------------------------------------

void processCommand() {
  COMMANDBUFFER[COMMANDLENGTH] = '\0';

  if (strcmp(COMMANDBUFFER, "S") == 0) {
  
    ISSCANNING = true;
    NEXTMEASUREMENTTIME = millis();
  }
  else if (strcmp(COMMANDBUFFER, "P") == 0) {
 
    ISSCANNING = false;
    stopMeasurement();
  }
  else if (COMMANDBUFFER[0] == 'D' && COMMANDBUFFER[1] != '\0') {
   
    char *END;
    unsigned long DELAYVALUE = strtoul(COMMANDBUFFER + 1, &END, 10);
    if (*END == '\0' && DELAYVALUE <= 60000) {
      SCANDELAYMS = DELAYVALUE;
    }
  }
  else if (COMMANDBUFFER[0] == 'A') {
   
    char *COMMA = strchr(COMMANDBUFFER + 1, ',');
    if (COMMA != NULL) {
      *COMMA = '\0';
      char *MOTOREND, *ANGLEEND;
      long MOTOR = strtol(COMMANDBUFFER + 1, &MOTOREND, 10);
      long ANGLE = strtol(COMMA + 1, &ANGLEEND, 10);

      if (*MOTOREND == '\0' && *ANGLEEND == '\0' &&
          MOTOR >= 1 && MOTOR <= 2 && ANGLE >= 0 && ANGLE <= 180) {
        setServoToAngle(MOTOR - 1, ANGLE);
      }
    }
  }
  else if (COMMANDBUFFER[0] == 'R') {
    
    char *COMMA1 = strchr(COMMANDBUFFER + 1, ',');
    char *COMMA2 = COMMA1 ? strchr(COMMA1 + 1, ',') : NULL;
    char *COMMA3 = COMMA2 ? strchr(COMMA2 + 1, ',') : NULL;

    if (COMMA1 && COMMA2 && COMMA3) {
      *COMMA1 = '\0';
      *COMMA2 = '\0';
      *COMMA3 = '\0';

      char *MOTOREND, *MINEND, *MAXEND, *SPEEDEND;
      long MOTOR = strtol(COMMANDBUFFER + 1, &MOTOREND, 10);
      long MINANGLE = strtol(COMMA1 + 1, &MINEND, 10);
      long MAXANGLE = strtol(COMMA2 + 1, &MAXEND, 10);
      long SPEED = strtol(COMMA3 + 1, &SPEEDEND, 10);

      if (*MOTOREND == '\0' && *MINEND == '\0' &&
          *MAXEND == '\0' && *SPEEDEND == '\0' &&
          MOTOR >= 1 && MOTOR <= 2 &&
          MINANGLE >= 0 && MINANGLE <= 175 &&
          MAXANGLE >= MINANGLE + 5 && MAXANGLE <= 180 &&
          SPEED >= 1 && SPEED <= 180) {
        configureSweep(MOTOR - 1, MINANGLE, MAXANGLE, SPEED);
      }
    }
  }
  else if (COMMANDBUFFER[0] == 'W') {
   
    char *COMMA = strchr(COMMANDBUFFER + 1, ',');
    if (COMMA != NULL) {
      *COMMA = '\0';
      char *MOTOREND, *STATEEND;
      long MOTOR = strtol(COMMANDBUFFER + 1, &MOTOREND, 10);
      long STATE = strtol(COMMA + 1, &STATEEND, 10);

      if (*MOTOREND == '\0' && *STATEEND == '\0' &&
          MOTOR >= 1 && MOTOR <= 2 && (STATE == 0 || STATE == 1)) {
        setSweepEnabled(MOTOR - 1, STATE == 1);
      }
    }
  }

  COMMANDLENGTH = 0;
}

void readSerialInput() {
  while (Serial.available() > 0) {
    char C = Serial.read();

    if (C == '\n') {
      processCommand();
    } else if (C != '\r') {
      if (COMMANDLENGTH < sizeof(COMMANDBUFFER) - 1) {
        COMMANDBUFFER[COMMANDLENGTH++] = C;
      } else {
        COMMANDLENGTH = 0;   
      }
    }
  }
}

// ---------------------------------------------------------------------------
// Arduino entry points
// ---------------------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  Wire.begin();

  SCALE1.begin(LOADCELLDATAPIN1, LOADCELLCLOCKPIN1);
  SCALE2.begin(LOADCELLDATAPIN2, LOADCELLCLOCKPIN2);
  Serial.println("Dual HX711 load cells starting; empty platforms will be auto-tared.");


  for (uint8_t I = 0; I < 2; I++) {
    SERVOS[I].attach(SERVOPINS[I]);
    SERVOS[I].write(90);
  }

  Serial.println("Starting AS7265X...");

  SENSORISREADY = SPECTRALSENSOR.begin();
  if (!SENSORISREADY) {
    Serial.println("ERROR: Sensor not detected! Servo control remains available.");
  } else {
    Serial.println("AS7265X READY!");
    Serial.println("--------------------");
  }

  
  Serial.println("SV1,90");
  Serial.println("SV2,90");
  reportSweepState(0);
  reportSweepState(1);
}

void loop() {
  readSerialInput();
  updateSweeps();
  updateLoadCellReadings();


  if (!ISSCANNING || !SENSORISREADY) {
    stopMeasurement();
    delay(10);
    return;
  }

  unsigned long NOW = millis();

  if (!MEASUREMENTRUNNING) {
    if ((long)(NOW - NEXTMEASUREMENTTIME) >= 0) {
      startMeasurement();
    }
  } else if (SPECTRALSENSOR.dataAvailable()) {
    stopMeasurement();
    printMeasurement();
    NEXTMEASUREMENTTIME = millis() + SCANDELAYMS;
  } else if (NOW - MEASUREMENTSTARTTIME >= 1200) {
  
    stopMeasurement();
    Serial.println("ERROR: NIR measurement timed out");
    NEXTMEASUREMENTTIME = millis() + SCANDELAYMS;
  }

  delay(1);
}