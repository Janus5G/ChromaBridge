"""
core/address_registry.py – Log og generér unikke source_address til Chromaplex.

Holder styr på alle brugte adresser på tværs af kørsler, så du aldrig får
"source_address eksisterer allerede" fejlen igen.
"""

import os
import json
import hashlib
import time
from typing import Optional, Set, List

class AddressRegistry:
    """
    Registry til at generere og logge unikke source_address.
    Gemmer brugte adresser i used_addresses.json i projektets rod.
    """

    def __init__(self, registry_file: str = "used_addresses.json"):
        self.registry_file = registry_file
        self.used_addresses: Set[str] = set()
        self._counter = 0
        self._load_registry()

    def _load_registry(self) -> None:
        """Indlæs tidligere brugte adresser fra fil."""
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.used_addresses = set(data.get("used_addresses", []))
                    self._counter = data.get("counter", 0)
                print(f"📋 [AddressRegistry] Indlæst {len(self.used_addresses)} brugte adresser")
            except Exception as e:
                print(f"⚠️ [AddressRegistry] Kunne ikke indlæse registry: {e}")
                self.used_addresses = set()
                self._counter = 0

    def _save_registry(self) -> None:
        """Gem brugte adresser til fil."""
        try:
            with open(self.registry_file, "w", encoding="utf-8") as f:
                json.dump({
                    "used_addresses": list(self.used_addresses),
                    "counter": self._counter,
                    "last_updated": time.time()
                }, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ [AddressRegistry] Kunne ikke gemme registry: {e}")

    def generate_unique_address(self, prefix: str = "C0:F5") -> str:
        """
        Generér en ny unik source_address.
        Format: C0:F5:{unique_hash}:D{counter}
        """
        self._counter += 1
        max_attempts = 1000
        
        for attempt in range(max_attempts):
            # Brug counter + timestamp + random for at sikre unikhed
            unique_id = hashlib.md5(f"{time.time()}{self._counter}{attempt}".encode()).hexdigest()[:8]
            address = f"{prefix}:{unique_id}:D{self._counter}"
            
            if address not in self.used_addresses:
                self.used_addresses.add(address)
                self._save_registry()
                return address
        
        raise RuntimeError(f"Kunne ikke generere unik adresse efter {max_attempts} forsøg")

    def mark_as_used(self, address: str) -> None:
        """Markér en adresse som brugt (hvis den ikke allerede er registreret)."""
        if address and address not in self.used_addresses:
            self.used_addresses.add(address)
            self._save_registry()

    def is_used(self, address: str) -> bool:
        """Tjek om en adresse allerede er brugt."""
        return address in self.used_addresses

    def get_used_count(self) -> int:
        """Returnér antal brugte adresser."""
        return len(self.used_addresses)

    def reset(self) -> None:
        """Nulstil registry (brug med forsigtighed!)."""
        self.used_addresses = set()
        self._counter = 0
        self._save_registry()
        print("🗑️ [AddressRegistry] Registry er nulstillet")


# ---------- Singleton instance ----------
_registry_instance: Optional[AddressRegistry] = None

def get_address_registry() -> AddressRegistry:
    """Hent eller opret singleton-instans af AddressRegistry."""
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = AddressRegistry()
    return _registry_instance