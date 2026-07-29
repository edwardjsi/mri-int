import os, glob, re

frontend_dir = "frontend/src"
files = glob.glob(f"{frontend_dir}/Cai*.tsx")

for filepath in files:
    with open(filepath, "r") as f:
        content = f.read()

    # Skip if fetch is not used with /api/
    if "fetch(\"/api" not in content and "fetch('/api" not in content and "fetch(`/api" not in content:
        continue

    # Update imports
    if "getAuthHeaders" in content and "apiFetch" not in content:
        content = content.replace("import { getAuthHeaders } from './api';", "import { getAuthHeaders, apiFetch } from './api';")
    elif "apiFetch" not in content:
        if "import { api }" in content:
            content = content.replace("import { api } from './api';", "import { api, apiFetch } from './api';")
        else:
            content = "import { apiFetch } from './api';\n" + content

    # Replace fetch with apiFetch and remove /api
    content = re.sub(r"fetch\((['\"`])/api/", r"apiFetch(\g<1>/", content)
    
    # Now we need to remove the res.json() calls because apiFetch already parses it.
    # Pattern: 
    # const res = await apiFetch(...)
    # if (!res.ok) { ... await res.json() ... }
    # const data = await res.json()
    
    # Let's fix them manually for safety, but we can do simple substitutions for common patterns
    content = content.replace("const res = await apiFetch", "const data = await apiFetch")
    content = content.replace("const data = await res.json();\n      setPortfolio(data);", "setPortfolio(data);")
    content = content.replace("const json = await res.json();\n        setData(json);", "setData(data);")
    content = content.replace("const json = await res.json();\n        setData(json);", "setData(data);")
    content = content.replace("if (json.current_price) setPrice(json.current_price);", "if (data.current_price) setPrice(data.current_price);")
    content = content.replace("const data = await res.json();\n        setData(data);", "setData(data);")

    # In CaiPortfolioPage.tsx:
    content = content.replace("const err = await res.json().catch(() => ({ detail: 'Failed to parse error response' }));", "")
    content = content.replace("throw new Error(err.detail || 'Failed to add position');", "")
    content = content.replace("throw new Error(err.detail || 'Failed to add tranche');", "")
    content = content.replace("if (!res.ok) {", "")
    content = content.replace("if (!data.ok) {", "")
    
    # We will write the file, then we can review manually if there are syntax errors.
    with open(filepath, "w") as f:
        f.write(content)

print("Replacement complete. Please review the diffs.")
