import re
import os

filepath = 'frontend/src/WeeklyReviewDashboard.tsx'

if os.path.exists(filepath):
    with open(filepath, 'r') as f:
        content = f.read()

    # Replacements to match CaiPortfolioPage dark theme
    replacements = [
        # Layout backgrounds
        (r'bg-gray-50', r'bg-gray-900'),
        (r'bg-white', r'bg-gray-800'),
        (r'bg-gray-100', r'bg-gray-700'),
        (r'border-gray-100', r'border-gray-700'),
        (r'border-gray-200', r'border-gray-600'),
        
        # Text colors
        (r'text-gray-900', r'text-white'),
        (r'text-gray-800', r'text-gray-100'),
        (r'text-gray-700', r'text-gray-300'),
        (r'text-gray-600', r'text-gray-400'),
        (r'text-gray-500', r'text-gray-400'),
        
        # Specific colored backgrounds that need dark mode adjustments
        (r'bg-indigo-50', r'bg-indigo-900/30'),
        (r'text-indigo-700', r'text-indigo-300'),
        (r'bg-indigo-100', r'bg-indigo-800/50'),
        
        (r'bg-green-50', r'bg-green-900/30'),
        (r'border-green-200', r'border-green-800/50'),
        (r'text-green-800', r'text-green-300'),
        (r'bg-green-100', r'bg-green-900/40'),
        (r'text-green-700', r'text-green-400'),
        
        (r'bg-red-50', r'bg-red-900/30'),
        (r'border-red-100', r'border-red-800/50'),
        (r'text-red-800', r'text-red-300'),
        (r'bg-red-100', r'bg-red-900/40'),
        (r'border-red-200', r'border-red-700/50'),
        (r'text-red-600', r'text-red-400'),
        (r'text-red-700', r'text-red-400'),
        
        (r'bg-blue-100', r'bg-blue-900/40'),
        (r'text-blue-700', r'text-blue-400'),
        
        (r'bg-orange-50', r'bg-orange-900/30'),
        (r'border-orange-100', r'border-orange-800/50'),
        (r'text-orange-800', r'text-orange-300'),
        (r'text-orange-600', r'text-orange-400'),
    ]

    for old, new in replacements:
        content = re.sub(old, new, content)

    # Some manual fixes for shadows which look bad on dark mode
    content = content.replace('shadow-sm', '')
    content = content.replace('shadow-md', 'shadow-xl shadow-black/20')

    with open(filepath, 'w') as f:
        f.write(content)

    print("Theme update complete.")
else:
    print("File not found.")
