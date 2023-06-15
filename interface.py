'''Factory pattern file created for the application to run on many media
players'''
import abc
import time
import pyautogui


class Command(metaclass=abc.ABCMeta):
    '''
    This class defines a set of abstract methods for controlling a media
    player.
    '''
    def play_pause(self):
        pass

    def volume_decrease(self):
        pass

    def volume_increase(self):
        pass

    def forward(self):
        pass

    def backward(self):
        pass


class Youtube(Command):

    def play_pause(self):
        pyautogui.press('Space')
        time.sleep(0.7)

    def volume_decrease(self):
        pyautogui.press('Down')
        time.sleep(0.7)

    def volume_increase(self):
        pyautogui.press('Up')
        time.sleep(0.7)

    def forward(self):
        pyautogui.press('Right')
        time.sleep(0.7)

    def backward(self):
        pyautogui.press('Left')
        time.sleep(0.7)


class MediaPlayerFactory():
    def create_media_player(self, media_ply_name):
        '''The function that enables the user-selected media player to be
        activated in the application'''
        name = media_ply_name
        if name == 'youtube':
            return Youtube()
        else:
            raise ValueError(
                'The application does not work on this media player!')
