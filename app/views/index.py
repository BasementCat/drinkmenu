import os

from flask import (
    Blueprint,
    render_template,
    request,
    abort,
    flash,
    redirect,
    url_for,
    send_file,
    current_app,
    session,
)

import PIL
from PIL import Image

from app.database import Drink, DrinkComponent, Order, SavedOrder, Event, Device
from app.forms.orders import OrderForm
from app.lib.auth import require_login, is_house_device
from app.lib.printer import queue_order_to_print, PrintError


app = Blueprint('index', __name__)


@app.route('/init-device/<device_id>', methods=['GET'])
def init_device(device_id):
    session['device_id'] = device_id
    dev = Device.get_by_devid(device_id)
    if not dev:
        dev = Device(device_id=device_id)
        dev.save()
    return redirect(url_for('.index'))


@app.route('/', methods=['GET'])
def index():
    # drinks = Drink.find(is_orderable=True, in_stock=True, sort_key='order')
    saved_orders = SavedOrder.all()
    # drink_components = DrinkComponent.find(in_stock=True, sort_key='order')
    # FIXME: ordering by name for now, since custom sorting is broken
    drinks = Drink.find(is_orderable=True, in_stock=True, sort_key='name')
    drink_components = DrinkComponent.find(in_stock=True, sort_key='name')

    in_stock_drink_components = set([d.doc_id for d in drink_components])
    def _filter_saved(o):
        o_coms = set(o.drink_components)
        have_coms = o_coms & in_stock_drink_components
        return have_coms == o_coms
    saved_orders = list(filter(_filter_saved, saved_orders))

    def get_components(ids):
        return DrinkComponent.find(*ids, sort_key='order')

    return render_template('index/index.jinja.html', drinks=drinks, saved_orders=saved_orders, drink_components=drink_components, get_components=get_components)


@app.route('/order', methods=['GET', 'POST'])
@require_login()
def order():
    drink = None
    drink_components = None
    drink_name = None
    order = None

    if request.args.get('d'):
        drink = Drink.get(int(request.args['d']))
        if not drink:
            abort(404, "That drink doesn't exist")
        if not drink.in_stock:
            abort(400, "That drink is out of stock")
    elif request.args.get('s'):
        saved_order = SavedOrder.get(int(request.args['s']))
        if not saved_order:
            abort(404, "No such saved order")
        drink_name = saved_order.drink_name
        drink_components = DrinkComponent.find(*saved_order.drink_components, sort_key='order')
    elif request.args.get('c'):
        drink_components = DrinkComponent.find(*map(int, request.args.getlist('c')), sort_key='order')

    if drink_components:
        if len(drink_components) < len(request.args.getlist('c')):
            abort(404, "Some of your choices do not exist")
        if any((not c.in_stock for c in drink_components)):
            abort(400, "Some of your choices are not in stock")

    name = None
    if not is_house_device():
        name = session.get('saved_name')
    form = OrderForm(drink=drink, drink_name=drink_name, name=name)
    if form.validate_on_submit():
        if not is_house_device():
            session['saved_name'] = form.name.data
        params = {
            'name': form.name.data,
        }
        if drink:
            params['drink'] = drink.doc_id
        else:
            params['drink_name'] = form.drink_name.data or None
            params['drink_components'] = [c.doc_id for c in drink_components]
        if not drink or drink.has_strengths:
            params['strength'] = form.strength.data
        if not drink and hasattr(form, 'save_for_later') and form.save_for_later.data:
            SavedOrder(drink_name=params['drink_name'], drink_components=params['drink_components']).save()
        order = Order(event=Event.get_current_id(), **params)
        order.save()
        try:
            queue_order_to_print(order=order, auto=True)
        except PrintError:
            # Should be because we're not auto cutting and there's already a job queued
            pass
        flash("Your order has been placed", 'success')

        return redirect(url_for('.index'))

    return render_template('index/order.jinja.html', form=form, drink=drink, drink_components=drink_components)


@app.route('/images/<name>', methods=['GET'])
@app.route('/images/<any(full):mode>/<name>', methods=['GET'])
def images(name, mode=None):
    outfile = None
    orig = os.path.abspath(os.path.join(current_app.config['DATA_DIRECTORY'], 'images', name))
    if mode == 'full':
        outfile = orig
    else:
        cached = os.path.abspath(os.path.join(current_app.config['DATA_DIRECTORY'], 'images', 'resized', name))
        if not os.path.exists(cached):
            img = Image.open(orig)
            img = img.convert('RGBA')
            w, h = img.size
            sz = max(w, h)
            out = Image.new('RGBA', (sz, sz), (0, 0, 0, 0))
            out.paste(img, (int((sz - w)), 0))
            out = out.resize((144, 144), PIL.Image.ANTIALIAS)

            with open(cached, 'wb') as fp:
                out.save(fp, 'PNG', quality=70)
        outfile = cached

    return send_file(outfile, mimetype='image/png')
