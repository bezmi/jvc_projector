import socket
from time import sleep
import datetime
import logging
from typing import Optional, Union
import traceback
import errno

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
        
        if self.password:
            if len(self.password) < 8:
                raise JVCConfigError("Specified network password invalid (too short). Please check your configuration.")
            if len(self.password) > 10:
                raise JVCConfigError("Specified network password invalid (too long). Please check your configuration.")


        self.jvc_sock: Optional[socket.socket] = None
        # self.jvc_sock.settimeout(self.connect_timeout)

    def __throttle(self, last_time: datetime.datetime) -> None:
        delta = datetime.datetime.now() - last_time

        if self.delay > delta:
            sleep((self.delay - delta).total_seconds() * 1.1)

    def __connect(self, retry: int = 0) -> None:
        self.jvc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.jvc_sock.settimeout(self.connect_timeout)
        try:
            _LOGGER.debug("Trying to establish connection.")
            self.jvc_sock.connect((self.host, self.port))
        except socket.timeout as e:
            self.jvc_sock.close()
            raise JVCConnectionError(
                "Timeout when trying to connect to projector"
            ) from None
        except OSError as e:
            self.jvc_sock.close()
            if e.errno == errno.EISCONN:
                return
            if retry < self.max_retries:
                _LOGGER.debug(
                    f"Received error: {repr(e)}, {e.errno} when trying to connect, retrying (we're on retry number {retry+1} of {self.max_retries})"
                )
                self.__throttle(datetime.datetime.now())
                return self.__connect(retry + 1)
                # _LOGGER.debug(f"Connection successful")
                # return self.jvc_sock
            raise JVCConnectionError(
                "Could not establish connection to projector"
            ) from e

    def __close(self) -> None:
        if self.jvc_sock is not None:
            self.jvc_sock.close()
        self.jvc_sock = None

    def handshake(self) -> None:

        JVC_GRT = b"PJ_OK"
        JVC_REQ = (b"PJREQ" + b"_" + bytes(self.password, "ascii")).ljust(10, b"\x00") if self.password else b"PJREQ"
        JVC_ACK = b"PJACK"

        _LOGGER.debug(f"Attempting handshake")
        try:
            if self.jvc_sock is None:
                self.__connect()
            else:
                _LOGGER.debug("already connected, proceeding")
                return
            assert self.jvc_sock is not None
            message: bytes = self.jvc_sock.recv(len(JVC_GRT))
            if message != JVC_GRT:
                self.__close()
                raise JVCHandshakeError(
                    f"Unable to complete handshake. Projector did not reply with PJ_OK (got `{message}` instead)"
                )
        except socket.timeout as e:
            self.__close()
            raise JVCConnectionError("Timeout during handshake while waiting to receive PJ_OK") from None

        # try sending PJREQ, if there's an error, raise exception
        try:
            self.jvc_sock.sendall(JVC_REQ)
        except OSError as e:
            self.jvc_sock.close()
            raise JVCConnectionError("Exception during handshake when sending PJREQ.") from e

        # see if we receive PJACK, if not, raise exception
        try:
            message = self.jvc_sock.recv(len(JVC_ACK))
            if message != JVC_ACK:
                self.__close()
                raise JVCHandshakeError(
                    f"Unable to complete handshake. Projector did not reply with PJACK (received `{message}` instead)"
                )
        except socket.timeout as e:
            self.__close()
            raise JVCConnectionError("Timeout during handshake when waiting to receive PJACK") from None

        _LOGGER.debug(f"Handshake successful")

    def send_command(self, command: Command, write_value: str = "") -> Union[str, bool]:
        """Send a single command to the projector from the list of known commands.

        returns a response for read commands or a boolean which is True if the command was successfully sent.
        """
        result: Union[str, bool] = False

        if self.jvc_sock is None:
            self.handshake()
        assert self.jvc_sock is not None

        try:
            if write_value:
                _LOGGER.debug(
                    f"writing property: {jfrmt.highlight(write_value)} to command group: {jfrmt.highlight(command.name)}"
                )
                command.write(self.jvc_sock, write_value)
                result = True
            elif command.write_only:
                _LOGGER.debug(
                    f"sending write_only operation: {jfrmt.highlight(command.name)}"
                )
                command.write(self.jvc_sock)
                result = True
            else:
                _LOGGER.debug(
                    f"reading from command group: {jfrmt.highlight(command.name)}"
                )
                result = command.read(self.jvc_sock)
                _LOGGER.debug(
                    f"the state of command group: {jfrmt.highlight(command.name)} is: {jfrmt.highlight(result)}"
                )

                self.last_command_time = datetime.datetime.now()
                _LOGGER.debug(f"command sent successfully")
        except JVCConnectionError as e:
            self.__close()
            raise JVCConnectionError(f"Unexpected error when sending command: {jfrmt.highlight(command.name)} with value: '{jfrmt.highlight(write_value)}' to projector.") from e
        except JVCCommandError as e:
            raise JVCCommandError() from e
        return result

    def verify_connection(self) -> bool:
        try:
            _LOGGER.debug(f"Sending nullcmd to verify connection to projector at: {self.host}:{self.port}.")
            # short circuit the retry counter so we only try once
            self.handshake()
            self.command("nullcmd")
            self.__close()
            return True

        except JVCConnectionError:
            _LOGGER.warning(f"Couldn't verify connection to projector at the specified address: {self.host}:{self.port}. Is it powered on and connected to the network?")
            return False

    def command(self, command: str, ignore_non_crit_error: bool = False) -> Optional[Union[str, bool]]:
        """Send a single command in the string format '{command group}-{write value}
        
        For example: "power-on" will write "on" to the "power" group
                    "power" (no write value) will read from the power group
        
        For a full list of compatible commands, see the Commands class in jvccommands.py
        """
        commandspl: list[str] = command.split("-")

        # command doesn't exist
        if not hasattr(Commands, commandspl[0]):
            _LOGGER.warn(
                f"The requested command: `{command}` is not in the list of recognised commands"
            )
            return False
        else:
            try:
                if len(commandspl) > 1: # operation command
                    return self.send_command(getattr(Commands, commandspl[0]), write_value=commandspl[1])
                else:
                    return self.send_command(getattr(Commands, commandspl[0]))
            except JVCCommandError as e:
                if ignore_non_crit_error:
                    _LOGGER.warn(
                        f"Error when sending command: {command}. ignore_non_crit_error is True so continuing. Enable debug logging for more information."
                    )
                    _LOGGER.debug(f"{traceback.format_exc()}")
                    return False
                else:
                    self.__close()
                    raise JVCCommandError("Error when sending the command: {command}.") from e
            except Exception as e:
                self.__close()
                raise RuntimeError(f"Unexpected error when sending command: {command}.") from e
    
    def commands(self, commands: list[str], ignore_non_crit_error: bool = False) -> Optional[Union[str, bool]]:
        """Send a list of commands in the string format '{command group}-{write value}

        See help(JVCProjector.command) for further information about the format of the command string.
        """
        ret_list: list[Union[str, bool]] = []
        for command in commands:
            commandspl: list[str] = command.split("-")

            # command doesn't exist
            if not hasattr(Commands, commandspl[0]):
                _LOGGER.warn(
                    f"The requested command: `{command}` is not in the list of recognised commands"
                )
                ret_list.append(False)
                continue
            else:
                try:
                    if len(commandspl) > 1: # operation command
                        ret_list.append(self.send_command(getattr(Commands, commandspl[0]), write_value=commandspl[1]))
                        continue
                    else:
                        ret_list.append(self.send_command(getattr(Commands, commandspl[0])))
                        continue
                except JVCCommandError as e:
                    if ignore_non_crit_error:
                        _LOGGER.warn(
                            f"Error when sending command: {command}. ignore_non_crit_error is True so continuing. Enable debug logging for more information."
                        )
                        _LOGGER.debug(f"{traceback.format_exc()}")
                        ret_list.append(False)
                        continue
                    else:
                        self.__close()
                        raise JVCCommandError("Error when sending the command: {command}.") from e
                except Exception as e:
                    self.__close()
                    raise RuntimeError(f"Unexpected error when sending command: {command}.") from e

    def power_on(self) -> None:
        self.command("power-on")

    def power_off(self) -> None:
        self.command("power-off")

    def power_state(self) -> Union[str, bool, None]:
        return self.command("power")

    def is_on(self) -> bool:
        on = ["lamp_on", "reserved"]
        return self.power_state() in on

    def get_mac(self) -> Union[str, bool, None]:
        return self.command("macaddr")

    def get_model(self) -> Union[str, bool, None]:
        return self.command("modelinfo")
