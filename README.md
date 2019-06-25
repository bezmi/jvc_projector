# JVC Projector Remote

This is a simple package to control JVC Projectors over IP.

Currently supports:
* Power on/off
* Lens Memory
* Input (HDMI only)
* Power Status (Standby, Cooling, Emergency, Lamp On, Reserved)

Raise an issue if you would like any extra commands implemented

# Testing
I wrote this to interface my projector with homeassistant. The code to
send/receive commands is rough and the error checking could be more robust. It
has been tested on a DLA-X5900, but should work on most of the projectors
that use a similar IP control scheme. Let me know if it works with your
projector and I will add it to the list below.

## Confirmed Models
* DLA-X5900

# Bugs
The main issue one might face is receiving ConnectionRefusedError when making a
request too soon after another. On my DLA-X5900, it takes about 600-700 ms
between commands.

# Improvements
* Currently I group all power states into either "on" or "off". I might separate
  these in future.

* Additional commands (Raise an issue and I'll update the package)


