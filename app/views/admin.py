from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    # current_app,
    abort,
    request,
    # session,
)

from app.forms.drinks import DrinkForm, DrinkComponentForm
from app.database import Drink, DrinkComponent, Order, SavedOrder
from app.lib.printer import print_stuff


app = Blueprint('admin', __name__)


@app.route('/', methods=['GET'])
def index():
    return render_template('admin/index.jinja.html')


@app.route('/drinks', methods=['GET'])
def drinks():
    return render_template('admin/drinks.jinja.html', drinks=Drink.all())


@app.route('/drinks/new', methods=['GET', 'POST'])
@app.route('/drinks/<int:id>', methods=['GET', 'POST'])
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
def delete_drink(id):
    drink = Drink.get(id)
    if not drink:
        abort(404, "No such drink")
    drink.delete()
    flash("Deleted drink " + drink.name, 'info')
    return redirect(url_for('.drinks'))


@app.route('/drink-components', methods=['GET'])
def drink_components():
    return render_template('admin/drink_components.jinja.html', drink_components=DrinkComponent.all(), types=DrinkComponent.TYPES)


@app.route('/drink-components/new', methods=['GET', 'POST'])
@app.route('/drink-components/<int:id>', methods=['GET', 'POST'])
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
def delete_drink_component(id):
    drink_component = DrinkComponent.get(id)
    if not drink_component:
        abort(404, "No such drink component")
    drink_component.delete()
    flash("Deleted drink component " + drink_component.name, 'info')
    return redirect(url_for('.drink-components'))


@app.route('/orders', methods=['GET'])
def orders():
    orders = Order.find(printed=False)
    printed_orders = Order.find(printed=True)
    saved_orders = SavedOrder.all()

    def get_drink(id):
        return Drink.get(id)

    def get_components(ids):
        return DrinkComponent.find(*ids)

    return render_template('admin/orders.jinja.html', printed_orders=printed_orders, orders=orders, saved_orders=saved_orders, get_drink=get_drink, get_components=get_components)


@app.route('/orders/print/<int:id>', methods=['POST'])
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

        strength = f' [{order.strength}]' if order.strength else ''
        res = print_stuff(
            name=order.name,
            drink_name=(order.drink_name + strength) if order.drink_name else None,
            drink=(drink.name + strength) if drink else None,
            drink_components=', '.join((c.name for c in drink_components)) if drink_components else None
        )

        if res:
            flash(f"Printed order {order.drink_name} for {order.name}", 'success')
            order.printed = True
            order.save()
        else:
            flash(f"Failed to print order", 'danger')

    return redirect(url_for('.orders'))


@app.route('/orders/complete/<int:id>', methods=['POST'])
def complete_order(id):
    order = Order.get(id)
    if not order:
        flash("No such order", 'danger')
    else:
        order.delete()
        flash(f"Completed order {order.drink_name} for {order.name}", 'success')

    return redirect(url_for('.orders'))


@app.route('/orders/delete-saved/<int:id>', methods=['POST'])
def delete_saved_order(id):
    order = SavedOrder.get(id)
    if not order:
        flash("No such saved order", 'danger')
    else:
        order.delete()
        flash(f"Deleted saved order {order.drink_name}", 'success')

    return redirect(url_for('.orders'))
