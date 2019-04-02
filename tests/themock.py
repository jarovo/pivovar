try:
    from unittest.mock import MagicMock, patch
except ImportError:
    from mock import MagicMock, patch

# Avoid the falke8 complains about not used imports.
MagicMock
patch
