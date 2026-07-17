"""Reasoning Engine version constants.

All three version strings must match the stored cache.json values for the
cache to be considered valid. A repository_hash mismatch also invalidates.
"""

REASONING_VERSION  = "v1"   # bump when engine logic changes
SCHEMA_VERSION     = "v1"   # bump when model field structure changes
GENERATOR_VERSION  = "devmind-reasoning-8.8"
