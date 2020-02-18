from flask import (
    Blueprint,
    render_template,
    request,
    abort,
    flash,
    redirect,
    url_for,
)

from app.database import Drink, DrinkComponent, Order
from app.forms.orders import OrderForm


app = Blueprint('index', __name__)


@app.route('/', methods=['GET'])
def index():
    drinks = Drink.find(is_orderable=True)
    return render_template('index/index.jinja.html', drinks=drinks)


@app.route('/order', methods=['GET', 'POST'])
def order():
    drink = None
    drink_components = None

    if request.args.get('drink'):
        drink = Drink.get(int(request.args['drink']))
        if not drink:
            abort(404, "That drink doesn't exist")

    # TODO: components
    form = OrderForm(drink=drink)
    if form.validate_on_submit():
        params = {
            'name': form.name.data,
        }
        if drink:
            params['drink'] = drink.doc_id
        else:
            params['drink_name'] = form.drink_name.data
        if not drink or drink.has_strengths:
            params['strength'] = form.strength.data
        # if not drink:
        #     save_for_later = BooleanField('Save this drink')
        Order(**params).save()
        flash("Your order has been placed", 'success')
        return redirect(url_for('.index'))

    return render_template('index/order.jinja.html', form=form, drink=drink, drink_components=drink_components)
