# core/ide_extension.py
import os
import json
from datetime import datetime

class ChromaplexIDEExtension:
    def __init__(self, input_mappe):
        self.input_mappe = input_mappe
        self.godkendte_data = []

    def log(self, besked):
        print(f"[{datetime.now().strftime('%H:%M:%S')}] [IDE-Extension] {besked}")

    def importer_og_valider(self):
        self.log(f"🚀 Starter ingestion af rå data fra: {self.input_mappe}")
        if not os.path.exists(self.input_mappe):
            os.makedirs(self.input_mappe)
            self.log(f"⚠️ Mappen var tom. Oprettet '{self.input_mappe}'. Læg filer heri.")
            return False

        # 🔥 SCAN REKURSIVT – alle undermapper (f.eks. /database)
        for rod, _, filer in os.walk(self.input_mappe):
            for fil in filer:
                fuld_sti = os.path.join(rod, fil)
                if fil.endswith(".json"):
                    if self._valider_json_og_aktiver(fuld_sti):
                        self.godkendte_data.append(fuld_sti)

        self.log(f"📋 Validering fuldført. {len(self.godkendte_data)} kilde-filer godkendt til binær kompilering.")
        return True

    def _valider_json_og_aktiver(self, fil_sti):
        try:
            with open(fil_sti, "r", encoding="utf-8") as f:
                data = json.load(f)

            # Konceptuel scanning efter font- og sti-fejl for at beskytte caffeine.ai
            indhold_streng = json.dumps(data)
            if "url(" in indhold_streng and not "http" in indhold_streng:
                self.log(f"⚠️ Advarsel i {os.path.basename(fil_sti)}: Relativ font/aktiv-sti detekteret!")

            return True
        except Exception as e:
            self.log(f"❌ Korrupt fil afvist: {os.path.basename(fil_sti)} - Fejl: {str(e)}")
            return False