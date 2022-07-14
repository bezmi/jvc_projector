from enum import Enum
import socket
from time import sleep
import datetime
import logging

from .jvccommands import *

_LOGGER = logging.getLogger(__name__)
# TODO: add some debug statements


class JVCProjector:
    """JVC Projector Control"""

    def __init__(
        self,
        host: str,
        password: Optional[str] = None,
        port: int = 20554,
        delay_ms: int = 700,
        connect_timeout: int = 10,
    ):
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self.delay = datetime.timedelta(microseconds=(delay_ms * 1000))
        self.last_command_time = datetime.datetime.now() - datetime.timedelta(
            seconds=10
        )
        self.password = password

        self.JVC_REQ = b"PJREQ"
        if self.password != None:
            if len(self.password) == 10:
                self.JVC_REQ = b"PJREQ_" + bytes(self.password, "ascii")
            elif len(self.password) == 9:
                self.JVC_REQ = b"PJREQ_" + bytes(self.password, "ascii") + b"\x00"
            elif len(self.password) == 8:
                self.JVC_REQ = b"PJREQ_" + bytes(self.password, "ascii") + b"\x00\x00"
            else:
                raise JVCConfigError(
                    "Specified network password invalid (too long/short)"
                )

        try:
            self._send_command(Commands.nullcmd)
        except JVCCannotConnectError as e:
            raise JVCConfigError(
                f"Couldn't connect to projector at the specified address: {self.host}:{self.port}. "
                f"Make sure the host and port are set correctly and control4 is turned off in projector settings"
            ) from e

    def _throttle(self) -> None:
        if self.delay == 0:
            return

        delta = datetime.datetime.now() - self.last_command_time

        if self.delay > delta:
            sleep((self.delay - delta).total_seconds())

        return

    def _handshake(self) -> socket.socket:

        JVC_GRT = b"PJ_OK"
        JVC_REQ = self.JVC_REQ
        JVC_ACK = b"PJACK"

        jvc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        jvc_sock.settimeout(self.connect_timeout)

        try:
            jvc_sock.connect((self.host, self.port))  # connect to projector
        except socket.timeout as e:
            jvc_sock.close()
            raise JVCCannotConnectError(
                "Timed out when trying to connect to projector"
            ) from e
        except ConnectionRefusedError as e:
            jvc_sock.close()
            raise JVCCannotConnectError(
                "Connection refused. There may be another active connection, or `delay_ms` may be too short"
            ) from e

        # 3 step handshake:
        # Projector sends PJ_OK, client sends PJREQ, projector replies with PJACK
        # first, after connecting, see if we receive PJ_OK. If not, raise exception
        try:
            message = jvc_sock.recv(len(JVC_GRT))
            if message != JVC_GRT:
                jvc_sock.close()
                raise JVCHandshakeError(
                    f"Projector did not reply with PJ_OK (got `{message}` instead)"
                )
        except socket.timeout as e:
            jvc_sock.close()
            raise JVCHandshakeError("Timeout when waiting to receive PJ_OK") from e

        # try sending PJREQ, if there's an error, raise exception
        try:
            jvc_sock.sendall(JVC_REQ)
        except socket.error as e:
            jvc_sock.close()
            raise JVCHandshakeError("Socket exception when sending PJREQ.") from e

        # see if we receive PJACK, if not, raise exception
        try:
            message = jvc_sock.recv(len(JVC_ACK))
            if message != JVC_ACK:
                jvc_sock.close()
                raise JVCHandshakeError(
                    f"Projector did not reply with PJACK (received `{message}` instead)"
                )
        except socket.timeout as e:
            jvc_sock.close()
            raise JVCHandshakeError("Timeout when waiting to receive PJACK") from e

        return jvc_sock

    def _send_command(self, command: Command, value: str = "") -> Optional[str]:
        """Call Commands.read() if not value, else Commands.write(value)"""

        self._throttle()

        jvc_sock: socket.socket = self._handshake()

        result: Optional[str] = None

        if value:
            command.write(jvc_sock, value)
        elif command.write_only:
            command.write(jvc_sock)
        else:
            result = command.read(jvc_sock)

        jvc_sock.close()
        self.last_command_time = datetime.datetime.now()

        if result is not None:
            return result

    def power_on(self) -> None:
        # TODO: check powerstate before calling
        self._send_command(Commands.power, "on")

    def power_off(self) -> None:
        # TODO: check powerstate before calling
        self._send_command(Commands.power, "off")

    def command(self, command_string: str) -> Optional[str]:
        # ps = self.power_state()
        # if (command_string not in ["power-on", "power"]) and ps != "lamp_on":
        #     raise JVCPoweredOffError(
        #         f"Can't execute command_string: `{command_string}` unless the projector is in state `lamp_on`. "
        #         f"Current power state is: `{ps}`"
        #     )

        commandl: list[str] = command_string.split("-")
        print(commandl)

        if not hasattr(Commands, commandl[0]):
            raise JVCCommandNotFoundError(
                f"The requested command: `{command_string}` is not in the list of recognised commands"
            )
        else:
            if len(commandl) > 1:
                self._send_command(getattr(Commands, commandl[0]), commandl[1])
            else:
                return self._send_command(getattr(Commands, commandl[0]))

    def power_state(self) -> Optional[str]:
        return self._send_command(Commands.power)

    def is_on(self) -> bool:
        on = ["lamp_on", "reserved"]
        return self.power_state() in on
