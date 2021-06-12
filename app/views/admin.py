import datetime
from collections import namedtuple

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    # current_app,
    abort,
    request,
    session,
)

from app.forms.drinks import DrinkForm, DrinkComponentForm
from app.forms.config import ConfigForm
from app.database import Drink, DrinkComponent, Order, SavedOrder, RuntimeConfig, OrderStat, Event, Device
from app.lib.printer import print_stuff, PrintError
from app.lib.auth import require_login


app = Blueprint('admin', __name__)


@app.route('/', methods=['GET'])
@require_login(admin=True)
def index():
    return render_template('admin/index.jinja.html')


@app.route('/drinks', methods=['GET'])
@require_login(admin=True)
def drinks():
    return render_template('admin/drinks.jinja.html', drinks=Drink.all(sort_key='order'))


@app.route('/drinks/new', methods=['GET', 'POST'])
@app.route('/drinks/<int:id>', methods=['GET', 'POST'])
@require_login(admin=True)
def edit_drink(id=None):
    drink = None
    is_new = True
    if id:
        is_new = False
        drink = Drink.get(id)
        if not drink:
            abort(404, "No such drink")

    form = DrinkForm(obj=drink)
    if form.validate_on_submit():
        if not drink:
            drink = Drink()
        form.populate_obj(drink)
        drink.save()
        flash("Your changes have been saved.", 'success')
        if is_new:
            return redirect(url_for('.edit_drink', id=drink.doc_id))

    return render_template('admin/edit_drink.jinja.html', form=form)


@app.route('/drinks/delete/<int:id>', methods=['POST'])
@require_login(admin=True)
def delete_drink(id):
    drink = Drink.get(id)
    if not drink:
        abort(404, "No such drink")
    drink.delete()
    flash("Deleted drink " + drink.name, 'info')
    return redirect(url_for('.drinks'))


@app.route('/drink-components', methods=['GET'])
@require_login(admin=True)
def drink_components():
    return render_template('admin/drink_components.jinja.html', drink_components=DrinkComponent.all(sort_key='order'), types=DrinkComponent.TYPES)


@app.route('/drink-components/new', methods=['GET', 'POST'])
@app.route('/drink-components/<int:id>', methods=['GET', 'POST'])
@require_login(admin=True)
def edit_drink_component(id=None):
    drink_component = None
    is_new = True
    if id:
        is_new = False
        drink_component = DrinkComponent.get(id)
        if not drink_component:
            abort(404, "No such drink component")

    form = DrinkComponentForm(obj=drink_component)
    if form.validate_on_submit():
        if not drink_component:
            drink_component = DrinkComponent()
        form.populate_obj(drink_component)
        drink_component.save()
        flash("Your changes have been saved.", 'success')
        if is_new:
            return redirect(url_for('.edit_drink_component', id=drink_component.doc_id))

    return render_template('admin/edit_drink_component.jinja.html', form=form)


@app.route('/drink-components/delete/<int:id>', methods=['POST'])
@require_login(admin=True)
def delete_drink_component(id):
    drink_component = DrinkComponent.get(id)
    if not drink_component:
        abort(404, "No such drink component")
    drink_component.delete()
    flash("Deleted drink component " + drink_component.name, 'info')
    return redirect(url_for('.drink-components'))


@app.route('/orders', methods=['GET'])
@require_login(admin=True)
def orders():
    orders = Order.find(printed=False)
    printed_orders = Order.find(printed=True)
    saved_orders = SavedOrder.all()

    def get_drink(id):
        return Drink.get(id)

    def get_components(ids):
        return DrinkComponent.find(*ids)

    return render_template(
        'admin/orders.jinja.html',
        printed_orders=printed_orders,
        orders=orders,
        saved_orders=saved_orders,
        get_drink=get_drink,
        get_components=get_components,
        total_orders_ev=len(list(OrderStat.find(event=Event.get_current_id()))),
        total_orders_all=len(list(OrderStat.all())),
    )


@app.route('/orders/print/<int:id>', methods=['POST'])
@require_login(admin=True)
def print_order(id):
    order = Order.get(id)
    if not order:
        flash("No such order", 'danger')
    else:
        drink = None
        if order.drink:
            drink = Drink.get(order.drink)

        drink_components = None
        if order.drink_components:
            drink_components = DrinkComponent.find(*order.drink_components)

        try:
            strength = f' [{order.strength}]' if order.strength else ''
            print_stuff(
                order.doc_id,
                name=order.name,
                drink_name=(order.drink_name + strength) if order.drink_name else None,
                drink=(drink.name + strength) if drink else None,
                drink_components=', '.join((c.name for c in drink_components)) if drink_components else None
            )
        except PrintError as e:
            flash(str(e), 'danger')
        else:
            flash(f"Queued order {order.drink_name} for {order.name} for printing", 'success')

    return redirect(url_for('.orders'))


