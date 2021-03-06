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
from app.database import Drink, DrinkComponent, Order, SavedOrder, RuntimeConfig, OrderStat
from app.lib.printer import print_stuff, PrintError
from app.lib.auth import require_login, set_house_device


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
        total_orders=len(list(OrderStat.all())),
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
        for k in RuntimeConfig.get_fields():
            f = getattr(form, k, None)
            if f:
                setattr(c, k, f.data or None)
        c.save()

        flash("Configuration changes have been saved.", 'success')
        if set_house_device(form.house_device.data):
            flash("This device is configured as a house device - admin is logged out, names will not be saved", 'info')
            return redirect(url_for('index.index'))

    return render_template('admin/config.jinja.html', form=form)



@app.route('/stats', methods=['GET'])
@require_login(admin=True)
def stats():
    est_oz = {
        'mocktail': 0,
        'light': 1,
        'normal': 2,
        'strong': 3,
    }
    stats = {'drinks': {}, 'strengths': {}, 'count': 0, 'total_oz': 0}

    for stat in OrderStat.all():
        if stat.drink:
            drink = Drink.get(stat.drink)
            if drink:
                stats['drinks'].setdefault(drink.name, 0)
                stats['drinks'][drink.name] += 1

        stats['strengths'].setdefault(stat.strength, 0)
        stats['strengths'][stat.strength] += 1

        stats['count'] += 1
        stats['total_oz'] += est_oz.get(stat.strength, 0)

    stats['drinks'] = sorted(stats['drinks'].items(), key=lambda v: v[1], reverse=True)
    stats['strengths'] = sorted(stats['strengths'].items(), key=lambda v: v[1], reverse=True)

    return render_template('admin/stats.jinja.html', stats=stats, totals=[('Total Count', 'count'), ('Total oz of Liquor', 'total_oz')])
