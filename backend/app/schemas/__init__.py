"""按业务模块拆分的 schemas，保留稳定的包级导入接口。"""

from .auth import Credentials
from .auth import UserResponse
from .auth import AuthResponse
from .avatar import AvatarPreferenceUpdate
from .avatar import AvatarPreferenceResponse
from .session import CreateSession
from .session import SubmitTurn
from .speech import SpeechStatus, TranscriptionResponse

__all__ = ['Credentials', 'UserResponse', 'AuthResponse', 'AvatarPreferenceUpdate', 'AvatarPreferenceResponse', 'CreateSession', 'SubmitTurn', 'SpeechStatus', 'TranscriptionResponse']
