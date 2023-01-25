# JVC Projector Remote
A python package to control JVC Projectors over IP.

&NewLine;

<details>
<summary>
⚠️ This project is looking for (co-)maintainers.
</summary>
&NewLine;
Times change, I might end up with a different projector brand, JVC might change the command interface for a newer model that I don't have. Enough people use this library now that I think it's important to think about think about its future. I would be grateful to have people who are competent in python and have access to a JVC projector on board. If you're willing to help, submit a pull request implementing new features, fixing bugs or tidying up my terrible programming and documentation!

If you'd like to make a donation to sponsor work on this project, you can [donate on ko-fi](https://ko-fi.com/bezmi), or [github sponsors](https://github.com/sponsors/bezmi)
</details>

## References
This library is used by following software:

- [JVC projector remote for Homeassistant](https://github.com/bezmi/homeassistant_jvc_projector_remote) (add-on for [Home Assistant](https://www.home-assistant.io/)).
- [homebridge-jvc-projector](https://www.npmjs.com/package/homebridge-jvc-projector)(plugin for [Homebridge](https://homebridge.io))

It can also be used standalone or in a Python script.

## Command format

### Read state

To read a property, use the `JVCProjector.command(<command>)` method.

Examples:
- Power state: send command `power` and the response will be `standby`, `lamp_on`, `cooling`, `reserved` or `emergency`
- Signal state: send command `signal` and the response will be `no_signal` or `active_signal`

### Write state
To control the projector, use `JVCProjector.command(<command>-<state>)`.

Examples:
- Power _ON_: `power-on`
- Change picture mode to _film_: `picture_mode-film`
- Switch lamp to _high_: `lamp-high`

## Supported commands

| Description      | Command      | State                                                                                                                                            |
| ---------------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| Power            | power        | **Read**: `standby`, `lamp_on`, `cooling`, `reserved`, `emergency`<br>**Write**: `on`, `off`                                                     |
| Lens Memory      | memory       | **Read/Write**: `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`, `10`                                                                                |
| Input            | input        | **Read/Write**: `hdmi1`, `hdmi2`                                                                                                                 |
| Picture Mode     | picture_mode | `film`, `cinema`, `natural`, `hdr10`, `thx`, `user1`, `user2`, `user3`, `user4`, `user5`, `user6`, `hlg`, `frame_adapt_hdr`, `hdr10p`, `pana_pq` |
| Low Latency Mode | low_latency  | **Read/Write**: `on`, `off`                                                                                                                      |
| Mask             | mask         | **Read/Write**: `off`, `custom1`, `custom2`, `custom3`                                                                                           |
| Lamp Setting     | lamp         | `high`, `low`, `mid`                                                                                                                             |
| Menu Buttons     | menu         | **Write**: `menu`, `down`, `left`, `right`, `up`, `ok`, `back`                                                                                   |
| Lens Aperture    | aperture     | **Read/Write**: `off`, `auto1`, `auto2`                                                                                                          |
| Anamorphic Mode  | anamorphic   | **Read/Write**: `off`, `a`, `b`, `c`, `d`                                                                                                        |
| Signal Status    | signal       | **Read**: `no_signal`, `active_signal`                                                                                                           |
| Get Mac Address  | macaddr      | **Read**: returns mac address string                                                                                                             |
| Model Info       | modelinfo    | **Read**: returns the model info string                                                                                                          |
| Test Connection  | null         | **Write**: no write payload, used for testing connection                                                                                         |

> **_NOTE:_** Not all commands or states are supported by all models. You can easily tell by testing them on your JVC projector.

## Installation
For the latest stable version,
```console
$ python3 -m pip install jvc_projector_remote
```
If you want to install the latest unstable commits from this repo,
```console
$ python3 -m pip install -e git+https://github.com/bezmi/jvc_projector.git#egg=jvc-projector-remote
```
### Building from source
If you've made changes and want to install them, ensure you have [hatch](https://github.com/pypa/hatch).
```console
$ python3 -m pip install hatch
```
Run the build command from the root directory of this repository.
```console
$ hatch build
```
Finally, you can install the package. Make sure the filename that you specify matches the one you want to install in the `dist/` directory.
```console
$ pip install dist/jvc_projector_remote-vX.X.X-py3-none-any.whl
```
The `--force-reinstall` flag will ensure that updated files are installed even if the version number of your build matches the pre-existing package.

## Usage
For usage with Home Assistant, [see here](https://github.com/bezmi/homeassistant_jvc_projector_remote).

Below is an example for using this module standalone (see [command format](#command-format) section for command strings):

```python
>>> from jvc_projector_remote import JVCProjector

 # replace with your projector's local IP
>>> host = "192.168.1.12"

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

## Confirmed models
This module is confirmed to work for the models listed below. It should also work with projectors in the same series as the ones listed.

- DLA-X5900
- NX5
- NZ8/RS3100
- DLA-RS440

If you've confirmed functionality with a model that is unlisted, raise an issue or submit a pull request to have it added.

## Adding new commands
Raise an issue or open a pull request. Add new commands to the [`Commands`](src/jvc_projector_remote/jvccommands.py#L231-L340) class. The format is documented in the [docstring](src/jvc_projector_remote/jvccommands.py#L20-L37) for the parent `Command` class.


