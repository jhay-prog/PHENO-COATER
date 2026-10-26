/*
  PhenoCoater IR Bean Counter
  IR sensor OUT -> Arduino pin 2
  Serial baud rate: 115200

  Commands:
    START_SAMPLE -> Reset count and start counting
    STOP_SAMPLE  -> Stop counting and report final count
*/

#include <string.h>

const byte IR_PIN = 2;
const int DETECTED_STATE = LOW;
const unsigned long DEBOUNCE_MS = 40;
const unsigned long COUNT_COOLDOWN_MS = 1500;
const size_t COMMAND_BUFFER_SIZE = 24;

unsigned long beanCount = 0;
bool sampleActive = false;
bool countCooldownActive = false;

int lastRawState = HIGH;
int stableState = HIGH;
unsigned long lastChangeTime = 0;
unsigned long lastBeanCountTime = 0;

char commandBuffer[COMMAND_BUFFER_SIZE];
size_t commandLength = 0;

void startSample() {
  beanCount = 0;
  sampleActive = true;

  stableState = digitalRead(IR_PIN);
  lastRawState = stableState;
  lastChangeTime = millis();
  countCooldownActive = false;

  Serial.println("SAMPLE_STARTED");
  Serial.println("BEAN_COUNT: 0");
}

void stopSample() {
  if (!sampleActive) {
    return;
  }

  sampleActive = false;

  Serial.print("FINAL_BEAN_COUNT: ");
  Serial.println(beanCount);
  Serial.println("SAMPLE_COMPLETE");
}

void readCommands() {
  while (Serial.available() > 0) {
    const char incoming = static_cast<char>(Serial.read());

    if (incoming == '\r') {
      continue;
    }

    if (incoming == '\n') {
      commandBuffer[commandLength] = '\0';

      if (strcmp(commandBuffer, "START_SAMPLE") == 0) {
        startSample();
      } else if (strcmp(commandBuffer, "STOP_SAMPLE") == 0) {
        stopSample();
      }

      commandLength = 0;
    } else if (commandLength < COMMAND_BUFFER_SIZE - 1) {
      commandBuffer[commandLength++] = incoming;
    } else {
      commandLength = 0;
    }
  }
}

void setup() {
  pinMode(IR_PIN, INPUT_PULLUP);
  Serial.begin(115200);

  stableState = digitalRead(IR_PIN);
  lastRawState = stableState;
  lastChangeTime = millis();

  Serial.println("PHENOCOATER_BEAN_COUNTER_READY");
}

void loop() {
  readCommands();

  if (!sampleActive) {
    return;
  }

  const int rawState = digitalRead(IR_PIN);

  if (rawState != lastRawState) {
    lastRawState = rawState;
    lastChangeTime = millis();
  }

  if (millis() - lastChangeTime >= DEBOUNCE_MS &&
      rawState != stableState) {
    stableState = rawState;

    if (stableState == DETECTED_STATE) {
      if (!countCooldownActive) {
        beanCount++;
        lastBeanCountTime = millis();
        countCooldownActive = true;

        Serial.print("BEAN_COUNT: ");
        Serial.println(beanCount);
      }
    }
  }

  if (countCooldownActive &&
      stableState != DETECTED_STATE &&
      millis() - lastBeanCountTime >= COUNT_COOLDOWN_MS) {
    countCooldownActive = false;
  }
}