@app.route('/orders/complete/<int:id>', methods=['POST'])
@require_login(admin=True)
def complete_order(id):
    order = Order.get(id)
    if not order:
        flash("No such order", 'danger')
    else:
        if order.drink:
            drink = Drink.get(order.drink)
            if drink and drink.inventory_level is not None:
                drink.inventory_level = max(0, drink.inventory_level - 1)
                if drink.inventory_level == 0:
                    drink.in_stock = False
                drink.save()

        OrderStat.from_order(order)
        order.delete()
        flash(f"Completed order {order.drink_name} for {order.name}", 'success')

    return redirect(url_for('.orders'))


@app.route('/orders/delete/<int:id>', methods=['POST'])
@require_login(admin=True)
def delete_order(id):
    order = Order.get(id)
    if not order:
        flash("No such order", 'danger')
    else:
        order.delete()
        flash(f"Deleted order {order.drink_name} for {order.name}", 'success')

    return redirect(url_for('.orders'))


@app.route('/orders/delete-saved/<int:id>', methods=['POST'])
@require_login(admin=True)
def delete_saved_order(id):
    order = SavedOrder.get(id)
    if not order:
        flash("No such saved order", 'danger')
    else:
        order.delete()
        flash(f"Deleted saved order {order.drink_name}", 'success')

    return redirect(url_for('.orders'))


@app.route('/config', methods=['GET', 'POST'])
@require_login(admin=True)
def config():
    c = RuntimeConfig.get_single()
    form = ConfigForm(obj=c, house_device=session.get('house_device'))
    if form.validate_on_submit():
        logo = form.save_image(c.logo)
        if logo:
            c.logo = logo
        for k in RuntimeConfig.get_fields():
            if k == 'logo':
                continue
            f = getattr(form, k, None)
            if f:
                setattr(c, k, f.data or None)
        c.save()

        if form.new_event.data:
            for e in Event.find(is_current=True):
                e.is_current = False
                e.save()
            e = Event(name=form.new_event.data, date=str(datetime.datetime.utcnow()), is_current=True)
            e.save()
            flash(f'Created new event "{e.name}"', 'info')
            # The form must be recreated so that we can reload the current event, and clear out the new event field
            form = ConfigForm(obj=c, house_device=session.get('house_device'))
            form.new_event.data = ''

        flash("Configuration changes have been saved.", 'success')

    return render_template('admin/config.jinja.html', form=form)


@app.route('/stats', methods=['GET'])
@require_login(admin=True)
def stats():
    fake_event = namedtuple('FakeEvent', ('doc_id', 'name', 'is_current'))
    events = list(reversed(list(Event.all(sort_key='date'))))
    valid_events = [e.doc_id for e in events]
    events = [
        fake_event(-1, "UNKNOWN", False),
        fake_event(0, "NONE", False),
    ] + events
    try:
        selected_event = int(request.args['event'])
    except:
        try:
            selected_event = Event.get_current().doc_id
        except:
            selected_event = 0

    est_oz = {
        'mocktail': 0,
        'light': 1,
        'normal': 2,
        'strong': 3,
    }
    stats_ev = {'drinks': {}, 'strengths': {}, 'count': 0, 'total_oz': 0}
    stats_all = {'drinks': {}, 'strengths': {}, 'count': 0, 'total_oz': 0}

    def add_stat(dest, stat):
        if stat.drink:
            drink = Drink.get(stat.drink)
            if drink:
                dest['drinks'].setdefault(drink.name, 0)
                dest['drinks'][drink.name] += 1

        dest['strengths'].setdefault(stat.strength, 0)
        dest['strengths'][stat.strength] += 1

        dest['count'] += 1
        dest['total_oz'] += est_oz.get(stat.strength, 2)

    for stat in OrderStat.all():
        if (selected_event == 0 and not stat.event) or stat.event == selected_event or (selected_event == -1 and stat.event not in valid_events):
            add_stat(stats_ev, stat)
        add_stat(stats_all, stat)

    for dest in (stats_ev, stats_all):
        dest['drinks'] = sorted(dest['drinks'].items(), key=lambda v: v[1], reverse=True)
        dest['strengths'] = sorted(dest['strengths'].items(), key=lambda v: v[1], reverse=True)


    return render_template(
        'admin/stats.jinja.html',
        events=events,
        selected_event=selected_event,
        stats_ev=stats_ev,
        stats_all=stats_all,
        totals=[('Total Count', 'count'), ('Total oz of Liquor', 'total_oz')]
    )



@app.route('/devices', methods=['GET', 'POST'])
@require_login(admin=True)
def devices():
    if request.method == 'POST':
        updated = 0
        for dev in Device.all():
            if dev.device_id in request.form.getlist('delete'):
                dev.delete()
                flash(f"Deleted device {dev.device_id}", 'info')
            else:
                dev.is_house_device = dev.device_id in request.form.getlist('is_house_device')
                dev.use_osk = dev.device_id in request.form.getlist('use_osk')
                dev.save()
                updated += 1
        if updated:
            flash(f"Updated {updated} devices", 'success')
    return render_template('admin/devices.jinja.html', devices=Device.all())