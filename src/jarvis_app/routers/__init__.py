# routers package — re-export sub-modules for convenient import
from . import history as history
from . import knowledge as knowledge
from . import settings as settings
from . import smartprep as smartprep
from . import training as training

__all__ = ["history", "knowledge", "settings", "smartprep", "training"]
