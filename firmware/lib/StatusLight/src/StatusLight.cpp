#include "StatusLight.h"

namespace {
constexpr uint8_t kRgbLedPin = 48;
constexpr uint8_t kBrightness = 24;

struct Color {
    uint8_t red;
    uint8_t green;
    uint8_t blue;
};

Color colorForState(StatusState state) {
    switch (state) {
        case StatusState::Free:
            return {0, kBrightness, 0};
        case StatusState::Busy:
            return {0, 0, kBrightness};
        case StatusState::Call:
            return {kBrightness, 0, 0};
    }
    return {0, 0, 0};
}
}

const char* statusStateName(StatusState state) {
    switch (state) {
        case StatusState::Free:
            return "free";
        case StatusState::Busy:
            return "busy";
        case StatusState::Call:
            return "call";
    }
    return "free";
}

bool parseStatusState(const char* name, StatusState& state) {
    if (strcmp(name, "free") == 0) {
        state = StatusState::Free;
        return true;
    }
    if (strcmp(name, "busy") == 0) {
        state = StatusState::Busy;
        return true;
    }
    if (strcmp(name, "call") == 0) {
        state = StatusState::Call;
        return true;
    }
    return false;
}

void StatusLight::begin() {
    preferences.begin("status-light", false);
    const String savedState = preferences.getString("state", "free");
    StatusState restoredState;
    if (parseStatusState(savedState.c_str(), restoredState)) {
        currentState = restoredState;
    }
    writeLed();
}

void StatusLight::setState(StatusState state) {
    if (state == currentState) {
        return;
    }
    currentState = state;
    writeLed();
    preferences.putString("state", statusStateName(state));
}

StatusState StatusLight::state() const {
    return currentState;
}

const char* StatusLight::stateName() const {
    return statusStateName(currentState);
}

void StatusLight::writeLed() {
    const Color color = colorForState(currentState);
    rgbLedWrite(kRgbLedPin, color.red, color.green, color.blue);
}
