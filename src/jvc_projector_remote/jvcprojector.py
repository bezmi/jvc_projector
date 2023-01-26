import socket
from time import sleep
import datetime
import logging
from typing import Optional, Union
import traceback

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
        self.connect_timeout = connect_timeout if connect_timeout else 2
        self.delay = (
            datetime.timedelta(microseconds=(delay_ms * 1000))
            if isinstance(delay_ms, int)
            else datetime.timedelta(microseconds=(600000))
        )
        self.last_command_time = datetime.datetime.now() - datetime.timedelta(
            seconds=10
        )
        self.password = password if password else ""
        self.max_retries = max_retries if max_retries else 5

        _LOGGER.debug(
            f"initialising JVCProjector with host={self.host}, password={self.password}, port={self.port}, delay={self.delay.total_seconds()*1000}, connect_timeout={self.connect_timeout}, max_retries={self.max_retries}"
        )
        
        self.JVC_REQ = b"PJREQ"

        if self.password:
            if len(self.password) < 8:
                raise JVCConfigError("Specified network password invalid (too short). Please check your configuration.")
            if len(self.password) > 10:
                raise JVCConfigError("Specified network password invalid (too long). Please check your configuration.")

            self.JVC_REQ = b"PJREQ" + b"_" + bytes(self.password, "ascii").ljust(10, b"\x00")

    def __throttle(self, last_time: datetime.datetime) -> None:
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
            raise JVCConnectionError(
                "Timed out when trying to connect to projector"
            ) from e
        except OSError as e:
            jvc_sock.close()
            if retry < self.max_retries:
                _LOGGER.debug(
                    f"Received error: {repr(e)} when trying to connect, retrying (we're on retry number {retry+1} of {self.max_retries})"
                )
                self.__throttle(datetime.datetime.now())
                jvc_sock = self.__connect(retry + 1)
                _LOGGER.debug(f"Connection successful")
                return jvc_sock
            raise JVCConnectionError(
                "Could not establish connection to projector"
            ) from e

    def handshake(self) -> socket.socket:

        JVC_GRT = b"PJ_OK"
        JVC_REQ = self.JVC_REQ
        JVC_ACK = b"PJACK"

        _LOGGER.debug(f"Attempting handshake")

        jvc_sock = self.__connect()

        try:
            message = jvc_sock.recv(len(JVC_GRT))
            if message != JVC_GRT:
                jvc_sock.close()
                raise JVCHandshakeError(
                    f"Unable to complete handshake. Projector did not reply with PJ_OK (got `{message}` instead)"
                )

        except socket.timeout as e:
            jvc_sock.close()
            raise JVCConnectionError("Timeout during handshake while waiting to receive PJ_OK") from e

        # try sending PJREQ, if there's an error, raise exception
        try:
            jvc_sock.sendall(JVC_REQ)
        except OSError as e:
            jvc_sock.close()
            raise JVCConnectionError("Socket exception during handshake when sending PJREQ.") from e

        # see if we receive PJACK, if not, raise exception
        try:
            message = jvc_sock.recv(len(JVC_ACK))
            if message != JVC_ACK:
                jvc_sock.close()
                raise JVCHandshakeError(
                    f"Unable to complete handshake. Projector did not reply with PJACK (received `{message}` instead)"
                )
        except socket.timeout as e:
            jvc_sock.close()
            raise JVCConnectionError("Timeout durin handshake when waiting to receive PJACK") from e

        _LOGGER.debug(f"Handshake successful")
        return jvc_sock

    def send_command(self, jvc_sock: socket.socket, command: Command, value: str = "") -> Union[str, bool]:
        """Send a single command to the projector from the list of known commands.

        returns a response for read commands or a boolean which is True if the command was successfully sent.
        """
        result: Union[str, bool] = False

        if value:
            _LOGGER.debug(
                f"writing property: {jfrmt.highlight(value)} to command group: {jfrmt.highlight(command.name)}"
            )
            command.write(jvc_sock, value)
            result = True
        elif command.write_only:
            _LOGGER.debug(
                f"sending write_only operation: {jfrmt.highlight(command.name)}"
            )
            command.write(jvc_sock)
            result = True
        else:
            _LOGGER.debug(
                f"reading from command group: {jfrmt.highlight(command.name)}"
            )
            result = command.read(jvc_sock)
            _LOGGER.debug(
                f"the state of command group: {jfrmt.highlight(command.name)} is: {jfrmt.highlight(result)}"
            )

            self.last_command_time = datetime.datetime.now()
            _LOGGER.debug(f"command sent successfully")
        return result

    def validate_connection(self) -> bool:
        try:
            _LOGGER.debug(
                f"Trying to establish communication with {jfrmt.highlight(f'{self.host}:{self.port}')}"
            )
            # short circuit the retry counter so we only try once
            s: socket.socket = self.__connect(self.max_retries)
            s.close()
            return True
        except JVCConnectionError:
            _LOGGER.warning(f"Couldn't verify connection to projector at the specified address: {self.host}:{self.port}.")
            return False

    def command(self, command: str, jvc_sock: Optional[socket.socket] = None, ignore_non_crit_error: bool = False) -> Optional[Union[str, bool]]:
        resp: Union[str, bool] = False
        commandspl: list[str] = command.split("-")
        is_temp_sock: bool = True if jvc_sock is None else False
        if jvc_sock is None:
            jvc_sock = self.handshake()

        # command doesn't exist
        if not hasattr(Commands, commandspl[0]):
            _LOGGER.warn(
                f"The requested command: `{command}` is not in the list of recognised commands"
            )
            resp = False
        else:
            try:
                if len(commandspl) > 1: # operation command
                    resp = self.send_command(jvc_sock, getattr(Commands, commandspl[0]), value=commandspl[1])
                else:
                    resp = self.send_command(jvc_sock, getattr(Commands, commandspl[0]))
            except JVCCommandError as e:
                if ignore_non_crit_error:
                    _LOGGER.warn(
                        f"There was an error when sending command: {command}. ignore_non_crit_error is True so socket will remain open, \n"
                        f"{traceback.format_exc()}"
                    )
                    resp = False
                else:
                    jvc_sock.close()
                    raise JVCCommandError("There was an error when sending the command: {command}. Aborting and closing the socket.") from e
            except Exception as e:
                jvc_sock.close()
                raise RuntimeError(f"Unexpected error when sending command: {command}. Aborting and closing the socket.") from e
        if is_temp_sock: jvc_sock.close()
        return resp
                        

    def power_on(self) -> None:
        """send the power_on command without caring about whether it was successful"""
        self.command("power-on")

    def power_off(self) -> None:
        """send the power_off command without caring about whether it was successful"""
        self.command("power-off")

    def power_state(self) -> Union[str, bool, None]:
        ps = self.command("power")
        return ps

    def is_on(self) -> bool:
        on = ["lamp_on", "reserved"]
        return self.power_state() in on

    def get_mac(self) -> Union[str, bool, None]:
        gm = self.command("macaddr")
        return gm

    def get_model(self) -> Union[str, bool, None]:
        model = self.command("modelinfo")
        return model
