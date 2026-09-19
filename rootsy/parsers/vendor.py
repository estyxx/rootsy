"""Vendor extension tags more than one record parser reads."""

# Tags that name the record rather than the person or family it describes: an
# exporter's own record number and the stamp it writes when a record changes.
# Every record that carries them keeps them in a `vendor` dict of its own.
RECORD_TAGS = frozenset({"RIN", "_UPD"})
