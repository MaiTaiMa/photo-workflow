"""Automationsmodi (Master-Prompt v13, 4.1)."""
from enum import Enum

class AutomationMode(str, Enum):
    OFF = "off"
    SHADOW = "shadow"
    ASSISTED = "assisted"
    AUTO_PHASE1 = "auto_phase1"
    AUTO_PHASE2 = "auto_phase2"
    FULL_AUTO = "full_auto"

def can_auto_predict(mode: AutomationMode) -> bool:
    return mode in (AutomationMode.SHADOW, AutomationMode.ASSISTED,
                    AutomationMode.AUTO_PHASE1, AutomationMode.AUTO_PHASE2, AutomationMode.FULL_AUTO)

def can_auto_decide(mode: AutomationMode) -> bool:
    return mode in (AutomationMode.AUTO_PHASE1, AutomationMode.AUTO_PHASE2, AutomationMode.FULL_AUTO)

def can_auto_phase2(mode: AutomationMode) -> bool:
    return mode in (AutomationMode.AUTO_PHASE2, AutomationMode.FULL_AUTO)
