# Version check bypass kar diya taake metadata error na aye
__version__ = "1.0.0"

from .tts import ChatterboxTTS
from .vc import ChatterboxVC
from .mtl_tts import ChatterboxMultilingualTTS, SUPPORTED_LANGUAGES

# FIX: handler.py ko crash se bachanay kay liye alias bana diya
Chatterbox = ChatterboxTTS