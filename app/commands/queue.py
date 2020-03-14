import logging
import time

import click
from flask.cli import AppGroup
from flask import current_app

try:
    import requests
except ImportError:
    pass

from app.lib.printer import print_queue, PrintError


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)

commands = AppGroup('queue')


@commands.command('print')
def run_print_queue():
    try:
        requests
    except NameError:
        raise RuntimeError("Requests is not installed")

    url = current_app.config['API_URL'] + '/print/job'
    while True:
        try:
            logger.debug("Get queued: %s", url)
            res = requests.get(url)
            res.raise_for_status()
            job = res.json()['result']
            if job is None:
                # There's no print job, just continue
                continue

            try:
                # Print the job, and tell the server it's done
                logger.debug("Printing job: %s", job)
                id = print_queue(job)
            except:
                logger.error("Failed to print", exc_info=True)
            else
                try:
                    logger.debug("Inform api %s is done", id)
                    requests.post(url + '/' + id).raise_for_status()
                except:
                    logger.error("Failed to notify api job is done", exc_info=True)
        except:
            logger.error("Failed to get the print job", exc_info=True)
            time.sleep(10)
