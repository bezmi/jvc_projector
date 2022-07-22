import socket
from time import sleep
import datetime
import logging
from typing import Optional

from .jvccommands import *

_LOGGER = logging.getLogger(__name__)


class JVCProjector:
    """JVC Projector Control"""

    def __init__(
        self,
        host: str,
        password: Optional[str] = None,
        port: Optional[int] = None,
        delay_ms: Optional[int] = None,
        connect_timeout: Optional[int] = None,
        max_retries: Optional[int] = None,
    ):
        self.host = host
        self.port = port if port else 20554
        self.connect_timeout = connect_timeout if connect_timeout else 10
        self.delay = (
            datetime.timedelta(microseconds=(delay_ms * 1000))
            if delay_ms
            else datetime.timedelta(microseconds=(600000))
        )
        self.last_command_time = datetime.datetime.now() - datetime.timedelta(
            seconds=10
        )
        self.password = password if password else ""
        self.max_retries = max_retries if max_retries else 10

        _LOGGER.debug(
            f"initialising JVCProjector with host={self.host}, password={self.password}, port={self.port}, delay={self.delay.total_seconds()*1000}, connect_timeout={self.connect_timeout}, max_retries={self.max_retries}"
        )

        self.JVC_REQ = b"PJREQ"
        if self.password != None and len(self.password):
            if len(self.password) == 10:
                self.JVC_REQ = b"PJREQ_" + bytes(self.password, "ascii")
            elif len(self.password) == 9:
                self.JVC_REQ = b"PJREQ_" + bytes(self.password, "ascii") + b"\x00"
            elif len(self.password) == 8:
                self.JVC_REQ = b"PJREQ_" + bytes(self.password, "ascii") + b"\x00\x00"
            else:
                raise JVCConfigError(
                    "Specified network password invalid (too long/short). Please check your configuration."
                )

    def __throttle(self, last_time: datetime.datetime) -> None:
        if self.delay == 0:
            return

        delta = datetime.datetime.now() - last_time

        if self.delay > delta:
            sleep((self.delay - delta).total_seconds() * 1.1)

    def __connect(self, retry: int = 0) -> socket.socket:
        jvc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        jvc_sock.settimeout(self.connect_timeout)
        try:
            jvc_sock.connect((self.host, self.port))
            return jvc_sock
        except socket.timeout as e:
            jvc_sock.close()
            raise JVCCannotConnectError(
                "Timed out when trying to connect to projector"
            ) from e
        except OSError as e:
            jvc_sock.close()
            if retry <= self.max_retries:
                _LOGGER.debug(
                    f"Received error: {repr(e)} when trying to connect, retrying (we're on retry number {retry+1} of {self.max_retries})"
                )
                self.__throttle(datetime.datetime.now())
                jvc_sock = self.__connect(retry + 1)
                _LOGGER.debug(f"Connection successful")
                return jvc_sock
            raise JVCCannotConnectError(
                "Could not establish connection to projector"
            ) from e

    def __handshake(self) -> socket.socket:

        JVC_GRT = b"PJ_OK"
        JVC_REQ = self.JVC_REQ
        JVC_ACK = b"PJACK"

        jvc_sock = self.__connect()

        _LOGGER.debug(f"Attempting handshake")

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
        except OSError as e:
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

        _LOGGER.debug(f"Handshake successful")
        return jvc_sock

    def _send_command(self, command: Command, value: str = "") -> Optional[str]:
        """Call Commands.read() if not value, else Commands.write(value)"""

        self.__throttle(self.last_command_time)

        jvc_sock: socket.socket = self.__handshake()

        result: Optional[str] = None

        if value:
            _LOGGER.debug(
                f"writing property: {jfrmt.highlight(value)} to command group: {jfrmt.highlight(command.name)}"
            )
            command.write(jvc_sock, value)
        elif command.write_only:
            _LOGGER.debug(
                f"sending write_only operation: {jfrmt.highlight(command.name)}"
            )
            command.write(jvc_sock)
        else:
            _LOGGER.debug(
                f"reading from command group: {jfrmt.highlight(command.name)}"
            )
            result = command.read(jvc_sock)

        self.last_command_time = datetime.datetime.now()
        _LOGGER.debug(f"command sent successfully")

        if result is not None:
            _LOGGER.debug(
                f"the state of command group: {jfrmt.highlight(command.name)} is: {jfrmt.highlight(result)}"
            )
            return result

    def validate_connection(self) -> bool:
        try:
            _LOGGER.debug(
                f"Sending nullcmd to {jfrmt.highlight(f'{self.host}:{self.port}')} to verify connection"
            )
            self._send_command(Commands.nullcmd)
            return True
        except JVCCannotConnectError as e:
            _LOGGER.debug(f"Couldn't verify connection to projector at the specified address: {self.host}:{self.port}.")
            return False


    def power_on(self) -> None:
        self._send_command(Commands.power, "on")

    def power_off(self) -> None:
        self._send_command(Commands.power, "off")

    def command(self, command_string: str) -> Optional[str]:
        ps = self.power_state()
        if (command_string not in ["power-on", "power"]) and ps != "lamp_on":
            raise JVCPoweredOffError(
                f"Can't execute command: `{command_string}` unless the projector is in state `lamp_on`. "
                f"Current power state is: `{ps}`"
            )

        commandl: list[str] = command_string.split("-")

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
