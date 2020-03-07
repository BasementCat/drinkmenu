import logging
import re

from flask import current_app

from escpos import BluetoothConnection
from escpos.impl.epson import GenericESCPOS

logger = logging.getLogger(__name__)


def print_stuff(name=None, drink_name=None, drink=None, drink_components=None):
    try:
        addr = current_app.config['ESCPOS_PRINTER_BT_ADDR']
        conn = BluetoothConnection.create(addr)
        printer = GenericESCPOS(conn)
        printer.init()

        fmt = list(map(str.strip, current_app.config['ESCPOS_PRINTER_FMT'].split(',')))
        for item in fmt:
            m = re.match(r'^lf(\d+)?$', item)
            if m:
                printer.lf(lines=int(m.group(1) or 1))
                continue

            m = re.match(r'^([lcr])$', item)
            if m:
                if m.group(1) == 'l':
                    printer.justify_left()
                elif m.group(1) == 'c':
                    printer.justify_center()
                elif m.group(1) == 'r':
                    printer.justify_right()
                continue

            m = re.match(r'^s(\d+)(?::(\d+))?$', item)
            if m:
                w = m.group(1)
                h = m.group(2) if m.group(2) is not None else w
                printer.set_text_size(int(w), int(h))
                continue

            # TODO: expanded/condensed/emphasized

            if locals().get(item):
                printer.text(locals()[item])
    except KeyError as e:
        logger.error("Missing config key %s", str(e))
    except:
        logger.error("Error accessing printer", exc_info=True)
