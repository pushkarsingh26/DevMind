# Core versions
COLLABORATION_VERSION = "v1"
WORKSPACE_SCHEMA_VERSION = "v1"
CONSENSUS_VERSION = "v1"

# Ruleset versions — changing any rule set must bump its version
# so that manifest validation invalidates any cached collaboration data
# produced under the old rules.
REVIEW_RULESET_VERSION = "v1"   # review_engine.py — validation thresholds and logic
EVIDENCE_RULESET_VERSION = "v1"   # evidence_manager.py — quality scoring weights
CONFLICT_RULESET_VERSION = "v1"   # conflict_resolver.py — detection and resolution rules
