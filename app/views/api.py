import logging
import functools
import time

from werkzeug.exceptions import HTTPException
from werkzeug.wrappers import Response

from flask import (
    Blueprint,
    abort,
    jsonify,
    request,
)

from app.lib.printer import get_print_job, clear_print_job, PrintError
from app.lib.auth import require_login
from app.database import Order, Drink, DrinkComponent


logger = logging.getLogger(__name__)
app = Blueprint('api', __name__)


def json_response(callback):
    @functools.wraps(callback)
    def json_response_wrapper(*args, **kwargs):
        try:
            res = callback(*args, **kwargs)
            if isinstance(res, Response):
                return res
            return jsonify({'result': res})
        except HTTPException as e:
            return jsonify({'error': {'code': e.code, 'message': e.description}}), e.code
        except Exception as e:
            logger.error("Error in API", exc_info=True)
            return jsonify({'error': {'code': 500, 'message': "An internal error has occurred."}}), 500
    return json_response_wrapper


@app.route('/', methods=['GET'])
@json_response
def index():
    abort(404)


@app.route('/print/job', methods=['GET', 'POST'])
@app.route('/print/job/<id>', methods=['GET', 'POST'])
@json_response
def print_job(id=None):
    if request.method == 'POST':
        if not id:
            abort(400, "An ID is required to clear")
        doc_id = clear_print_job(id)
        if not doc_id:
            abort(400, "The ID is invalid")

        order = Order.get(doc_id)
        if order:
            order.printed = True
            order.save()
        return "OK"

    elif id:
        abort(400, "An ID is only used to clear")

    else:
        to = int(request.args.get('timeout') or 10)
        t = time.time()
        while time.time() - t < to:
            res = get_print_job()
            if res:
                return res
            time.sleep(0.25)
        return None


@app.route('/admin/reorder/<type_>', methods=['POST'])
@require_login(admin=True)
@json_response
def admin_reorder_type(type_):
    data = {int(k): int(v) for k, v in request.json.items()}
    if type_ == 'drinks':
        Drink.set_order(data)
    elif type_ == 'drink-components':
        DrinkComponent.set_order(data)
    else:
        abort(400, "Invalid type: " + str(type_))
    return 'OK'
