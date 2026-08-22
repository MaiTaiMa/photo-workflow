import warnings

import pytest

# Unterdrücke pkg_resources-Warnung aus face_recognition_models
warnings.filterwarnings(
    "ignore",
    message=".*pkg_resources is deprecated.*",
    category=UserWarning,
    module="face_recognition_models",
)
