from enum import Enum


class FingerEvent(Enum):
    FOLD = "fold"
    UNFOLD = "unfold"
    INDEX_STRAIT = "index_strait"
    INDEX_FOLD = "index_fold"
    THUMB_STRAIT = "thumb_strait"
    THUMB_FOLD = "thumb_fold"
    THUMB_INDEX_CLOSE = "thumb_index_close"
    THUMB_INDEX_OPEN = "thumb_index_open"


class HandState:
    def __init__(self):
        self.is_folded = False
        self.push_loaded = False
        self.bullet = 6
        self.push_trigger = False

    @property
    def is_idle(self):
        return not self.push_loaded and not self.push_trigger

    def callback(self, event, data):
        if event == FingerEvent.FOLD:
            self.is_folded = True
        if event == FingerEvent.UNFOLD:
            self.is_folded = False
        if event == FingerEvent.THUMB_FOLD:
            self.push_loaded = True
        if event == FingerEvent.THUMB_STRAIT and (self.bullet < 6) and self.push_loaded:
            self.bullet = 6
            self.push_loaded = False
            print("reloaded!")
        if event == FingerEvent.INDEX_FOLD and (self.bullet > 0) and not self.push_trigger:
            self.push_trigger = True
        if event == FingerEvent.INDEX_STRAIT and self.push_trigger:
            self.push_trigger = False
            print("shot!")
            self.bullet -= 1

    def on_event(self, event, data):
        self.callback(event, data)

    @property
    def state(self):
        return {
            "is_folded": self.is_folded,
            "push_loaded": self.push_loaded,
            "bullet": self.bullet,
            "push_trigger": self.push_trigger,
            "is_idle": self.is_idle
        }
