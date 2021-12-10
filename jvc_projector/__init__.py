import socket
from enum import Enum
from time import sleep
import datetime


class Commands(Enum):
    # power commands
    power_on = b"\x21\x89\x01\x50\x57\x31\x0A"
    power_off = b"\x21\x89\x01\x50\x57\x30\x0A"

    # lens memory commands
    memory1 = b"\x21\x89\x01\x49\x4E\x4D\x4C\x30\x0A"
    memory2 = b"\x21\x89\x01\x49\x4E\x4D\x4C\x31\x0A"
    memory3 = b"\x21\x89\x01\x49\x4E\x4D\x4C\x32\x0A"
    memory4 = b"\x21\x89\x01\x49\x4E\x4D\x4C\x33\x0A"
    memory5 = b"\x21\x89\x01\x49\x4E\x4D\x4C\x34\x0A"

    # input commands
    hdmi1 = b"\x21\x89\x01\x49\x50\x36\x0A"
    hdmi2 = b"\x21\x89\x01\x49\x50\x37\x0A"

    # power status query commands
    power_status   = b"\x3F\x89\x01\x50\x57\x0A"
    current_output = b"\x3F\x89\x01\x49\x50\x0A"
    
    # picture mode commands
    pm_cinema = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x31\x0A"
    pm_hdr = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x34\x0A"
    pm_natural = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x33\x0A"
    pm_film = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x30\x0A"
    pm_THX = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x36\x0A"
    pm_user1 = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x43\x0A"
    pm_user2 = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x44\x0A"
    pm_user3 = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x45\x0A"
    pm_user4 = b"\x21\x89\x01\x50\x4D\x50\x4D\x30\x46\x0A"
    pm_user5 = b"\x21\x89\x01\x50\x4D\x50\x4D\x31\x30\x0A"
    pm_user6 = b"\x21\x89\x01\x50\x4D\x50\x4D\x31\x31\x0A"
    pm_hlg = b"\x21\x89\x01\x50\x4D\x50\x4D\x31\x34\x0A"

    # low latency enable/disable
    pm_low_latency_enable = b"\x21\x89\x01\x50\x4D\x4C\x4C\x31\x0A"
    pm_low_latency_disable = b"\x21\x89\x01\x50\x4D\x4C\x4C\x30\x0A"

    # mask commands
    mask_off = b"\x21\x89\x01\x49\x53\x4D\x41\x32\x0A"
    mask_custom1 = b"\x21\x89\x01\x49\x53\x4D\x41\x30\x0A"
    mask_custom2 = b"\x21\x89\x01\x49\x53\x4D\x41\x31\x0A"
    mask_custom3 = b"\x21\x89\x01\x49\x53\x4D\x41\x33\x0A"

    #lamp commands
    lamp_high = b"\x21\x89\x01\x50\x4D\x4C\x50\x31\x0A"
    lamp_low = b"\x21\x89\x01\x50\x4D\x4C\x50\x30\x0A"

    #menu controls
    menu = b"\x21\x89\x01\x52\x43\x37\x33\x32\x45\x0A"
    menu_down = b"\x21\x89\x01\x52\x43\x37\x33\x30\x32\x0A"
    menu_left = b"\x21\x89\x01\x52\x43\x37\x33\x33\x36\x0A"
    menu_right = b"\x21\x89\x01\x52\x43\x37\x33\x33\x34\x0A"
    menu_up = b"\x21\x89\x01\x52\x43\x37\x33\x30\x31\x0A"
    menu_ok = b"\x21\x89\x01\x52\x43\x37\x33\x32\x46\x0A"
    menu_back = b"\x21\x89\x01\x52\x43\x37\x33\x30\x33\x0A"

    #Lens Aperture commands
    aperture_off = b"\x21\x89\x01\x50\x4D\x44\x49\x30\x0a"
    aperture_auto1 = b"\x21\x89\x01\x50\x4D\x44\x49\x31\x0a"
    aperture_auto2 = b"\x21\x89\x01\x50\x4D\x44\x49\x32\x0a"

    #Anamorphic commands
    anamorphic_off = b"\x21\x89\x01\x49\x4E\x56\x53\x30\x0A"
    anamorphic_a = b"\x21\x89\x01\x49\x4E\x56\x53\x31\x0A"
    anamorphic_b = b"\x21\x89\x01\x49\x4E\x56\x53\x32\x0A"
    anamorphic_c = b"\x21\x89\x01\x49\x4E\x56\x53\x33\x0A"



