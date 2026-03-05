#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速运行脚本
双击运行或在终端执行：python3 run.py
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from main import main

if __name__ == "__main__":
    main()
