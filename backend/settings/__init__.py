# -*- coding: utf-8 -*-
"""
Created on June 15 2022

@author:
    Wesley Eliel MONTCHO, alias DevBackend7
"""

from .base import *
from .smtp import *

environment = os.environ.get("DEV_ENV")

if environment == "dev":  # assuming value of DEV_ENV is 'development'
    from .dev import *
else:
    from .prod import *
