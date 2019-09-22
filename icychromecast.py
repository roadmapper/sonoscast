import time
import pychromecast
import sys
import logging
import requests
import urllib.parse

from pychromecast.controllers.media import MediaStatus

logger = logging.getLogger(__name__)
source_device_name = sys.argv[1]
icecast_host = sys.argv[2]


def media_status_listener(status: MediaStatus):
    """
    Listens to media status changes.
    :param status: the new status
    """
    logger.info(f'Media status changed to: {status}')
    title = urllib.parse.quote_plus(status.title)
    artist = urllib.parse.quote_plus(status.artist)
    # TODO: might need smarter logic to find the appropriate image to push to Icecast
    # album_art = status.images[0].url

    requests.get(f'http://{icecast_host}/admin/metadata?mount=/stream&mode=updinfo&song={title}+-+{artist}',
                 auth=('admin', 'hackme'))


def main():
    # Get all Google Cast enabled devices
    chromecasts = pychromecast.get_chromecasts()

    if len(chromecasts) == 0:
        logging.error('No Chromecast devices found!')
        sys.exit(1)

    # [cc.device.friendly_name for cc in chromecasts]
    # ['Dev', 'Living Room', 'Den', 'Bedroom']

    source_device = None

    for cc in chromecasts:
        logging.info(f'Found device: {cc.device.friendly_name}')
        if cc.device.friendly_name == source_device_name:
            source_device = cc

    # TODO: to improve speed, the IP should be used to connect to the Chromecast device
    # source_device = pychromecast.Chromecast(source_device_ip)

    cast = next(source_device)
    # Start worker thread and wait for cast device to be ready
    cast.wait()
    logging.info(cast.device)
    # DeviceStatus(friendly_name='Living Room', model_name='Chromecast', manufacturer='Google Inc.', uuid=UUID('df6944da-f016-4cb8-97d0-3da2ccaa380b'), cast_type='cast')

    logging.info(cast.status)
    # CastStatus(is_active_input=True, is_stand_by=False, volume_level=1.0, volume_muted=False, app_id='CC1AD845', display_name='Default Media Receiver', namespaces=['urn:x-cast:com.google.cast.player.message', 'urn:x-cast:com.google.cast.media'], session_id='CCA39713-9A4F-34A6-A8BF-5D97BE7ECA5C', transport_id='web-9', status_text='')

    mc = cast.media_controller
    mc.register_status_listener()
    # mc.play_media('http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4', 'video/mp4')
    # mc.block_until_active()
    # print(mc.status)
    # MediaStatus(current_time=42.458322, content_id='http://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4', content_type='video/mp4', duration=596.474195, stream_type='BUFFERED', idle_reason=None, media_session_id=1, playback_rate=1, player_state='PLAYING', supported_media_commands=15, volume_level=1, volume_muted=False)
# <MediaStatus {'metadata_type': 0, 'title': 'CGI 3D Animated Short: "Mechanical" - by ESMA', 'series_title': None, 'season': None, 'episode': None, 'artist': None, 'album_name': None, 'album_artist': None, 'track': None, 'subtitle_tracks': {}, 'images': [MediaImage(url='https://i.ytimg.com/vi/sDI2admB0eQ/hqdefault.jpg', height=None, width=None)], 'supports_pause': True, 'supports_seek': True, 'supports_stream_volume': False, 'supports_stream_mute': False, 'supports_skip_forward': False, 'supports_skip_backward': False, 'current_time': 13.874, 'content_id': 'sDI2admB0eQ', 'content_type': 'x-youtube/video', 'duration': 400.841, 'stream_type': 'BUFFERED', 'idle_reason': None, 'media_session_id': 1333990241, 'playback_rate': 1, 'player_state': 'PLAYING', 'supported_media_commands': 3, 'volume_level': 0.8600000143051147, 'volume_muted': False, 'media_custom_data': {}, 'media_metadata': {'metadataType': 0, 'title': 'CGI 3D Animated Short: "Mechanical" - by ESMA', 'subtitle': 'TheCGBros', 'images': [{'url': 'https://i.ytimg.com/vi/sDI2admB0eQ/hqdefault.jpg'}]}, 'current_subtitle_tracks': [], 'last_updated': datetime.datetime(2018, 10, 3, 17, 4, 19, 470151)}>
    # mc.pause()
    # time.sleep(5)
    # mc.play()
    while not exit():
        time.sleep(2)
        logger.info('asuh')


# class MyController(BaseController):
#     def __init__(self):
#         super(MyController, self).__init__('urn:x-cast:com.google.cast.media')
#
#     def receive_message(self, message, data):
#         logger.info("Wow, I received this message: {}".format(data))
#         return True  # indicate you handled this message


if __name__ == '__main__':
    main()