class PowerStates(Enum):
    standby   = b"\x40\x89\x01\x50\x57\x30\x0A"
    cooling   = b"\x40\x89\x01\x50\x57\x32\x0A"
    emergency = b"\x40\x89\x01\x50\x57\x34\x0A"

    # on some projectors like the DLA-X5900, the status
    # is returned as the "reserved" on below when the
    # projector lamp is warming up and "lamp_on" when
    # the lamp is on
    lamp_on  = b"\x40\x89\x01\x50\x57\x31\x0A"
    reserved = b"\x40\x89\x01\x50\x57\x33\x0A"


class ACKs(Enum):
    power_ack = b"\x06\x89\x01\x50\x57\x0A"
    input_ack = b"\x06\x89\x01\x49\x50\x0A"


class JVCProjector:
    """JVC Projector Control"""

    def __init__(self, host, port=20554, delay_ms=600, connect_timeout=60):
        self.host = host
        self.port = port
        self.connect_timeout = connect_timeout
        self.delay = datetime.timedelta(microseconds=(delay_ms * 1000))
        self.last_command_time = datetime.datetime.now() - datetime.timedelta(seconds=10)

    def throttle(self):
        if self.delay == 0:
            return

        delta = datetime.datetime.now() - self.last_command_time

        if self.delay > delta:
            sleep((self.delay - delta).total_seconds())

        return

    def _send_command(self, operation, ack=None):
        JVC_GREETING = b'PJ_OK'
        JVC_REQ = b'PJREQ'
        JVC_ACK = b'PJACK'
        result = False

        self.throttle()

        jvc_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        jvc_sock.settimeout(self.connect_timeout)
        jvc_sock.connect((self.host, self.port)) # connect to projector

        # 3 step handshake:
        # Projector sends PJ_OK, client sends PJREQ, projector replies with PJACK
        # first, after connecting, see if we receive PJ_OK. If not, raise exception
        if jvc_sock.recv(len(JVC_GREETING)) != JVC_GREETING:
            raise Exception("Projector did not reply with correct PJ_OK greeting")

        # try sending PJREQ, if there's an error, raise exception
        try:
            jvc_sock.sendall(JVC_REQ)
        except socket.error as e:
            raise Exception("Socket exception when sending PJREQ")

        # see if we receive PJACK, if not, raise exception
        if jvc_sock.recv(len(JVC_ACK)) != JVC_ACK:
            raise Exception("Socket exception on PJACK")

        # 3 step connection is verified, send the command
        jvc_sock.sendall(operation)

        # if we send a command that returns info, the projector will send
        # an ack, followed by the message. Check to see if the ack sent by
        # projector is correct, then return the message.
        if ack:
            ACK = jvc_sock.recv(len(ack))

            if ACK == ack:
                message = jvc_sock.recv(1024)
                result = message

        jvc_sock.close()

        self.last_command_time = datetime.datetime.now()

        return result

    def power_on(self):
        self._send_command(Commands.power_on.value)

    def power_off(self):
        self._send_command(Commands.power_off.value)

    def command(self, command_string):
        if not hasattr(Commands, command_string):
            return False
        else:
            self._send_command(Commands[command_string].value)
            return True

    def power_state(self):
        message = self._send_command(Commands.power_status.value, ack=ACKs.power_ack.value)
        return PowerStates(message).name

    def is_on(self):
        on = [PowerStates.lamp_on.value, PowerStates.reserved.value]
        return self.power_state() in on

