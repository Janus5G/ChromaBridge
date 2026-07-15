import os
import struct
import json
from datetime import datetime

class ChromaplexBinaryCompiler:
    def __init__(self, output_mappe):
        self.output_mappe = output_mappe
        if not os.path.exists(output_mappe):
            os.makedirs(output_mappe)

    def log(self, besked):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [Compiler] {besked}")

    def kompiler_til_bin(self, fil_stier):
        kompilerede_filer = []
        MAGIC_HEADER = b"CPX2"

        for sti in fil_stier:
            navn = os.path.basename(sti).replace(".json", ".bin")
            maal_sti = os.path.join(self.output_mappe, navn)

            with open(sti, "r", encoding="utf-8") as f:
                data = json.load(f)

            raw_bytes = json.dumps(data).encode("utf-8")
            datalaengde = len(raw_bytes)

            # 🔑 BRUG DOUBLE (d) – matcher wallet_bridge
            tidsstempel = datetime.now().timestamp()
            header_pakke = struct.pack("<4s d I", MAGIC_HEADER, tidsstempel, datalaengde)

            with open(maal_sti, "wb") as bin_f:
                bin_f.write(header_pakke)
                bin_f.write(raw_bytes)

            self.log(f"🔒 Kompileret: {os.path.basename(sti)} -> {navn} ({datalaengde} bytes)")
            kompilerede_filer.append(maal_sti)

        return kompilerede_filer