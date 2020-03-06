from flask import (
    Blueprint,
    render_template,
    request,
    abort,
    flash,
    redirect,
    url_for,
)

from app.database import Drink, DrinkComponent, Order, SavedOrder
from app.forms.orders import OrderForm


app = Blueprint('index', __name__)


@app.route('/', methods=['GET'])
def index():
    drinks = Drink.find(is_orderable=True, in_stock=True)
    saved_orders = SavedOrder.all()
    drink_components = DrinkComponent.find(in_stock=True)

    in_stock_drink_components = set([d.doc_id for d in drink_components])
    def _filter_saved(o):
        o_coms = set(o.drink_components)
        have_coms = o_coms & in_stock_drink_components
        return have_coms == o_coms
    saved_orders = list(filter(_filter_saved, saved_orders))

    def get_components(ids):
        return DrinkComponent.find(*ids)

    return render_template('index/index.jinja.html', drinks=drinks, saved_orders=saved_orders, drink_components=drink_components, get_components=get_components)


@app.route('/order', methods=['GET', 'POST'])
def order():
    drink = None
    drink_components = None
    drink_name = None

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
        drink_components = DrinkComponent.find(*saved_order.drink_components)
    elif request.args.get('c'):
        drink_components = DrinkComponent.find(*map(int, request.args.getlist('c')))

    if drink_components:
        if len(drink_components) < len(request.args.getlist('c')):
            abort(404, "Some of your choices do not exist")
        if any((not c.in_stock for c in drink_components)):
            abort(400, "Some of your choices are not in stock")

    form = OrderForm(drink=drink, drink_name=drink_name)
    if form.validate_on_submit():
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
        if not drink and form.save_for_later.data:
            SavedOrder(drink_name=params['drink_name'], drink_components=params['drink_components']).save()
        Order(**params).save()
        flash("Your order has been placed", 'success')
        return redirect(url_for('.index'))

    return render_template('index/order.jinja.html', form=form, drink=drink, drink_components=drink_components)
