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


def on_connect(mqttclient, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    mqttclient.subscribe(userdata["mqtt_topic"])


def on_message(mqttclient, userdata, msg):
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

        set_brightness(int(round(brightness)))
    except ValueError:
        pass


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config not found at {config_path}. Copy the example file and update values."
        )

    config = configparser.ConfigParser()
    config.read(config_path)

    mqtt_config = config["mqtt"]
    brightness_config = config["brightness"]

    return {
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
    }


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
    mqttclient = mqtt.Client(client_id=config["client_id"], userdata=config)
    mqttclient.on_connect = on_connect
    mqttclient.on_message = on_message
    mqttclient.connect(
        config["mqtt_host"],
        config["mqtt_port"],
        config["mqtt_keepalive"],
    )
    mqttclient.loop_forever()
