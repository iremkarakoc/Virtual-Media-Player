'''
The Virtual Media Player refers to the design of a vision-based motion
recognition system for real-time control of video viewing functions on the
Web-based version of YouTube. Users can adjust the sound level, rewind,
forward, pause, and play videos in real time by using hand gestures that
correspond to predefined commands in the system's articulation model. The
system utilizes the Mediapipe library to detect and identify hand gestures,
allowing users to control video playback by showing their hand gestures to
the camera.
'''

import threading
import ctypes
import tkinter as tk
import cv2
import mediapipe as mp
from google.protobuf.json_format import MessageToDict
import keyboard
import pyautogui
import interface


finger_tips = [4, 8, 12, 16, 20]


class Screen:
    '''
    This class includes methods for displaying the image that defines how
    the user will interact with the application, on the computer screen and for
    calculating the positions of two lines on the screen to determine the
    functionalities of the application.
    '''
    def __init__(self, image):
        self.image = image

    def show_image(self):
        '''
        Displays the articulation image on the computer screen in a full-screen
        window for 10 seconds and then closes the window
        '''
        user32 = ctypes.windll.user32
        screen_size = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        root = tk.Tk()
        root.overrideredirect(True)
        root.config(bg="blue", bd=0, highlightthickness=0)
        root.attributes("-transparentcolor", "#FEFCFD")
        root.attributes("-topmost", True)
        tk_image = tk.PhotoImage(file=self.image)
        canvas_widget = tk.Canvas(
            root, bg="#FEFCFD", bd=0, highlightthickness=0,
            width=screen_size[0], height=screen_size[1])
        canvas_widget.pack()
        self.image = canvas_widget.create_image(
            0, 0, image=tk_image, anchor="nw")
        root.after(10000, root.destroy)
        root.mainloop()

    def line_pos(self):
        """
        The function calculates the position of two lines on the screen based
        on the screen size.

        return: the position of two lines on the screen, specifically the
        x-coordinate of the first and second lines, scaled to a resolution of
        640 pixels.
        """
        user32 = ctypes.windll.user32
        screen_size = user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        screen_first_line_x = (screen_size[0]*555)/1920
        screen_second_line_x = (screen_size[0]*1365)/1920
        pos_line1 = (screen_first_line_x*640)/screen_size[0]
        pos_line2 = (screen_second_line_x*640)/screen_size[0]
        return pos_line1, pos_line2


class HandDetection():
    '''
    The HandDetection class uses MediaPipe Hands to detect and track
    hands in an input image, and provides functions to find the hand type
    and finger positions.
    '''

    def __init__(self, static_image_mode=False,
                 max_num_hands=2,
                 model_complexity=1,
                 min_detection_confidence=0.6,
                 min_tracking_confidence=0.6):
        '''
        These parameters are adjustable values that affect the performance of
        hand detection and tracking, and can be tuned to optimize the detection
        and tracking process.

        :param static_image_mode: A boolean value that determines whether the
        detectionshould be optimized for static images or for video frames,
        defaults to False (optional)

        :param max_num_hands: The maximum number of hands to detect in the
        image or video stream,defaults to 2 (optional)

        :param model_complexity: refers to the complexity of the hand detection
        model used. A higher value means a more complex model, which may result
        in better accuracy but slower performance, defaults to 1 (optional)

        :param min_detection_confidence: The minimum confidence score required
        for a hand to be detected in the image

        :param min_tracking_confidence: The minimum confidence value required
        for the hand tracking to be considered successful. If the confidence
        value is lower than this threshold, the hand tracking will be
        considered failed
        '''
        self.static_image_mode = static_image_mode
        self.max_num_hands = max_num_hands
        self.model_complexity = model_complexity
        self.min_detection_confidence = min_detection_confidence
        self.min_tracking_confidence = min_tracking_confidence
        # self.mp_drawing = mp.solutions.drawing_utils
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(self.static_image_mode,
                                         self.max_num_hands,
                                         self.model_complexity,
                                         self.min_detection_confidence,
                                         self.min_tracking_confidence)
        self.result = None

    def find_hands(self, image):
        """
        This function takes an image, flips it, converts it to RGB, and
        processes it to detect hands using the Google Mediapipe library and
        returns the image.

        :param image: The input image on which the hands are to be detected
        :return: the input image after processing it with the
        `self.hands.process()`method.
        """

        # Flipping the input image ensures that it is consistent with the
        # original orientation, allowing the hand detection algorithm to
        # correctly determine the hand type
        image = cv2.cvtColor(cv2.flip(image, 1), cv2.COLOR_BGR2RGB)
        image.flags.writeable = False  # to improve performance
        self.result = self.hands.process(image)
        image.flags.writeable = True
        return image

    def hand_type(self):
        '''
        This function determines the handedness (left or right) of a detected
        hand in an image.

        :return: a string that represents the classification label of the hand,
        which can be "Left" or "Right".
        '''
        left_or_right = None
        if self.result.multi_handedness:
            for hand_handedness in (self.result.multi_handedness):
                handedness_dict = MessageToDict(hand_handedness)
                left_or_right = handedness_dict['classification'][0]['label']
        return left_or_right

    def finger_position(self, image):
        """
        This function takes an image and returns a list of finger positions
        detected inthe image using the MediaPipe library.

        :param image: an image (in the form of a numpy array) on which the
        hand landmarks are detected

        :return: A list of finger positions for the first detected hand in the
        input image. Each finger position is represented as a list containing
        the finger index (1-20 for fingers and 0 for the palm), and the x and y
        coordinates of the finger landmark in the image.
        """
        position_list = []
        if self.result.multi_hand_landmarks is not None:
            my_hand = self.result.multi_hand_landmarks[0]
            for index, landmarks in enumerate(my_hand.landmark):
                height, width, = image.shape[0], image.shape[1]
                coordinate_x, coordinate_y = int(
                    landmarks.x * width), int(landmarks.y * height)
                position_list.append([index, coordinate_x, coordinate_y])
        return position_list


