import functools

from flask import session, flash, redirect, url_for

from app.database import RuntimeConfig


def login(type_, password):
    c = RuntimeConfig.get_single()
    p = getattr(c, type_ + '_pass', None)
    if p:
        if password == p:
            session['login_' + type_] = True
        else:
            return False
    return True


def require_login(admin=False):
    def require_login_impl(callback):
        @functools.wraps(callback)
        def require_login_wrapper(*args, **kwargs):
            if admin and not session.get('login_admin'):
                flash("Admin login is required", 'danger')
                return redirect(url_for('auth.index', type_='admin'))
            if not (session.get('login_admin') or session.get('login_user')):
                flash("Login is required", 'danger')
                return redirect(url_for('auth.index', type_='user'))
            return callback(*args, **kwargs)
        return require_login_wrapper
    return require_login_impl
