import os
import sys
import secrets
import re
import subprocess
import json


def die(msg, *args, **kwargs):
    sys.stderr.write("FATAL: " + msg.format(*args, **kwargs) + '\n')
    sys.exit(1)

def warn(msg, *args, **kwargs):
    sys.stderr.write("WARN: " + msg.format(*args, **kwargs) + '\n')


def ask(msg, choices=None, match=None, type_=None, **kwargs):
    prompt = msg
    if choices:
        prompt += ' [' + ', '.join(choices) + ']'
    if kwargs.get('dfl') is not None:
        prompt += ' ({})'.format(str(kwargs['dfl']))
    prompt += ': '

    if match and isinstance(match, str):
        match = re.compile(match)

    while True:
        res = input(prompt).strip()
        if res:
            if type_:
                try:
                    res = type_(res)
                except (TypeError, ValueError):
                    continue
            if choices and res not in choices:
                continue
            if match and not match.match(res):
                continue
            return res
        elif 'dfl' in kwargs:
            return kwargs['dfl']


def ask_bool(msg, dfl=None):
    yes_re = re.compile(r'^y(es)?|t(rue)?|1$', re.I)
    no_re = re.compile(r'^no?|f(alse)?|0$', re.I)
    ka = {}
    if dfl is not None:
        ka['dfl'] = 'true' if dfl else 'false'
    while True:
        res = ask(msg, **ka)
        if yes_re.match(res):
            return True
        elif no_re.match(res):
            return False
        elif dfl is not None:
            return dfl


def check_exists():
    files = [
        ('config', './config.json', False),
        ('inv', './inventory.yaml', False),
        ('venv', './venv', True),
    ]
    out = {}
    for name, path, isdir in files:
        if os.path.exists(path):
            if os.path.isdir(path) == isdir:
                out[name] = path
            else:
                die("{} exists, but is{} a directory", path, ' not' if isdir else '')
    return out


def ask_prod_url(context):
    if not (context['files'].get('config') and context['files'].get('inv')):
        context['prod_url'] = ask("Enter the production URL of your Drinkmenu instance")


def _ask_config(context):
    config = {}

    config['SECRET_KEY'] = ask("Enter a secret key (or nothing, to autogenerate)", dfl=None)
    if not config['SECRET_KEY']:
        config['SECRET_KEY'] = secrets.token_urlsafe(256)

    config['ESCPOS_PRINTER_MODE'] = ask("Enter the printer mode", choices=['bt', 'usb'])
    if config['ESCPOS_PRINTER_MODE'] == 'bt':
        addr = ask("Enter the printer's bluetooth MAC address", match=r'^([0-9a-fA-F]:){5}[0-9a-fA-F]$')
        svc = ask("Enter the service number", dfl=1, type_=int)
        config['ESCPOS_PRINTER_BT_ADDR'] = '{}/{}'.format(addr, svc)
    elif config['ESCPOS_PRINTER_MODE'] == 'usb':
        config['ESCPOS_PRINTER_ID'] = list(map(int, ask("Enter the printer's USB manufacturer & ID (decimal, '1234:5678')", match=r'^\d+:\d+').split(':')))

    config['ESCPOS_PRINTER_IMAGE_IMPL'] = ask("Printer image implementation (don't set unless you know what you're doing)", dfl='bitImageRaster')
    config['ESCPOS_PRINTER_HAS_CUTTER'] = ask_bool("Does the printer have a cutter?", dfl=False)

    config['API_URL'] = ask("Remote API URL", dfl=context['prod_url'].rstrip('/') + '/api')

    print("To modify the printout format, see ESCPOS_PRINTER_FMT in ./config.json")

    return config


def _write_config(context, config_params):
    with open(os.path.join(os.path.dirname(__file__), '..', 'config-example.json'), 'r') as fp:
        config = json.load(fp)

    for k in ('ESCPOS_PRINTER_MODE', 'ESCPOS_PRINTER_BT_ADDR', 'ESCPOS_PRINTER_ID'):
        config.pop(k, None)

    config.update(config_params)

    with open(os.path.join(os.path.dirname(__file__), 'config.json'), 'w') as fp:
        json.dump(config, fp, indent=4)


def check_config(context):
    if not context['files'].get('config'):
        _write_config(context, _ask_config(context))


def check_inv(context):
    if not context['files'].get('inv'):
        addr = ask("Enter your pi's IP address or hostname")
        port = ask("Enter your pi's SSH port", type_=int, dfl=22)
        user = ask("Enter your pi's username", dfl='pi')
        is_kiosk = ask_bool("Does this pi need a kiosk setup? (it may not, if you use a distro that provides this)")
        is_printer = ask_bool("Does this pi need the printing service?")

        inv = '''\
---
all:
    hosts:
        pi:
            ansible_host: "{}"
            ansible_port: {}
            ansible_user: "{}"
    children:
        kiosk: {}
        printer: {}
    vars:
        config_file: ./config.json
        kiosk_url: "{}"
'''.format(
    addr, port, user,
    '{hosts: {pi: {}}}' if is_kiosk else '',
    '{hosts: {pi: {}}}' if is_printer else '',
    context['prod_url']
)

        with open('./inventory.yaml', 'w') as fp:
            fp.write(inv)

        print("Note that you should run `ssh-copy-id {}@{}:{}` before continuing setup".format(user, addr, port))
        print("If you have more than one pi, you may modify ./inventory.yaml directly")


def _make_venv(context, will_retry=True):
    try:
        subprocess.check_call(['python3', '-m', 'virtualenv', '-p', 'python3', './venv'])
        return True
    except:
        if will_retry:
            return False
        raise


def check_venv(context):
    if not context['files'].get('venv'):
        if not _make_venv(context):
            subprocess.check_call(['python3', '-m', 'pip', 'install', 'virtualenv', '--user'])
            _make_venv(context, will_retry=False)
        subprocess.check_call(['./venv/bin/pip', 'install', '-r', './requirements.txt'])

        die("Not running in virtual environment - please rerun")

    if '/venv/' not in sys.executable:
        die("Not running in virtual environment - please rerun")


def run_ansible(context):
    subprocess.check_call([
        './venv/bin/ansible-playbook',
        '-i', './inventory.yaml',
        '--ask-become-pass',
        'playbook.yaml'
    ])



# main
context = {'files': check_exists()}
ask_prod_url(context)
check_config(context)
check_inv(context)
check_venv(context)
run_ansible(context)