# JVC Projector Remote

<details>
<summary>
⚠️ This project is looking for (co-)maintainers.
</summary>
Times change, I might end up with a different projector brand, JVC might change the command interface for a newer model that I don't have. Enough people use this library now that I think it's important to think about think about its future. I would be grateful to have people who are competent in python and have access to a JVC projector on board. If you're willing to help, submit a pull request implementing new features, fixing bugs or tidying up my terrible programming and documentation!

If you'd like to make a donation to sponsor work on this project, you can [donate on ko-fi](https://ko-fi.com/bezmi), or [github sponsors](https://github.com/sponsors/bezmi)

</details>

&NewLine;

This is a package to control JVC Projectors over IP.

## References

This library is used by following software:

- [JVC projector remote for Homeassistant](https://github.com/bezmi/homeassistant_jvc_projector_remote) (add-on for [Home Assistant](https://www.home-assistant.io/)).
- [homebridge-jvc-projector](https://www.npmjs.com/package/homebridge-jvc-projector)(plugin for [Homebridge](https://homebridge.io))

It can also be used standalone or in a Python script.

## Command Format

### Read State

To get a status a specific command is sent with the `JVCProjector.command(<command>)` method.

Examples:

- To read power state, send command `power` and receive `standby`, `lamp_on`, `cooling`, `reserved` or `emergency`
- To read signal state, send command `signal` and receive `no_signal` or `active_signal`

### Write State

To control the projector, a command together with a certain state is sent with the `JVCProjector.command(<command>-<state>)` method.

Examples:

- Power _ON_: `power-on`
- Change picture mode to _film_: `picture_mode-film`
- Switch lamp to _high_: `lamp-high`

## Supported Commands

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

```console
$ python3 -m pip install jvc_projector_remote
```

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

## Confirmed Models

- DLA-X5900
- NX5
- NZ8/RS3100
- DLA-RS440

Let me know if it works with your
projector and I will add it to the list above.

## Error _ConnectionRefusedError_

The main issue one might face is receiving ConnectionRefusedError when making a
request too soon after another. If this is the case, we will retry up to `max_retries`. It is important to set `delay_ms` to a reasonable value. For example, my X5900 will hang for 0.8-1 second after the power-off command is sent.

## Adding New Commands

If you are not familiar with Python at all, raise an issue with a request to add a new command. Otherwise, follow the [documentation](src/jvc_projector_remote/jvccommands.py#L19) for the `Command` base class and be sure to look at the [examples](src/jvc_projector_remote/jvccommands.py#L215) in the `Commands` class.
