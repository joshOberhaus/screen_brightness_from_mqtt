# screen_brightness_from_mqtt

Consume power values from MQTT and map them to display brightness.
I mainly use this because my cycling power (and power target), are on my MQTT.
To fight my laziness, and desire to not use a stationary trainer, I map this to my screen brightness while distracting myself.

I use a slightly modified [Flux](https://github.com/pitisec/Flux) to send the MQTT messages, I hope to open source that soon on the newer version of Flux.

This has been tested on MacOS (15.7), and Windows 11. No reason it shouldn't work on Linux.

## Configuration
Copy the example config and update values:

- brightness_from_mqtt.example.ini → brightness_from_mqtt.ini

You can also set $BRIGHTNESS_FROM_MQTT_CONFIG to point to a config path.

Config lookup order:
1. $BRIGHTNESS_FROM_MQTT_CONFIG
2. Same directory as the executable (when frozen)
3. Current working directory
4. Script directory

## macOS brightness dependency
There is no python library which can handle changing Mac's brightness, because this can apparently only be accomplished through some hacky method. A CLI tool brightness, accomplishes this. An outdated version which does not work on my M3 is on homebrew, but installing from source or my homebrew-tap should work.
Install the brightness CLI utility with:

- scripts/install_brightness_mac.sh

## One-click launch scripts
These scripts create/activate a local venv and run the client:

- macOS: scripts/run_brightness_from_mqtt_mac.command
- Windows: scripts/run_brightness_from_mqtt_windows.bat

## Build executables
These scripts create a venv, install deps, and build a one-file executable.

- macOS: scripts/build_mac.sh
- Windows: scripts/build_windows.ps1
