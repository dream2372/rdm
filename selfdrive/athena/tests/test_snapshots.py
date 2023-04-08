#!/usr/bin/env python3

from selfdrive.athena.athenad import takeSnapshot

ret = takeSnapshot()
assert(ret is not None)