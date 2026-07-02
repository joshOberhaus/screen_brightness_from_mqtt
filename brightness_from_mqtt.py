import configparser
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import paho.mqtt.client as mqtt
import screen_brightness_control as sbc

CONFIG_ENV_VAR = "BRIGHTNESS_FROM_MQTT_CONFIG"
DEFAULT_CONFIG_NAME = "brightness_from_mqtt.ini"


def on_connect(mqttclient, userdata, flags, reason_code, properties):
    print("Connected with result code " + str(reason_code))
    mode = userdata["mode"]
    if mode in ("power", "combined"):
        mqttclient.subscribe(userdata["mqtt_topic"])
    if mode in ("heart_rate", "combined"):
        mqttclient.subscribe(userdata["hr_topic"])


def on_power_message(mqttclient, userdata, msg):
    print(msg.topic + " " + str(msg.payload))
    try:
        power = int(msg.payload.decode("utf-8"))
        max_power = userdata["max_power"]
        min_brightness = userdata["min_brightness"]
        max_brightness = userdata["max_brightness"]
        slope = userdata["slope"]
        intercept = userdata["intercept"]

        if power > max_power:
            brightness = max_brightness
        else:
            brightness = slope * power + intercept
            brightness = min(brightness, max_brightness)
            brightness = max(brightness, min_brightness)

        brightness = int(round(brightness))
        userdata["last_power_brightness"] = brightness

        if userdata["mode"] == "power":
            set_brightness(brightness)
        else:
            # combined: HR overrides when out of zone (hr=0 means no data yet)
            hr = userdata["current_hr"]
            if hr > 0 and not (userdata["hr_min"] <= hr <= userdata["hr_max"]):
                set_brightness(userdata["hr_out_of_zone_brightness"])
            else:
                set_brightness(brightness)
    except ValueError:
        pass


def on_hr_message(mqttclient, userdata, msg):
    print(msg.topic + " " + str(msg.payload))
    try:
        hr = int(msg.payload.decode("utf-8"))
        userdata["current_hr"] = hr
        in_zone = userdata["hr_min"] <= hr <= userdata["hr_max"]

        if userdata["mode"] == "heart_rate":
            brightness = userdata["hr_in_zone_brightness"] if in_zone else userdata["hr_out_of_zone_brightness"]
            set_brightness(brightness)
        else:
            # combined: restore last power-based brightness when back in zone
            if in_zone:
                set_brightness(userdata["last_power_brightness"])
            else:
                set_brightness(userdata["hr_out_of_zone_brightness"])
    except ValueError:
        pass


def on_message(mqttclient, userdata, msg):
    mode = userdata["mode"]
    if mode in ("heart_rate", "combined") and msg.topic == userdata["hr_topic"]:
        on_hr_message(mqttclient, userdata, msg)
    elif mode in ("power", "combined") and msg.topic == userdata["mqtt_topic"]:
        on_power_message(mqttclient, userdata, msg)


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config not found at {config_path}. Copy the example file and update values."
        )

    config = configparser.ConfigParser()
    config.read(config_path)

    mqtt_config = config["mqtt"]
    brightness_config = config["brightness"]

    mode = mqtt_config.get("mode", "power")
    if mode not in ("power", "heart_rate", "combined"):
        raise ValueError(f"Invalid mode '{mode}'. Must be power, heart_rate, or combined.")

    result = {
        "mode": mode,
        "mqtt_host": mqtt_config.get("host", "localhost"),
        "mqtt_port": mqtt_config.getint("port", 1883),
        "mqtt_topic": mqtt_config.get("topic", "cycling/power"),
        "mqtt_keepalive": mqtt_config.getint("keepalive", 60),
        "client_id": mqtt_config.get("client_id", "brightness_from_mqtt"),
        "max_power": brightness_config.getint("max_power", 110),
        "min_brightness": brightness_config.getint("min_brightness", 2),
        "max_brightness": brightness_config.getint("max_brightness", 100),
        "slope": brightness_config.getfloat("slope", 1.25),
        "intercept": brightness_config.getfloat("intercept", -25),
        # mutable state tracked in userdata
        "current_hr": 0,
        "last_power_brightness": brightness_config.getint("min_brightness", 2),
    }

    if mode in ("heart_rate", "combined"):
        if "heart_rate" not in config:
            raise ValueError(f"Mode '{mode}' requires a [heart_rate] section in the config.")
        hr_config = config["heart_rate"]
        result.update({
            "hr_topic":               hr_config.get("topic", "auuki/heartRate"),
            "hr_min":                 hr_config.getint("min_bpm", 115),
            "hr_max":                 hr_config.getint("max_bpm", 145),
            "hr_in_zone_brightness":  hr_config.getint("in_zone_brightness", 100),
            "hr_out_of_zone_brightness": hr_config.getint("out_of_zone_brightness", 5),
        })

    return result


def set_brightness(value: int) -> None:
    system = platform.system().lower()
    if system == "darwin" and shutil.which("brightness"):
        result = subprocess.run(
            ["brightness", str(value / 100)],
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return
        if result.stderr:
            print(result.stderr.strip())

    sbc.set_brightness(value)


def resolve_config_path() -> Path:
    config_override = os.environ.get(CONFIG_ENV_VAR)
    if config_override:
        return Path(config_override).expanduser()

    candidates = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / DEFAULT_CONFIG_NAME)
    candidates.append(Path.cwd() / DEFAULT_CONFIG_NAME)
    candidates.append(Path(__file__).resolve().parent / DEFAULT_CONFIG_NAME)

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return candidates[0]


if __name__ == "__main__":
    config_file = resolve_config_path()
    config = load_config(config_file)
    mqttclient = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=config["client_id"], userdata=config)
    mqttclient.on_connect = on_connect
    mqttclient.on_message = on_message
    mqttclient.connect(
        config["mqtt_host"],
        config["mqtt_port"],
        config["mqtt_keepalive"],
    )
    mqttclient.loop_forever()
