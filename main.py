#!/usr/bin/env python3

import asyncio
import collections
from contextlib import suppress
import copy
import math
import numpy as np
import os
import random
import sys
import subprocess

import testRunner
import runner

async def main():
    await runner.trainAndPlay()

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
