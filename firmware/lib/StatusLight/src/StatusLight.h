#pragma once

#include <Arduino.h>
#include <Preferences.h>

enum class StatusState {
    Free,
    Busy,
    Call,
};

const char* statusStateName(StatusState state);
bool parseStatusState(const char* name, StatusState& state);

class StatusLight {
public:
    void begin();
    void setState(StatusState state);
    StatusState state() const;
    const char* stateName() const;

private:
    void writeLed();

    Preferences preferences;
    StatusState currentState = StatusState::Free;
};