class HandGesture():
    '''This class defines hand commands to control a media player based on
    the position of the fingers.'''

    def __init__(self, o_pos_lst, lines_pos, label):
        """
        This is a class with methods that use hand position data to control
        media player functions such as play/pause, skip forward/backward, and
        adjust volume.

        :param o_pos_lst: A list of tuples representing the positions of the
        fingertips and other landmarks of a hand detected by a hand tracking
        algorithm
        :param lines_pos: The position of the lines on the screen that are used
        as reference points for hand gestures
        :param label: The label parameter is a string that specifies whether
        the hand being detected is the left or right hand
        """
        self.o_pos_lst = o_pos_lst
        self.lines_pos = lines_pos
        self.label = label

    def total_fingers_0(self):
        '''
        This function checks if the hand gesture shown to the camera is a fist
        and if the gesture is positioned in the middle of the computer screen.
        If both conditions are met, it plays or pauses the selected media
        player.
        '''
        if (self.o_pos_lst[9][1] > self.lines_pos[0] and
                self.o_pos_lst[9][1] < self.lines_pos[1]):
            o_media_player.play_pause()

    def total_fingers_1(self):
        '''
        This function only works when all fingers except the index finger touch
        the palm. If the user shows their right hand to the camera and the hand
        is on the right side of the screen, it performs the forward function of
        the media player. Similarly, if the user shows their left hand to the
        camera and the hand is on the left side of the screen, it performs the
        backward function of the media player.
        '''
        if self.o_pos_lst[8][2] < self.o_pos_lst[6][2]:
            if (self.o_pos_lst[8][1] < self.lines_pos[0] and
                    self.label == 'Left'):
                o_media_player.backward()
            if (self.o_pos_lst[8][1] > self.lines_pos[1] and
                    self.label == 'Right'):
                o_media_player.forward()

    def total_fingers_2(self):
        '''
        This function works only when all fingers except the index and middle
        fingers touch the palm. If the user shows their right hand to the
        camera and the hand is on the right side of the screen, it performs
        the volume up function of the media player. Similarly, if the user
        shows their left hand to the camera and the hand is on the left side
        of the screen, it performs the volume down function of the media
        player.
        '''
        if (self.o_pos_lst[12][2] < self.o_pos_lst[10][2] and
                self.o_pos_lst[8][2] < self.o_pos_lst[6][2]):
            if (self.o_pos_lst[9][1] < self.lines_pos[0] and
                    self.label == 'Left'):
                o_media_player.volume_decrease()
            if (self.o_pos_lst[9][1] > self.lines_pos[1] and
                    self.label == 'Right'):
                o_media_player.volume_increase()


media_player_fac = interface.MediaPlayerFactory()
o_media_player_name = input('Enter the name of the media player: ')
o_media_player = media_player_fac.create_media_player(
    o_media_player_name.lower())


def main():
    """
    The main function captures video input, detects hand gestures, and
    performs actions based on the number of fingers detected.
    """
    articulation = Screen("interface.png")
    thread_1 = threading.Timer(3, articulation.show_image)
    thread_1.start()

    # includes first line pos in index 0, second line pos in index 1
    lines_pos_x = articulation.line_pos()

    pyautogui.FAILSAFE = False

    stream = cv2.VideoCapture(0)
    tracking = HandDetection()

    while stream.isOpened():

        success, image = stream.read()
        if success is False:
            break

        if keyboard.is_pressed("q"):
            break

        image = tracking.find_hands(image)
        label = tracking.hand_type()
        o_position_list = tracking.finger_position(image)
        if len(o_position_list) != 0:
            fingers = []
            gesture = HandGesture(o_position_list, lines_pos_x, label)
            for i in range(1, 5):
                if (o_position_list[finger_tips[i]][2] <
                        o_position_list[finger_tips[i]-2][2]):
                    fingers.append(1)
                if (o_position_list[finger_tips[i]][2] >
                        o_position_list[finger_tips[i]-2][2]):
                    fingers.append(0)
            total_fingers = fingers.count(1)

            if total_fingers == 0:
                gesture.total_fingers_0()

            if total_fingers == 1:
                gesture.total_fingers_1()

            if total_fingers == 2:
                gesture.total_fingers_2()


if __name__ == "__main__":
    main()
