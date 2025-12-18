
# fix_warnings.py
import os
import re

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix use_container_width
    content = content.replace('use_container_width=True', "width='stretch'")
    content = content.replace('use_container_width=False', "width='content'")
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Fixed: {filepath}")

# Fix all UI files
files_to_fix = [
    'ui_billing.py',
    'ui_reports.py',
    'ui_customers.py',
    'ui_products.py',
    'ui_stock.py',
    'ui_company.py'
]

for filename in files_to_fix:
    if os.path.exists(filename):
        fix_file(filename)

print("\n🎉 All warnings fixed!")
