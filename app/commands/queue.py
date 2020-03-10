import logging
import time

import click
from flask.cli import AppGroup
from flask import current_app

import requests

from app.lib.printer import print_queue, PrintError


logger = logging.getLogger(__name__)

commands = AppGroup('queue')


@commands.command('print')
def run_print_queue():
    url = current_app.config['API_URL'] + '/print/job'
    while True:
        try:
            res = requests.get(url)
            res.raise_for_status()
            job = res.json()['result']
            if job is None:
                # There's no print job, just continue
                continue

            try:
                # Print the job, and tell the server it's done
                id = print_queue(job)
                requests.post(url + '/' + id)
            except PrintError:
                logger.error("Failed to print", exc_info=True)
        except:
            logger.error("Failed to get the print job", exc_info=True)
            time.sleep(10)
