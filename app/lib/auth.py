import functools

from flask import session, flash, redirect, url_for, g

from app.database import RuntimeConfig, Device


def login(type_, password):
    house_disabled = False
    config = RuntimeConfig.get_single()
    check_password = getattr(config, type_ + '_pass', None)
    if check_password:
        if password == check_password:
            session['login_' + type_] = True
        else:
            return False, None
    return True, house_disabled


def get_device(prop=None):
    dev = g.get('current_device')
    if dev is None:
        g.current_device = False
        devid = session.get('device_id')
        if devid:
            dev = Device.get_by_devid(devid)
            if dev:
                g.current_device = dev

    if prop:
        if g.current_device:
            return getattr(g.current_device, prop)
        return False
    return g.current_device


def is_house_device():
    return get_device('is_house_device')


def use_osk():
    return get_device('use_osk')


def require_login(admin=False):
    def require_login_impl(callback):
        @functools.wraps(callback)
        def require_login_wrapper(*args, **kwargs):
            config = RuntimeConfig.get_single()
            if admin and config.admin_pass and not session.get('login_admin'):
                flash("Admin login is required", 'danger')
                return redirect(url_for('auth.index', type_='admin'))
            if config.user_pass and not (session.get('login_admin') or session.get('login_user') or is_house_device()):
                flash("Login is required", 'danger')
                return redirect(url_for('auth.index', type_='user'))
            return callback(*args, **kwargs)
        return require_login_wrapper
    return require_login_impl
