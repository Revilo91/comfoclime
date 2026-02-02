#!/usr/bin/env python3
"""Standalone script to record API responses from a real ComfoClime device.

Usage:
    python tests/record_device_responses.py [--ip 10.0.2.27]

This will record all API responses to tests/recorded_responses/ for use
in offline testing.
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.conftest_real_device import RESPONSES_DIR, record_all_responses


async def main():
    parser = argparse.ArgumentParser(
        description="Record ComfoClime API responses for testing"
    )
    parser.add_argument(
        "--ip",
        default="10.0.2.27",
        help="IP address of the ComfoClime device (default: 10.0.2.27)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("ComfoClime Response Recorder")
    print("=" * 60)

    await record_all_responses(args.ip, RESPONSES_DIR)


if __name__ == "__main__":
    asyncio.run(main())
