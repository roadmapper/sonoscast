from queue import Empty

from soco import SoCo
from soco.events import event_listener
import logging
from pprint import pprint

logging.basicConfig(level=logging.DEBUG)
# pick a device
device = SoCo('192.168.0.9')

# print out the events as they arise
sub = device.renderingControl.subscribe()
sub2 = device.avTransport.subscribe()

while True:
    try:
        event = sub.events.get(timeout=0.5)
        pprint(event.variables)
    except Empty:
        pass
    try:
        event = sub2.events.get(timeout=0.5)
        pprint(event.variables)
    except Empty:
        pass

    except KeyboardInterrupt:
        sub.unsubscribe()
        sub2.unsubscribe()
        event_listener.stop()
        break
