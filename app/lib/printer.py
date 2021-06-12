import logging
import re
import time
import uuid
import os
import tempfile

from flask import current_app, url_for

have_printer_imports = False
try:
    from escpos import printer
    import requests
    have_printer_imports = True
except ImportError:
    pass

from app.database import Order, Drink, DrinkComponent, RuntimeConfig


logger = logging.getLogger(__name__)


class PrintError(Exception):
    pass


def auto_cut():
    if current_app.config.get('ESCPOS_PRINTER_HAS_CUTTER'):
        for c in current_app.config.get('ESCPOS_PRINTER_FMT', []):
            if c.get('command') == 'cut':
                return True
    return False


def queue_order_to_print(order=None, order_id=None, auto=False, force=False):
    if not order:
        if not order_id:
            raise PrintError("Need an order or ID")
        order = Order.get(order_id)
        if not order:
            raise PrintError("No such order")

    if force or not order.printed:
        if not auto_cut():
            if auto:
                # Called on order save - don't automatically print
                return
            for o in Order.find(custom_conds=[lambda q: q.print_queued > 0]):
                if time.time() - o.print_queued < 10:
                    raise PrintError("A print job is already queued")
        order.print_queued = time.time()
        order.save()

    return order


def get_queued_order():
    for o in Order.find(custom_conds=[lambda q: q.print_queued > 0]):
        if auto_cut() or time.time() - o.print_queued < 10:
            return o


def get_order_printable(order):
    drink = None
    if order.drink:
        drink = Drink.get(order.drink)

    drink_components = None
    if order.drink_components:
        drink_components = DrinkComponent.find(*order.drink_components)

    strength = f' [{order.strength}]' if order.strength else ''

    c = RuntimeConfig.get_single()
    logo = None
    if c.logo:
        logo = url_for('index.images', name=c.logo, mode='full', _external=True)

    return {
        'id': order.doc_id,
        'logo': logo,
        'name': order.name,
        'drink_name': (order.drink_name + strength) if order.drink_name else None,
        'drink': (drink.name + strength) if drink else None,
        'drink_components': ', '.join((c.name for c in drink_components)) if drink_components else None
    }


def clear_queued_order(order=None, order_id=None):
    if not order:
        if not order_id:
            raise PrintError("Need an order or ID")
        order = Order.get(order_id)
        if not order:
            raise PrintError("No such order")
    order.printed = True
    order.print_queued = 0
    order.save()
    return order.doc_id


logo_cache = {}


def print_order(printer, data):
    if data.get('logo') and data['logo'] not in logo_cache:
        fname = os.path.join(tempfile.gettempdir(), data['logo'].split('/')[-1])
        res = requests.get(data['logo'], stream=True)
        res.raise_for_status()
        with open(fname, 'wb') as fp:
            for chunk in res.iter_content(chunk_size=1024):
                fp.write(chunk)
        logo_cache[data['logo']] = fname

    for c in current_app.config.get('ESCPOS_PRINTER_FMT', []):
        if c['command'] == 'text':
            printer.text(c['value'])
        elif c['command'] == 'logo':
            if current_app.config.get('ESCPOS_PRINTER_IMAGE_IMPL'):
                if data.get('logo'):
                    printer.image(
                        logo_cache[data['logo']],
                        impl=current_app.config['ESCPOS_PRINTER_IMAGE_IMPL']
                    )
        elif c['command'] == 'font':
            args = {}
            if c.get('align'):
                args['align'] = c['align']
            if c.get('size'):
                args['width'], args['height'] = c['size']
            printer.set(**args)
        elif c['command'] in ('name', 'drink_name', 'drink', 'drink_components'):
            if data.get(c['command']):
                printer.text(data[c['command']] + '\n')
        elif c['command'] == 'cut':
            if current_app.config.get('ESCPOS_PRINTER_HAS_CUTTER'):
                printer.cut(mode='PART' if c.get('partial') else 'FULL')


def get_printer():
    if not have_printer_imports:
        raise PrintError("Printer libraries are not installed")

    if current_app.config.get('ESCPOS_PRINTER_MODE') == 'usb':
        return printer.Usb(*current_app.config['ESCPOS_PRINTER_ID'])
    else:
        raise PrintError("Invalid printer mode")
