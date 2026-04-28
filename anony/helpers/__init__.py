# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


from ._admins import admin_check, can_manage_vc, is_admin, reload_admins
from ._cache import Cache
from ._dataclass import Media, Track
from ._exec import format_exception, meval
from ._inline import Inline
from ._queue import Queue
from ._thumbnails import Thumbnail
from ._utilities import Utilities

buttons = Inline()
cache = Cache("mongodb+srv://debojitex:470mebdS6T9nhLvo@cluster0.sehar.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")
thumb = Thumbnail()
utils = Utilities()
