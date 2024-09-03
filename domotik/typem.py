from dataclasses import dataclass
# from enum import auto
# from enum import Enum
# from enum import IntEnum


@dataclass
class DoorbellConfig:
    bell_gpio: int
    button_gpio: int


@dataclass
class GeneralConfig:
    altitude: float


@dataclass
class I2cConfig:
    bus: int


@dataclass
class LinkyConfig:
    server_port: int
    serial_port: int
    baudrate: int
    bytesize: str
    stopbits: str
    parity: str


@dataclass
class MqttConfig:
    host: str
    port: int


@dataclass
class UpsConfig:
    ac220_gpio: int
    buzzer_gpio: int
