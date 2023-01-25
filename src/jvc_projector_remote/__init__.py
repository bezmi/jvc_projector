from .jvcprojector import *
from .jvccommands import *
from importlib.metadata import version
import logging

__version__ = version('jvc_projector_remote')
logging.getLogger(__name__).debug(f"imported jvc_projector_remote {__version__}")

