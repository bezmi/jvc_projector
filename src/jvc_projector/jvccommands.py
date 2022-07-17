"""Commands for the jvc_projector library."""

import socket
import logging
from dataclasses import dataclass, field

_LOGGER = logging.getLogger(__name__)

# Headers
OPR = b"!\x89\x01"  # operation (set)
REF = b"?\x89\x01"  # reference (get)
RES = b"@\x89\x01"  # response
ACKH = b"\x06\x89\x01"  # projector ack
COM_ACK_LENGTH = 6  # length of ACKs sent by the projector


# use a dataclass so that we have a nice repr
@dataclass(init=False)
class Command:
    """Base class for defining a set of read/write commands.
    Args:
        cmd (bytes): the base command bytes, for examplee b"PW" for power, b"PMPM" for picture mode.
        *args (dict[str, bytes]): dictionaries of str:bytes pairs defining the read and write values.
            If two dicts are provided as args, then the first is used for the write commands and
            the second is used for read values. If only a single dict is provided,
            we use it for both the write commands and the read values.
        write_only(bool, optional): If true, this command group does not read from the projector
            Defaults to False.
        read_only(bool, optional): If True, this command group cannot write to the projector
            Defaults to False.
        verify_write (bool, optional): Whether we should wait for an ACK once we send a write command.
            Defaults to True.

    Examples:
        See jvccommands.Commands, jvcprojector.JVCProjector
    """

    cmd: bytes
    name: str
    readwritevals: tuple[dict[str, bytes]] = field(repr=False)
    write_only: bool
    read_only: bool
    verify_write: bool

    write_vals: dict[str, bytes]
    read_vals: dict[str, bytes]

    def __init__(
        self,
        cmd: bytes,
        *readwritevals: dict[str, bytes],
        write_only: bool = False,
        read_only: bool = False,
        verify_write: bool = True,
    ):
        self.cmd = cmd
        self.verify_write = verify_write

        self.ack = ACKH + self.cmd[0:2] + b"\n"

        try:
            assert len(readwritevals) <= 2
        except AssertionError:
            raise AssertionError(
                "(set_vals, get_vals) AND setget_vals cannot be defined at the same time."
            )

        self.write_only = write_only
        self.read_only = read_only
        if len(readwritevals) == 1:
            if write_only:
                self.write_vals = readwritevals[0]
                self.read_vals = {}
            elif read_only:
                self.write_vals = {}
                self.read_vals = readwritevals[0]
            else:
                self.write_vals = readwritevals[0]
                self.read_vals = readwritevals[0]

        elif len(readwritevals) == 2:
            self.write_vals = readwritevals[0]
            self.read_vals = readwritevals[1]
        else:
            self.write_vals = {}
            self.read_vals = {}

        self.write_valsinv = {
            self.write_vals[key]: key for key in self.write_vals.keys()
        }
        self.read_valsinv = {self.read_vals[key]: key for key in self.read_vals.keys()}

        for key in self.write_vals.keys():
            assert "-" not in key, "command keys cannot contain hyphens ('-') !"

        for key in self.read_vals.keys():
            assert "-" not in key, "command keys cannot contain hyphens ('-') !"

    def __set_name__(self, owner, name: str):
        self.name = name

    def __send(self, sock: socket.socket, command: bytes) -> None:
        try:
            sock.sendall(command)
        except OSError as e:
            sock.close()
            raise JVCCommunicationError(
                f"Socket exception of `{self.name}` command when sending bytes: `{command}`."
            ) from e

    def __verify_ack(self, sock: socket.socket, command: bytes) -> None:
        try:
            ACK = sock.recv(COM_ACK_LENGTH)

            # check if the ACK is valid (compare to user provided ack if available)
            if not ACK.startswith(ACKH):
                sock.close()
                raise JVCCommunicationError(
                    f"Malformed ACK response from the projector when sending command: `{self.name}` with bytes: `{command}`. "
                    f"Received ACK: `{ACK}` does not have the correct header"
                )
            elif not ACK == self.ack:
                sock.close()
                raise JVCCommunicationError(
                    f"Malformed ACK response from the projector when sending command: `{self.name}` with bytes: `{command}`. "
                    f"Expected `{self.ack}`, received `{ACK}`"
                )

        except socket.timeout as e:
            sock.close()
            raise JVCCommunicationError(
                f"Timeout when waiting for the specified ACK: `{self.ack}` for command: `{self.name}` with bytes: `{command}`"
            ) from e

        except OSError as e:
            sock.close()
            raise JVCCommunicationError(
                f"Socket exception when waiting for the specified ACK: `{self.ack}` for command: `{self.name}` with bytes: `{command}`"
            ) from e

    def write(self, sock: socket.socket, value: str = "") -> None:
        if self.read_only:
            sock.close()
            raise JVCCommandNotFoundError(
                f"The command group `{self.name}` does not implement any writable properties"
            )
        try:
            command = OPR + self.cmd + self.write_vals[value] + b"\n"
        except KeyError as e:
            if not value and not self.write_vals:
                command = OPR + self.cmd + b"\n"
            elif not value and self.write_only:
                sock.close()
                raise JVCCommandNotFoundError(
                    f"The write_only command group: `{self.name}` requires a property key to be defined to do a write operation"
                ) from e
            else:
                sock.close()
                raise JVCCommandNotFoundError(
                    f"The command: `{self.name}` does not have write operation: `{value}`"
                ) from e

        if not self.verify_write:
            _LOGGER.debug(
                f"ACK verification disabled for the command: `{jfrmt.highlight(self.name)} `. Error handling will be less robust"
            )

        self.__send(sock, command)

        # no need to wait for ACK or message as this is not a reference command without ACK specified
        if not self.verify_write:
            sock.close()
            return

        self.__verify_ack(sock, command)

        sock.close()

    def read(self, sock: socket.socket) -> str:
        if self.write_only:
            sock.close()
            raise JVCCommandNotFoundError(
                f"The command group: `{self.name}` does not implement any readable properties"
            )

        command = REF + self.cmd + b"\n"

        self.__send(sock, command)

        self.__verify_ack(sock, command)

        try:
            resp = sock.recv(1024)
        except socket.timeout as e:
            sock.close()
            raise JVCCommunicationError(
                f"Timeout when waiting for response for read command: `{self.name}`"
            ) from e
        except OSError as e:
            sock.close()
            raise JVCCommunicationError(
                f"Socket exception when waiting for response for read command: `{self.name}`"
            ) from e

        sock.close()
        if not resp.startswith(RES + self.cmd[0:2]):
            raise JVCCommunicationError(
                f"Malformed response header for read command: `{self.name}`"
            )

        resp = resp[len(RES) + 2 : -1]

        if not self.read_vals:
            return resp.decode("ascii")

        return self.read_valsinv[resp]


