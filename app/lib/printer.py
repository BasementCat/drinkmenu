import logging
import re
import time
import uuid
import os

from flask import current_app

have_printer_imports = False
try:
    from escpos import printer
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
    return {
        'id': order.doc_id,
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


def print_order(printer, data):
    for c in current_app.config.get('ESCPOS_PRINTER_FMT', []):
        if c['command'] == 'text':
            printer.text(c['value'])
        elif c['command'] == 'logo':
            if current_app.config.get('ESCPOS_PRINTER_IMAGE_IMPL'):
                c = RuntimeConfig.get_single()
                if c.logo:
                    printer.image(
                        os.path.abspath(os.path.join(current_app.config['DATA_DIRECTORY'], 'images', c.logo)),
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
