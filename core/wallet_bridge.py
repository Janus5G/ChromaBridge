import os
import json
import hashlib
import time
import struct
from typing import Dict, Any, Optional, List

from chromaplex_os.api import ChromaPlex
from chromaplex_os.facet_crystal import FacetAddress
from .address_registry import get_address_registry


class InternetIdentityWalletBridge:
    """
    Bro til ChromaPlex Wallet – med Address Registry og KORREKT format.
    """

    def __init__(self, wallet_url: Optional[str] = None, principal: Optional[str] = None):
        self.principal = principal
        self.cx = ChromaPlex(num_crystals=1)
        self.stored_addresses = []
        self._authenticated = True
        self._facet_counter = 0
        self.registry = get_address_registry()  # 🔥 BEHOLDER REGISTRY!

    def set_principal(self, principal: str):
        self.principal = principal

    def simuler_internet_identity_login(self) -> bool:
        return True

    def _find_available_position(self) -> tuple:
        facets = list(range(1, 58))
        colours = ["rød", "grøn", "blå", "violet", "uv"]
        
        for attempt in range(100):
            facet_idx = self._facet_counter % len(facets)
            colour_idx = (self._facet_counter // len(facets)) % len(colours)
            
            facet = facets[facet_idx]
            colour = colours[colour_idx]
            self._facet_counter += 1
            
            addr = FacetAddress(0, facet, colour, 0)
            if self.cx.ledger.is_address_available(addr.key):
                return facet, colour
        
        raise RuntimeError("Ingen ledig position fundet efter 100 forsøg!")

    def signer_og_send_bin_klynge(self, bin_fil_sti: str) -> Dict[str, Any]:
        print(f"📤 [WalletBridge] Behandler binær fil: {bin_fil_sti}")

        try:
            with open(bin_fil_sti, 'rb') as f:
                bin_data = f.read()

            if len(bin_data) < 16:
                raise ValueError(f"Bin-fil for kort ({len(bin_data)} bytes)")

            magic = bin_data[:4].decode('ascii', errors='ignore')
            if magic != "CPX2":
                raise ValueError(f"Ugyldig magic header: {magic} – forventer 'CPX2'")

            timestamp = struct.unpack('<d', bin_data[4:12])[0]
            data_len = struct.unpack('<I', bin_data[12:16])[0]
            json_bytes = bin_data[16:16+data_len]
            json_data = json.loads(json_bytes.decode('utf-8'))

            value = json_data.get("value", 0)
            representation = json_data.get("representation", "")
            original_source = json_data.get("source_address", "C0:F5:system:D0")

            base, exponent, rest = self._parse_representation(representation, value)

            facet, colour = self._find_available_position()
            print(f"📍 Bruger ledig position: facette {facet}, farve {colour}")

            addr = self.cx.store(facet=facet, colour=colour.upper(), value=value, base=base)

            # 🔥 BRUG REGISTRY TIL UNIK ADRESSE
            unique_id = self.registry.generate_unique_address()
            # 🔥 OMDAN TIL KORREKT FORMAT: C0:F{facet}:{colour}:D0
            # (Brug den unikke ID til at lave en unik adresse i det rigtige format)
            source_address = f"C0:F{facet}:{colour}:D{self.registry._counter}"

            self.stored_addresses.append({
                "fil": os.path.basename(bin_fil_sti),
                "address": addr,
                "value": value,
                "base": base,
                "exponent": exponent,
                "rest": rest,
                "source_address": source_address,
                "original_source": original_source,
                "representation": representation,
                "facet": facet,
                "colour": colour
            })

            print(f"✅ [WalletBridge] Gemt {value} på {source_address}")
            return {"status": "stored", "address": addr, "value": value, "facet": facet, "colour": colour}

        except Exception as e:
            print(f"❌ [WalletBridge] Fejl: {str(e)}")
            raise

    def afslut_og_send(self) -> List[Dict[str, Any]]:
        if not self.stored_addresses:
            print("⚠️ [WalletBridge] Ingen data at sende.")
            return []

        print("📸 [WalletBridge] Udfører linse-aflæsning for hver gemt facet...")
        
        for entry in self.stored_addresses:
            facet = entry.get("facet", 5)
            print(f"   Aflæser facette {facet}...")
            self.cx.lens_capture(facet=facet)
        
        print("⛓️ [WalletBridge] Sender til blockchain...")
        payloads = self.cx.lens_to_chain()

        results = []
        for i, payload in enumerate(payloads):
            if i < len(self.stored_addresses):
                entry = self.stored_addresses[i]
                
                payload["value"] = entry.get("value", 0)
                payload["representation"] = entry.get("representation", "")
                payload["source_address"] = entry.get("source_address", "C0:F5:system:D0")
                payload["base"] = entry.get("base", 2)
                payload["exponent"] = entry.get("exponent", 0)
                payload["rest"] = entry.get("rest", 0)
                
                hash_string = f"{payload['source_address']}:{payload['value']}:{payload['base']}:{payload['exponent']}:{payload['rest']}"
                extraction_hash = hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
                
                print(f"🔑 Input-streng: {hash_string}")
                
                payload["extraction_hash"] = extraction_hash
                
                results.append({
                    "fil": entry["fil"],
                    "payload": payload,
                    "address": entry["address"]
                })
            else:
                results.append({"payload": payload})

        print(f"✅ [WalletBridge] {len(results)} entries sendt til wallet.")
        return results

    def _parse_representation(self, rep: str, value: int) -> tuple:
        if not rep:
            return 2, 0, 0

        rep = rep.replace(" ", "")
        rest = 0

        if "+" in rep:
            power_part, rest_str = rep.split("+", 1)
            try:
                rest = int(rest_str)
            except ValueError:
                rest = 0
        else:
            power_part = rep

        if "^" in power_part:
            base_str, exp_str = power_part.split("^", 1)
            try:
                base = int(base_str)
                exponent = int(exp_str)
            except ValueError:
                base, exponent = 2, 0
        else:
            target = value - rest
            if target > 0:
                for base in [2, 3, 5, 7, 10]:
                    exp = 0
                    temp = 1
                    while temp <= target:
                        if temp == target:
                            return base, exp
                        temp *= base
                        exp += 1
            base, exponent = 2, 0

        return base, exponent, rest