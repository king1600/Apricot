__version__ = "1.4.8"
__author__  = "king1600"

#--------- Bind exit signals to task cleanup ---------#
import asyncio
from signal import SIGINT, SIGTERM
from asyncio import get_event_loop as get_loop
def __on_closing__():
    [t.cancel() for t in asyncio.Task.all_tasks()]
for sig in (SIGINT, SIGTERM):
    get_loop().add_signal_handler(sig, __on_closing__)
#######################################################

from .client import *