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
                _LOGGER.debug("Already connected.")
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

    def send_command(self, command: Command, write_value: str = "") -> Optional[str]:
        """Send a single command to the projector from the list of known commands.

        Returns:
          write command (write_value is specified, or nullcmd): no return value, error if write was unsuccessful
          read command: (no write_value specified): str containing the ascii decoded response.
        """
        if self.jvc_sock is None:
            self.handshake()
        assert self.jvc_sock is not None

        try:
            # we might pass a "write_only" command like nullcmd which has no "values"
            # the nullcmd is the only one that falls into this - JVC uses the write header for it.
            if write_value or command.write_only: 
                _LOGGER.debug(
                    f"writing value: {jfrmt.highlight(write_value)} to command group: {jfrmt.highlight(command.name)}"
                )
                command.write(self.jvc_sock, write_value)
            else: # if write_value isn't specified and the command is not write_only, that we want to read the property
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


    def command(self, command: str, ignore_non_crit_error: bool = True) -> Union[str, bool]:
        """Send a single command in the string format '{command group}-{write value}
        
        For example: "power-on" will write "on" to the "power" group
                    "power" (no write value) will read from the power group
        Returns:
          write command (write value is specified, or nullcmd):
            True: the write was successful (or ACKs are ignored in the implementation)
            False: the write was unsuccessful 
          read command (no write value): string containing the response.

        NOTE: write commands will only return false if "ignore_non_crit_error" is true.
              If this value is False, then JVCCommandErrors, which are emitted when the command
              was not successfully sent will be raised as exceptions instead of warnings.
        
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
                if len(commandspl) > 1: # operation (write) command
                    self.send_command(getattr(Commands, commandspl[0]), write_value=commandspl[1])
                    return True
                    
                else: # request (read) command
                    ret = self.send_command(getattr(Commands, commandspl[0]))
                    assert ret is not None # can't be as we asked to read a value
                    return ret

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
    
    def commands(self, commands: list[str], ignore_non_crit_error: bool = False) -> list[Union[str, bool]]:
        """Send a list of commands in the string format '{command group}-{write value}

        Returns: mixed list boolean (for write commands) or string (for read commands) values.

        See help(JVCProjector.command) for further information about the format of the command string.
        """
        ret_list: list[Union[str, bool]] = []
        for command in commands:
            ret_list.append(self.command(command, ignore_non_crit_error = ignore_non_crit_error))
        return ret_list

    def verify_connection(self) -> bool:
        """Send the nullcmd to check if the projector is responsive and disconnect immediately."""
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
