# JVC Projector Remote

This is a package to control JVC Projectors over IP. Created to be used with my [Homeassistant](https://www.home-assistant.io/) custom component: [bezmi/homeassistant_jvc_projector_remote](https://github.com/bezmi/homeassistant_jvc_projector_remote). It can also be used standalone.

The following command groups are supported, with the corresponding reference (`?`, read) and operation (`!`, write) values:
* Power (`power`)
  * Read: `standby`, `lamp_on`, `cooling`, `reserved`, `emergency`
  * Write: `on`, `off`
* Lens Memory (`memory`)
  * Read/Write: `1`, `2`, `3`, `4`, `5`
* Input (`input`, HDMI only)
  * Read/Write: `hdmi1`, `hdmi2`
* Picture Mode (`picture_mode`)
  * Read/Write: `film`, `cinema`, `natural`, `hdr10`, `thx`, `user1`, `user2`, `user3`, `user4`, `user5`, `user6`, `hlg`
* Low Latency Mode (`low_latency`)
  * Read/Write: `on`, `off`
* Mask (`mask`)
  * Read/Write: `off`, `custom1`, `custom2`, `custom3`
* Lamp Setting (`lamp`)
  * Read/Write: `high`, `low`
* Menu Buttons (`menu`)
  * Write: `menu`, `down`, `left`, `right`, `up`, `ok`, `back`
* Lens Aperture (`aperture`)
  * Read/Write: `off`, `auto1`, `auto2`
* Anamorphic Mode (`anamorphic`)
  * Read/Write: `off`, `a`, `b`, `c`
* Signal Status (`signal`)
  * Read: `no_signal`, `active_signal`
* Get Mac Address (`macaddr`)
  * Read: returns mac address string
* Model Info (`modelinfo`)
  * Real: Returns the model info string
* Null Command
  * Write: no write payload, used for testing connection

## Command Format
Commands are send to the projector with the `JVCProjector.command(command_string: str)` method. For write (operation) commands, the command string is the name of the command group, followed by a hyphen (`-`) and then the write value. For example:
* Power on command_string: `power-on`
* Change picture mode to `film`: `picture_mode-film`
* Switch lamp to high: `lamp-high`

For read (reference) commands, `command_string` is just the name of the group. For example:
* To read power state, send `power`. We will receive `standby`, `lamp_on`, `cooling`, `reserved` or `emergency`
* Read signal status, send `signal`, response will be `no_signal` or `active_signal`


Raise an issue if you would like any extra commands implemented. Alternatively pull requests are more than welcome and adding new commands is trivial. [See Below.](#adding-new-commands)

# Installation
## PyPi
Install [this package](https://pypi.org/project/jvc-projector-remote/) from PyPi
with:
~~~
pip install jvc_projector_remote
~~~
## From this repo
Install from this repo with:
~~~
pip install -e git+https://github.com/bezmi/jvc_projector.git#egg=jvc-projector-remote
~~~
For testing development branches:
~~~
pip install -e git+https://github.com/bezmi/jvc_projector.git@branch_name#egg=jvc-projector-remote
~~~
# Usage
For usage with homeassistant, [see here](https://github.com/bezmi/homeassistant_jvc_projector_remote).

Here is an example for using this module standalone (see [command format](#command-format) section for command strings):
``` python
>>> from jvc_projector import JVCProjector

 # replace with your projector's local IP
>>> host = "192.168.1.12"

 # replace with your projector's network password
 # only required for NZ series (check your network settings)
>>> password = "MYPASSWORD"

# initialise (for models older than the NZ series)
>>> projector = JVCProjector(host, port=20554, delay_ms=600, connect_timeout=10, max_retries=10)

# initialise (alternate, with network password)
>>> projector = JVCProjector(host, password="MYPASSWORD", port=20554, delay_ms=600, connect_timeout=10, max_retries=10)

# power on, power off
>>> projector.power_on()
# check status once it's on
>>> projector.is_on()
True

>>> projector.power_off()
# check if it's off
>>> projector.is_on()
False

# Send arbitrary command
# see the command format section above
>>> projector.command("input-hdmi2")
```

# Testing
I wrote this to interface my projector with homeassistant. It
has been tested on a DLA-X5900, but should work on most of the projectors
that use a similar IP control scheme. Let me know if it works with your
projector and I will add it to the list below.

## Confirmed Models
* DLA-X5900
* NX5
* NZ8/RS3100

# Bugs
The main issue one might face is receiving ConnectionRefusedError when making a
request too soon after another. If this is the case, we will retry up to `max_retries`. It is important to set `delay_ms` to a reasonable value. For example, my X5900 will hang for 0.8-1 second after the power-off command is sent. I have found that the defaults work in most situations.

# Adding New Commands
If you are not familiar with python at all, raise an issue with a request to add a new command. Otherwise, follow the [documentation](https://github.com/bezmi/jvc_projector/blob/improved_commands/src/jvc_projector/jvccommands.py#L19) for the `Command` base class and be sure to look at the [examples](https://github.com/bezmi/jvc_projector/blob/improved_commands/src/jvc_projector/jvccommands.py#L215) in the `Commands` class.



