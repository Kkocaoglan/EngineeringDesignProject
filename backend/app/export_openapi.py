"""API şemasını yazdırır. Kullanım: python -m app.export_openapi > ../docs/openapi.json"""

import json
import sys

from app.main import app

# Türkçe Windows'ta çıktı varsayılan olarak cp1254 + CRLF olur; CI'daki diff kırılmasın diye
# her işletim sisteminde UTF-8 ve LF yazılır.
sys.stdout.reconfigure(encoding="utf-8", newline="\n")
print(json.dumps(app.openapi(), indent=2, ensure_ascii=False, sort_keys=True))
