#!/usr/bin/env python3

import asyncio
import logging

import pigpio
from aiomqtt import Client
from paho.mqtt.subscribeoptions import SubscribeOptions

import config

_callback = None
_loop = None
_pi = None

_running = True
_task_ring = None
_task_client = None

# logger initial setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


async def init():
    global _callback
    global _loop
    global _pi
    global _task_client

    if _pi is None:
        _pi = pigpio.pi()

    _pi.set_mode(config.doorbell.bell_gpio, pigpio.OUTPUT)
    _pi.set_mode(config.doorbell.button_gpio, pigpio.INPUT)
    _pi.set_pull_up_down(config.doorbell.button_gpio, pigpio.PUD_DOWN)
    _pi.set_glitch_filter(config.doorbell.button_gpio, 500)

    _loop = asyncio.get_event_loop()

    _callback = _pi.callback(
        config.doorbell.button_gpio,
        pigpio.EITHER_EDGE,
        __callback
    )

    _task_client = asyncio.create_task(__subscribe())


async def __publish():
    async with Client(config.mqtt.hostname, config.mqtt.port) as client:
        await client.publish("home/doorbell/pressed")


def __callback(gpio: int, level: int, tick: int):
    if level == 1:
        logger.info("door bell button pressed")
        _loop.create_task(__publish())


async def __ring():
    global _task_ring

    try:
        for s in range(5):
            _pi.write(config.doorbell.bell_gpio, True)
            logger.debug("ding")
            await asyncio.sleep(0.4)

            if not _running:
                return

            _pi.write(config.doorbell.bell_gpio, False)
            logger.debug("dong")
            await asyncio.sleep(1.2)

            if not _running:
                return
    finally:
        _pi.write(config.doorbell.bell_gpio, False)
        _task_ring = None


async def __subscribe():
    global _task_ring

    async with Client(config.mqtt.hostname, config.mqtt.port) as client:
        await client.subscribe("home/doorbell/ring")
        try:
            async for message in client.messages:
                if _task_ring is None:
                    logger.info("ring the bell")
                    # the task is run using the loop of the main thread enabling
                    # _task to be tested without using a critical section
                    _task_ring = _loop.create_task(__ring())
        except (asyncio.CancelledError, KeyboardInterrupt):
            pass


async def close():
    global _callback
    global _pi
    global _running
    global _task_client
    global _task_ring

    logger.debug("closing")

    if _task_client is not None:
        try:
            _task_client.cancel()
            await _task_client
        except asyncio.CancelledError:
            pass
        _task_client = None

    _running = False
    if _task_ring is not None:
        await _task_ring
        _task_ring = None

    if _pi is not None:
        if _callback is not None:
            _callback.cancel()
            _callback = None

        _pi.stop()
        _pi = None


async def run(config_filename: str):
    config.read(config_filename)

    await init()

    await asyncio.sleep(1)

    __callback(0, 0, 0)

    await asyncio.sleep(20)


# main is used for test purpose as standalone
if __name__ == "__main__":
    import argparse
    import sys

    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter("%(asctime)s %(module)s %(levelname)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="config.toml")
    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run(args.config))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(close())
        loop.stop()
        logger.info("done")
