# Set up a Raspberry Pi as a drinkmenu kiosk

The drinkmenu kiosk does 2 things:

  1. Starts a kiosk mode web browser pointed at a hosted Drinkmenu instance
  2. Runs a printing service that will print out orders to a receipt printer

This Ansible playbook will set up a Raspberry Pi for kiosk mode.

## Setup

### Install an OS

You'll need to install an image on the raspberry pi, use either Raspberry Pi OS, or a purpose built kiosk distroy like FullPageOS - https://github.com/guysoft/FullPageOS

#### Raspberry Pi OS

This will require a full setup.  After flashing the OS image to the SD card, create 2 files on the boot volume:

  * Create an empty file called "ssh" to enable SSH on boot
  * Create "wpa_supplicant.conf" to configure wifi, if desired (see https://www.raspberrypi-spy.co.uk/2017/04/manually-setting-up-pi-wifi-using-wpa_supplicant-conf/ for more details)

Note that the kiosk setup is untested!

#### FullPageOS

After flashing, note that the ssh and fullpageos-wpa-supplicant.conf files already exist.  Edit fullpageos-wpa-supplicant.conf and configure with your wifi credentials (if not using ethernet), and edit fullpageos.txt to the URL of your Drinkmenu installation.

You may want to set the initial URL to https://domain.name/path/init-device/<device-id> where "<device-id>" is a unique identifier for the device - this allows you to configure some parameters from the admin pages.

### Configure Ansible

In the ansible directory, run `./run.sh`.  If you have not previously set it up, it'll do the following:

  * Prompt you for the URL of your Drinkmenu installation
  * Ask you for some configuration options (note: bluetooth setup is not currently supported by the ansible playbook)
  * Ask you for your Raspberry Pi hostname/IP
  * Ask you if this pi will be doing kiosk or printing - if using FullPageOS, you do not need the kiosk setup.  Otherwise, the kiosk setup may work but is untested
  * Create a virtual environment to run in, and ask you to rerun

Rerun `./run.sh` and Ansible will set up the pi