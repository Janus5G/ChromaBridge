import os
import json
import hashlib
import time
import sqlite3
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse

from .address_registry import get_address_registry

try:
    import requests
except ImportError:
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class DatabaseAnalyzer:
    def __init__(self, output_dir: str = "test_ingestion_input/database"):
        self.output_dir = output_dir
        self.session = None
        self.registry = get_address_registry()  # 🔑 Brug address registry
        self._init_session()

    def _init_session(self):
        if requests:
            self.session = requests.Session()
            self.session.headers.update({
                'User-Agent': 'ChromaBridge/1.0'
            })

    def convert_to_chromaplex_format(self, value: int) -> Dict:
        """Konverter en værdi til Chromaplex-format med UNIK source_address."""
        for base in [2, 3, 5, 7, 10]:
            exp = 0
            while base ** exp <= value:
                exp += 1
            exp -= 1
            rest = value - (base ** exp)
            if rest >= 0 and rest < value:
                return {
                    "value": value,
                    "representation": f"{base}^{exp} + {rest}",
                    "source_address": self.registry.generate_unique_address()  # 🔑 UNIK
                }
        return {
            "value": value,
            "representation": f"2^0 + {value}",
            "source_address": self.registry.generate_unique_address()  # 🔑 UNIK
        }

    def migrate_to_chromabridge(self, url: str) -> Dict[str, Any]:
        """Analyser en URL og gem data som JSON-filer med UNIKKE adresser."""
        analysis = self.analyze_from_url(url)
        if analysis["status"] != "success":
            return analysis

        saved_files = []

        if analysis["type"] in ["json", "json_file"] and "sample" in analysis:
            sample = analysis["sample"]
            if isinstance(sample, dict):
                for key, val in sample.items():
                    if isinstance(val, (int, float)):
                        entry = self.convert_to_chromaplex_format(int(val))
                        filename = f"migrated_{key}_{int(time.time())}.json"
                        filepath = os.path.join(self.output_dir, filename)
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(entry, f, indent=2, ensure_ascii=False)
                        saved_files.append(filepath)

        return {
            "status": "success",
            "source_url": url,
            "type": analysis["type"],
            "total_entries": len(saved_files),
            "saved_files": saved_files,
            "output_dir": self.output_dir
        }

    def analyze_from_url(self, url: str, depth: int = 1) -> Dict[str, Any]:
        """Analyser en URL og returner struktur."""
        self.source_url = url

        try:
            response = self.session.get(url, timeout=10)
            content_type = response.headers.get("content-type", "").lower()

            if 'application/json' in content_type or url.endswith(('.json', '.geojson')):
                data = response.json()
                return {
                    "status": "success",
                    "type": "json",
                    "url": url,
                    "sample": data if isinstance(data, dict) else {"data": data[:10]},
                    "total_records": len(data) if isinstance(data, list) else 1,
                    "output_dir": self.output_dir
                }

            if BeautifulSoup and 'text/html' in content_type:
                soup = BeautifulSoup(response.text, "html.parser")
                return {
                    "status": "success",
                    "type": "html",
                    "url": url,
                    "metadata": {
                        "title": soup.title.string if soup.title else None,
                        "links": len(soup.find_all("a")),
                        "images": len(soup.find_all("img")),
                        "tables": len(soup.find_all("table"))
                    },
                    "output_dir": self.output_dir
                }

            return {"status": "error", "message": f"Ukendt format: {content_type}"}

        except Exception as e:
            return {"status": "error", "message": str(e)}

    def _save_data(self, name: str, data: Any) -> str:
        """Gem data som JSON-fil (bruges af interne metoder)."""
        os.makedirs(self.output_dir, exist_ok=True)
        filename = f"{name}_{int(time.time())}.json"
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str, ensure_ascii=False)
        return filepath