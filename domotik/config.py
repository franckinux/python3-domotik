import logging
from pathlib import Path

import tomli

from domotik.typem import DoorbellConfig
from domotik.typem import GeneralConfig
from domotik.typem import I2cConfig
from domotik.typem import LinkyConfig
from domotik.typem import MqttConfig
from domotik.typem import UpsConfig

doorbell = None
general = None
i2c = None
linky = None
loggers = {}
mqtt = None
ups = None

_module = []


def parse_log_config(data: dict):
    global loggers
    global _module

    for k, v in data.items():
        _module.append(k)
        try:
            loggers[".".join(_module)] = getattr(logging, v["level"])
            _module.pop()
        except KeyError:
            parse_log_config(v)


def read(config_filename: str):
    config_file = Path(config_filename)
    with open(config_file, "rb") as f:
        raw_config = tomli.load(f)

    global doorbell
    doorbell = DoorbellConfig(**raw_config["doorbell"])

    global general
    general = GeneralConfig(**raw_config["general"])

    global i2c
    i2c = I2cConfig(**raw_config["i2c"])

    global linky
    linky = LinkyConfig(**raw_config["linky"])

    global loggers
    parse_log_config(raw_config["logger"][0])

    global mqtt
    mqtt = MqttConfig(**raw_config["mqtt"])

    global ups
    ups = UpsConfig(**raw_config["ups"])