class Commands:
    """A container for Commands"""

    # power commands
    power = Command(
        b"PW",
        {"on": b"1", "off": b"0"},
        {
            "standby": b"0",
            "lamp_on": b"1",
            "cooling": b"2",
            "reserved": b"3",
            "emergency": b"4",
        },
    )

    # lens memory commands
    memory = Command(
        b"INML",
        {"1": b"0", "2": b"1", "3": b"2", "4": b"3", "5": b"4"},
        write_only=True,
    )

    # input commands, input is technically a keyword, but should be okay...
    input = Command(b"IP", {"hdmi1": b"6", "hdmi2": b"7"})

    # picture mode commands
    picture_mode = Command(
        b"PMPM",
        {
            "film": b"00",
            "cinema": b"01",
            "natural": b"03",
            "hdr10": b"04",
            "thx": b"06",
            "user1": b"0C",
            "user2": b"0D",
            "user3": b"0E",
            "user4": b"0F",
            "user5": b"10",
            "user6": b"11",
            "hlg": b"14",
        },
    )

    # low latency enable/disable
    low_latency = Command(b"PMLL", {"on": b"1", "off": b"0"})

    # mask commands
    mask = Command(
        b"ISMA",
        {"off": b"2", "custom1": b"0", "custom2": b"1", "custom3": b"3"},
    )

    # lamp commands
    lamp = Command(
        b"PMLP",
        {"high": b"1", "low": b"0"},
    )

    # menu controls
    menu = Command(
        b"RC73",
        {
            "menu": b"2E",
            "down": b"02",
            "left": b"36",
            "right": b"34",
            "up": b"01",
            "ok": b"2F",
            "back": b"03",
        },
        write_only=True,
    )

    # Intelligent Lens Aperture commands
    aperture = Command(
        b"PMDI",
        {"off": b"0", "auto1": b"1", "auto2": b"2"},
    )

    # Anamorphic commands
    anamorphic = Command(
        b"INVS",
        {"off": b"0", "a": b"1", "b": b"2", "c": b"3"},
    )

    # active signal
    signal = Command(
        b"SC",
        {"no_signal": b"0", "active_signal": b"1"},
        read_only=True,
    )

    # MAC address, model, null command
    macaddr = Command(
        b"LSMA",
        read_only=True,
    )

    modelinfo = Command(
        b"MD",
        read_only=True,
    )
    nullcmd = Command(
        b"\x00\x00",
        write_only=True,
    )


class JVCConfigError(Exception):
    """Exception when the user supplied config is wrong"""

    pass


class JVCCannotConnectError(Exception):
    """Exception when we can't connect to the projector"""

    pass


class JVCHandshakeError(Exception):
    """Exception when there was a problem with the 3 step handshake"""

    pass


class JVCCommunicationError(Exception):
    """Exception when there was a communication issue"""

    pass


class JVCCommandNotFoundError(Exception):
    """Exception when the requested command doesn't exist"""

    pass


class JVCPoweredOffError(Exception):
    """Exception when projector is powered off and can't accept some commands."""

    pass


class jfrmt:
    @staticmethod
    def highlight(value: str) -> str:
        return "{:s}".format("\u035F".join(value))
