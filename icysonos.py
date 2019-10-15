import argparse
import logging
import subprocess
from typing import Optional

import psutil
import pychromecast
import requests
import sys
import time
import urllib.parse
import soco
from pychromecast.socket_client import CastStatus

from pychromecast.controllers.media import MediaStatus
from pychromecast import Chromecast

from xml.sax.saxutils import escape

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
icecast_host = None
icecast_admin_user = None
icecast_admin_password = None
cast_source = None
sonos_controller = None


def get_darkice_process() -> Optional[psutil.Process]:
    """
    Get the running Darkice process
    :return: psutil.Process
    """
    for pid in psutil.pids():
        p = psutil.Process(pid)
        if p.name() == "darkice":
            return p


class CastStatusListener:
    def __init__(self, previous_status: CastStatus):
        self.previous_status = previous_status

    def new_cast_status(self, status: CastStatus):
        logger.info(f'previous cast status: {self.previous_status}')
        logger.info(f'cast status: {status}')

        if self.previous_status.app_id is None and status.app_id:
            darkice_process = get_darkice_process()
            if darkice_process:
                logger.info(f'Darkice is running, pid: {darkice_process.pid}')
            else:
                logger.info('Darkice is not running')
                darkice_pid = subprocess.Popen(['darkice', '-c', '/etc/darkice.cfg']).pid
                logger.info(f'Darkice is running, pid: {darkice_pid}')

            # Set the Sonos source to be the Chromecast stream
            sonos_controller.play_uri(uri=f'http://{icecast_host}/pi.mp3', title='Chromecast', force_radio=True)

        self.previous_status = status


class MediaStatusListener:
    def new_media_status(self, status: MediaStatus):
        """
        Listens to media status changes.
        :param status: the new status
        """
        logger.info(f'Media status changed to: state -> {status.player_state}, title -> {status.artist} - {status.title}, content -> {status.content_type}')
        if status.player_state == pychromecast.controllers.media.MEDIA_PLAYER_STATE_PLAYING:
            if status.title:
                title = urllib.parse.quote_plus(status.title)
                title_xml_safe = escape(status.title)
            if status.artist:
                artist = urllib.parse.quote_plus(status.artist)
                artist_xml_safe = escape(status.artist)
            if status.album_name:
                album_name = urllib.parse.quote_plus(status.album_name)
                album_name_xml_safe = escape(status.album_name)
            else:
                album_name = ''
                album_name_xml_safe = ''
            # TODO: might need smarter logic to find the appropriate image to push to Icecast
            if status.images:
                album_art_url = status.images[0].url

            if status.title or status.artist:
                if icecast_host:
                    icecast_update_url = f'http://{icecast_host}/admin/metadata?mount=/pi.mp3&mode=updinfo&song={artist}+-+{title}'
                    r = requests.get(icecast_update_url, auth=(icecast_admin_user, icecast_admin_password))
                    logger.info(f'Update to Icecast server: {r.status_code}')

                meta_template = """<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/"
                                                xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
                                                xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"
                                                xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">
                                                <item id="R:0/0/0" parentID="R:0/0" restricted="true">
                                                    <res protocolInfo="x-rincon-mp3radio:*:*:*">x-rincon-mp3radio://http://192.168.0.100:8000/pi.mp3</res>
                                                    <r:streamContent>{artist_xml_safe} - {title_xml_safe}</r:streamContent>
                                                    <r:description>My Radio Stations</r:description>
                                                    <dc:title>Chromecast</dc:title>
                                                    <upnp:class>object.item.audioItem.audioBroadcast</upnp:class>
                                                    <upnp:albumArtURI>{album_art_url}</upnp:albumArtURI>
                                                    <desc id="cdudn" nameSpace="urn:schemas-rinconnetworks-com:metadata-1-0/">SA_RINCON65031_</desc>
                                                </item>
                                            </DIDL-Lite>"""
                meta = meta_template.format(
                    title_xml_safe=title_xml_safe,
                    artist_xml_safe=artist_xml_safe,
                    album_art_url=album_art_url
                )
                sonos_controller.play_uri(uri=f'http://{icecast_host}/pi.mp3', meta=meta, force_radio=True)

                # TODO: metadata can be updated by treating the stream like a normal media file
                # metadata = f"""<DIDL-Lite xmlns:dc="http://purl.org/dc/elements/1.1/"
                #                 xmlns:upnp="urn:schemas-upnp-org:metadata-1-0/upnp/"
                #                 xmlns:r="urn:schemas-rinconnetworks-com:metadata-1-0/"
                #                 xmlns="urn:schemas-upnp-org:metadata-1-0/DIDL-Lite/">
                #                 <item id="R:0/0/0" parentID="R:0/0" restricted="true">
                #                     <dc:title>{title_xml_safe}</dc:title>
                #                     <dc:creator>{artist_xml_safe}</dc:creator>
                #                     <upnp:album>{album_name_xml_safe}</upnp:album>
                #                     <upnp:class>object.item.audioItem.linein</upnp:class>
                #                     <upnp:albumArtURI>{album_art_url}</upnp:albumArtURI>
                #                 </item>
                #             </DIDL-Lite>"""
                # sonos_controller.avTransport.SetAVTransportURI([
                #     ('InstanceID', 0),
                #     ('CurrentURI', 'http://192.168.0.100:8000/pi.mp3'),
                #     ('CurrentURIMetaData', metadata)
                # ])


