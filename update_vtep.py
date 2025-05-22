#!/usr/bin/env python3
"""Backward compatible CLI entry point for updating Arista VTEP flood lists."""

from arista_vtep_update import main
import sys

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
