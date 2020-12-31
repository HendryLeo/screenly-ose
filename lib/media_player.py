from platform import machine

import sh
import vlc

from settings import settings
from lib.diagnostics import get_raspberry_code, get_raspberry_model

VIDEO_TIMEOUT = 20  # secs


class MediaPlayer:
    def __init__(self):
        pass

    def set_asset(self, uri, duration):
        raise NotImplementedError

    def play(self):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def is_playing(self):
        raise NotImplementedError


# class VLCMediaPlayer(MediaPlayer):
#     def __init__(self):
#         MediaPlayer.__init__(self)
#         self.instance = vlc.Instance()
#         self.player = self.instance.media_player_new()

#         self.player.audio_output_set('alsa')

#     def set_asset(self, uri, duration):
#         # @TODO: HDMI or 3.5mm jack audio output
#         self.player.set_mrl(uri)

#     def play(self):
#         self.player.play()

#     def stop(self):
#         self.player.stop()

#     def is_playing(self):
#         return self.player.get_state() in [vlc.State.Playing, vlc.State.Buffering, vlc.State.Opening]
class VLCMediaPlayer(MediaPlayer):
    def __init__(self):
        MediaPlayer.__init__(self)
        self._arch = machine()

        self._run = None
        self._player_args = list()
        self._player_kwargs = dict()

    def set_asset(self, uri, duration):
        settings.load()

        if settings['audio_output'] == 'hdmi':
            audio_device_1 = 'sysdefault:CARD=b1'
            audio_device_2 = 'sysdefault:CARD=b2'
        else:
            audio_device_1 = 'sysdefault:CARD=Headphones'
            audio_device_2 = 'no-sound'

        self._player_args = ['vlc', uri]
        self._player_kwargs = {'play-and-exit': True, 'intf': 'dummy', 'ignore-config': True, 'fullscreen': True, 'video-on-top': True, 'no-video-title-show': True, 'aout': 'alsa', 'alsa-audio-device': audio_device_1, '_bg': True, '_no_out': True, '_no_err': True, '_no_pipe': True}
        if audio_device_2 == 'sysdefault:CARD=b2':
            self._player_kwargs2 = {'play-and-exit': True, 'intf': 'dummy', 'ignore-config': True, 'fullscreen': True, 'video-on-top': True, 'no-video-title-show': True, 'aout': 'alsa', 'alsa-audio-device': audio_device_2, 'qt-fullscreen-screennumber': 1, '_bg': True, '_no_out': True, '_no_err': True, '_no_pipe': True}
        else:
            self._player_kwargs2 = {'play-and-exit': True, 'intf': 'dummy', 'ignore-config': True, 'fullscreen': True, 'video-on-top': True, 'no-video-title-show': True, 'no-audio': True, 'qt-fullscreen-screennumber': 1, '_bg': True, '_no_out': True, '_no_err': True, '_no_pipe': True}

        if duration and duration != 'N/A':
            self._player_args = ['timeout', VIDEO_TIMEOUT + int(duration.split('.')[0])] + self._player_args

    def play(self):
        settings.load()
        self._run = sh.Command(self._player_args[0])(*self._player_args[1:], **self._player_kwargs)
        if settings['enable_second_screen'] and get_raspberry_model(get_raspberry_code()) == 'Model 4B':
            self._run2 = sh.Command(self._player_args[0])(*self._player_args[1:], **self._player_kwargs2)

    def stop(self):
        try:
            sh.killall('vlc', _ok_code=[1])
        except OSError:
            pass

    def is_playing(self):
        settings.load()
        if settings['enable_second_screen'] and get_raspberry_model(get_raspberry_code()) == 'Model 4B':
            return bool(self._run.process.alive or self._run2.process.alive)
        else:
            return bool(self._run.process.alive)


class OMXMediaPlayer(MediaPlayer):
    def __init__(self):
        MediaPlayer.__init__(self)
        self._arch = machine()

        self._run = None
        self._player_args = list()
        self._player_kwargs = dict()

    def set_asset(self, uri, duration):
        settings.load()

        if self._arch in ('armv6l', 'armv7l'):
            if settings['audio_output'] == 'hdmi':
                audio_device_1 = 'alsa:hw:0'
                audio_device_2 = 'alsa:hw:1'
            else:
                if get_raspberry_model(get_raspberry_code()) == 'Model 4B':
                    audio_device_1 = 'alsa:hw:2'
                else:
                    audio_device_1 = 'alsa:hw:1'
                audio_device_2 = 'no-sound'
            
            self._player_args = ['omxplayer', uri]
            self._player_kwargs = {'display': 2, 'o': audio_device_1, 'layer': 1, '_bg': True, '_ok_code': [0, 124, 143]}
            # multiple process for video output to different HDMI screens for RPI-4
            if audio_device_2 == 'alsa:hw:1':
                self._player_kwargs2 = {'display': 7, 'o': audio_device_2, 'layer': 1, '_bg': True, '_ok_code': [0, 124, 143]}
            else:
                # Setting audiotrack to -1 disables the audio decode
                self._player_kwargs2 = {'display': 7, 'n': -1, 'layer': 1, '_bg': True, '_ok_code': [0, 124, 143]}
        else:
            self._player_args = ['mplayer', uri, '-nosound']
            self._player_kwargs = {'_bg': True, '_ok_code': [0, 124]}

        if duration and duration != 'N/A':
            self._player_args = ['timeout', VIDEO_TIMEOUT + int(duration.split('.')[0])] + self._player_args

    def play(self):
        self._run = sh.Command(self._player_args[0])(*self._player_args[1:], **self._player_kwargs)
        if settings['enable_second_screen'] and get_raspberry_model(get_raspberry_code()) == 'Model 4B':
            self._run2 = sh.Command(self._player_args[0])(*self._player_args[1:], **self._player_kwargs2)

    def stop(self):
        try:
            sh.killall('omxplayer.bin', _ok_code=[1])
        except OSError:
            pass

    def is_playing(self):
        settings.load()
        if settings['enable_second_screen'] and get_raspberry_model(get_raspberry_code()) == 'Model 4B':
            return bool(self._run.process.alive or self._run2.process.alive)
        else:
            return bool(self._run.process.alive)
