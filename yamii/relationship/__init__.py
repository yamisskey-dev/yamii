"""
関係性記憶システム
対話を通じて相手に適応・成長し続けるシェイプシフター型AIパートナー
"""

from .models import (
    RelationshipPhase,
    EpisodeType,
    ToneLevel,
    DepthLevel,
    RelationshipState,
    Episode,
    AdaptiveProfile,
)
from .memory_system import RelationshipMemorySystem, get_relationship_memory
from .episode_manager import EpisodeManager
from .phase_manager import PhaseManager
from .adaptive_profile import AdaptiveProfileManager
from .prompt_generator import RelationshipPromptGenerator

__all__ = [
    "RelationshipPhase",
    "EpisodeType",
    "ToneLevel",
    "DepthLevel",
    "RelationshipState",
    "Episode",
    "AdaptiveProfile",
    "RelationshipMemorySystem",
    "get_relationship_memory",
    "EpisodeManager",
    "PhaseManager",
    "AdaptiveProfileManager",
    "RelationshipPromptGenerator",
]
