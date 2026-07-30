import re

with open('engine_core/portfolio_os_mri_engine.py', 'r') as f:
    content = f.read()

# Make it import XaiFramework
content = "from engine_core.xai_framework import ExplanationNode, XaiCalculation, XaiEvidence\n" + content

# I will use multi_replace_file_content instead of writing a script, it's simpler.
