import logging
import re
import time
import uuid

from flask import current_app

have_printer_imports = False
try:
    from escpos import BluetoothConnection
    from escpos.impl.epson import GenericESCPOS
    have_printer_imports = True
except ImportError:
    pass

logger = logging.getLogger(__name__)

print_job = None


class PrintError(Exception):
    pass


def print_stuff(order_id, name=None, drink_name=None, drink=None, drink_components=None):
    global print_job
    if print_job:
        if time.time() - print_job['t'] < 10:
            raise PrintError("A print job is already queued")
        print_job = None

    queue = []
    def q(f, *a, **ka):
        queue.append({'f': f, 'a': a, 'ka': ka})

    try:
        fmt = list(map(str.strip, current_app.config['ESCPOS_PRINTER_FMT'].split(',')))
        for item in fmt:
            m = re.match(r'^lf(\d+)?$', item)
            if m:
                q('lf', lines=int(m.group(1) or 1))
                continue

            m = re.match(r'^([lcr])$', item)
            if m:
                if m.group(1) == 'l':
                    q('justify_left')
                elif m.group(1) == 'c':
                    q('justify_center')
                elif m.group(1) == 'r':
                    q('justify_right')
                continue

            m = re.match(r'^s(\d+)(?::(\d+))?$', item)
            if m:
                w = m.group(1)
                h = m.group(2) if m.group(2) is not None else w
                q('set_text_size', int(w), int(h))
                continue

            # TODO: expanded/condensed/emphasized

            if locals().get(item):
                q('text', locals()[item])

            if queue:
                print_job = {'i': order_id, 'u': str(uuid.uuid4()), 't': time.time(), 'c': queue}
    except KeyError as e:
        raise PrintError(f"Missing config key {e}")


def get_print_job():
    if print_job:
        if time.time() - print_job['t'] < 10:
            return print_job


def clear_print_job(id):
    global print_job
    if print_job:
        if print_job['u'] == id:
            print_job = None
            return True
    return False


def print_queue(job):
    if not have_printer_imports:
        raise PrintError("Printer libraries are not installed")

    try:
        addr = current_app.config['ESCPOS_PRINTER_BT_ADDR']
        conn = BluetoothConnection.create(addr)
        printer = GenericESCPOS(conn)
        printer.init()

        for fn in job['c']:
            getattr(printer, fn['f'])(*fn['a'], **fn['ka'])

        return job['u']
    except KeyError as e:
        raise PrintError(f"Missing config key {e}")