def main(args):
    # Get all Google Cast enabled devices
    chromecasts = pychromecast.get_chromecasts()

    if len(chromecasts) == 0:
        logger.error('No Chromecast devices found!')
        sys.exit(1)

    # [cc.device.friendly_name for cc in chromecasts]
    # ['Dev', 'Living Room', 'Den', 'Bedroom']

    if args.cast_device_name:
        for cc in chromecasts:
            logger.info(f'Found device: {cc.device.friendly_name}')
            if cc.device.friendly_name == args.cast_device_name:
                cast_source = cc
    # To improve speed, the hostname be used to connect to the Chromecast device
    elif args.cast_device_host:
        cast_source = pychromecast.Chromecast(args.cast_device_host)

    if cast_source:
        # Start worker thread and wait for cast device to be ready
        cast_source.wait()
        logger.info(cast_source.device)
        # DeviceStatus(friendly_name='Living Room', model_name='Chromecast', manufacturer='Google Inc.', uuid=UUID('df6944da-f016-4cb8-97d0-3da2ccaa380b'), cast_type='cast')

        logger.info(cast_source.status)
        # CastStatus(is_active_input=True, is_stand_by=False, volume_level=1.0, volume_muted=False, app_id='CC1AD845', display_name='Default Media Receiver', namespaces=['urn:x-cast:com.google.cast.player.message', 'urn:x-cast:com.google.cast.media'], session_id='CCA39713-9A4F-34A6-A8BF-5D97BE7ECA5C', transport_id='web-9', status_text='')

        cast_source.register_status_listener(CastStatusListener(cast_source.status))

        mc = cast_source.media_controller
        mc.register_status_listener(MediaStatusListener())

        while True:
            time.sleep(2)
    else:
        logger.error(f'Device "${args.source_device_name}" not found!')
        sys.exit(1)


# class MyController(BaseController):
#     def __init__(self):
#         super(MyController, self).__init__('urn:x-cast:com.google.cast.media')
#
#     def receive_message(self, message, data):
#         logger.info("Wow, I received this message: {}".format(data))
#         return True  # indicate you handled this message


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Darkice to Sonos bridge')
    parser.add_argument('--cast-device-name', '-c', help='the Chromecast source device name')
    parser.add_argument('--cast-device-host', '-d', help='the Chromecast source device hostname')
    parser.add_argument('--icecast-address', '-a', help='the Icecast 2 server address')
    parser.add_argument('--icecast-admin-user', '-u', help='the Icecast 2 server hostname and port')
    parser.add_argument('--icecast-admin-password', '-p', help='the Icecast 2 server hostname and port')
    parser.add_argument('--sonos-host', '-s', help='the Sonos controller hostname')
    args = parser.parse_args()

    icecast_host = args.icecast_address
    icecast_admin_user = args.icecast_admin_user
    icecast_admin_password = args.icecast_admin_password
    sonos_host = args.sonos_host

    sonos_controller = soco.SoCo(sonos_host)

    main(args)
