from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
)

from app.forms.auth import AuthForm
from app.lib.auth import login


app = Blueprint('auth', __name__)


@app.route('/', methods=['GET', 'POST'])
@app.route('/<any(user,admin):type_>', methods=['GET', 'POST'])
def index(type_='user'):
    form = AuthForm()
    if form.validate_on_submit():
        if login(type_, form.password.data):
            if type_ == 'admin':
                return redirect(url_for('admin.index'))
            return redirect(url_for('index.index'))
        flash("Invalid password", 'danger')

    return render_template('auth/index.jinja.html', form=form)
