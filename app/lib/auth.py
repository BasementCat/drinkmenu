import functools

from flask import session, flash, redirect, url_for

from app.database import RuntimeConfig


def login(type_, password):
    house_disabled = False
    config = RuntimeConfig.get_single()
    check_password = getattr(config, type_ + '_pass', None)
    if check_password:
        if password == check_password:
            session['login_' + type_] = True
            if type_ == 'admin' and is_house_device():
                house_disabled = True
                set_house_device(False)
        else:
            return False, None
    return True, house_disabled


def is_house_device():
    return True if session.get('house_device') else False


def set_house_device(v):
    session['house_device'] = True if v else False
    if session['house_device']:
        session['login_user'] = True
        session['login_admin'] = False
        return True
    return False


def require_login(admin=False):
    def require_login_impl(callback):
        @functools.wraps(callback)
        def require_login_wrapper(*args, **kwargs):
            config = RuntimeConfig.get_single()
            if admin and config.admin_pass and not session.get('login_admin'):
                flash("Admin login is required", 'danger')
                return redirect(url_for('auth.index', type_='admin'))
            if config.user_pass and not (session.get('login_admin') or session.get('login_user')):
                flash("Login is required", 'danger')
                return redirect(url_for('auth.index', type_='user'))
            return callback(*args, **kwargs)
        return require_login_wrapper
    return require_login_impl
