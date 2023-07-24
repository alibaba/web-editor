# coding: utf-8
#

import enum

class PlatformEnum(str, enum.Enum):
    AndroidUIAutomator2 = "Android"
    AndroidADB = "AndroidADB"
    IOS = "iOS"
