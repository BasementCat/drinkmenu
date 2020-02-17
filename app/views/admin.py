from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    # current_app,
    abort,
    # request,
    # session,
)

from app.forms.drinks import DrinkForm
from app.database import Drink


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
