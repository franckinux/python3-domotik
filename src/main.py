#!/usr/bin/env python3

import argparse
import asyncio
import importlib
import logging
import sys

from aiohttp import web
# import aiohttp_cors

import config
from bmp280 import init as init_bmp280
from bmp280 import close as close_bmp280
from bmp280 import get_pressure as get_pressure_data
from bmp280 import get_sea_level_pressure as get_sea_level_pressure_data
from bmp280 import get_temperature as get_temperature_data
from doorbell import close as close_doorbell
from doorbell import init as init_doorbell
import i2c
from linky import close as close_linky
from linky import get_data as get_linky_data
from linky import init as init_linky
from ups import init as init_ups

logger = logging.getLogger()
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter("%(asctime)s %(module)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)


async def linky_handler(request):
    data = get_linky_data()
    return web.json_response({"data": data})


async def pressure_handler(request):
    value = get_pressure_data()
    return web.json_response({"data": {"pressure": value}})


async def pressure_at_sea_level_handler(request):
    value = get_sea_level_pressure_data()
    return web.json_response({"data": {"sea-level-pressure": value}})


async def temperature_handler(request):
    value = get_temperature_data()
    return web.json_response({"data": {"temperature": value}})


async def startup(app):
    # set log level of modules logger
    for lg_name, lg_config in config.loggers.items():
        try:
            importlib.import_module(lg_name)
        except ModuleNotFoundError:
            logger.warning(f"module {lg_name} not found")
            continue

        if lg_name in logging.Logger.manager.loggerDict.keys():
            logging.getLogger(lg_name).setLevel(lg_config.level)

    i2c.open_bus(config.i2c.bus)

    init_bmp280(config.general.altitude)
    await init_doorbell()
    await init_linky()
    await init_ups()


async def cleanup(app):
    await close_bmp280()
    await close_doorbell()
    await close_linky()

    i2c.close_bus


async def make_app():
    # run a server
    app = web.Application()

    app.on_startup.append(startup)
    app.on_cleanup.append(cleanup)

    app.router.add_get("/linky", linky_handler)
    app.router.add_get("/pressure", pressure_handler)
    app.router.add_get("/pressure/sealevel", pressure_at_sea_level_handler)
    app.router.add_get("/temperature", temperature_handler)

    # cors = aiohttp_cors.setup(app, defaults={
    #     "*": aiohttp_cors.ResourceOptions(
    #         allow_credentials=True,
    #         expose_headers="*",
    #         allow_headers="*",
    #     )
    # })
    #
    # # Configure CORS on all routes.
    # for route in list(app.router.routes()):
    #     cors.add(route)

    return app


async def run(config_filename: str):
    config.read(config_filename)

    # await init()

    app = await make_app()

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.network.server_port)
    await site.start()
    while True:
        await asyncio.sleep(1)


async def close():
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-c", "--config", default="config.toml")
    args = parser.parse_args()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        logger.info("server started")
        loop.run_until_complete(run(args.config))
    except KeyboardInterrupt:
        pass
    finally:
        loop.run_until_complete(close())
        loop.stop()
        logger.info("server stopped")
