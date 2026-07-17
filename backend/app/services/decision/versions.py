"""Decision Engine version constants.

Used for validating cache.json. Any changes to logic or models should
bump these versions to invalidate stored decisions and force rebuild.
"""

DECISION_VERSION = "v1"
SCHEMA_VERSION = "v1"
GENERATOR_VERSION = "devmind-decision-8.9"
