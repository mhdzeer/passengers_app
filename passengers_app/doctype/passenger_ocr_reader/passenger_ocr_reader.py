# -*- coding: utf-8 -*-
    from __future__ import unicode_literals
    import frappe
    import pytesseract
    from frappe.model.document import Document
    from PIL import Image
    import io
    import re

    class PassengerOCRReader(Document):
        def after_insert(self):
            # auto-run OCR after insertion
            try:
                if self.image:
                    self.run_ocr()
            except Exception as e:
                frappe.log_error(f"PassengerOCR: after_insert error: {e}")

        def run_ocr(self):
            # fetch file content (works with File doc)
            try:
                file_doc = frappe.get_doc("File", {"file_url": self.image})
                file_content = file_doc.get_content()
            except Exception:
                # fallback: try direct path
                file_content = None
                try:
                    f = frappe.get_site_path("public", self.image.lstrip("/"))
                    with open(f, "rb") as fh:
                        file_content = fh.read()
                except Exception as e:
                    frappe.log_error(f"PassengerOCR: could not get file content: {e}")
                    return

            try:
                img = Image.open(io.BytesIO(file_content))
            except Exception as e:
                frappe.log_error(f"PassengerOCR: Pillow cannot open image: {e}")
                return

            # run tesseract for Arabic+English - adjust languages per your install
            try:
                text = pytesseract.image_to_string(img, lang="ara+eng")
            except Exception:
                # fallback to default lang
                text = pytesseract.image_to_string(img)

            self.recognized_text = text
            self.save(ignore_permissions=True)

            data = self.extract_passenger_data(text)

            # create Passenger record
            try:
                passenger = frappe.get_doc({
                    "doctype": "Passenger",
                    "first_name": data.get("first_name") or data.get("given_name") or "",
                    "last_name": data.get("last_name") or data.get("surname") or "",
                    "cpr_number": data.get("cpr_number") or "",
                    "passport_number": data.get("passport_number") or "",
                    "nationality": data.get("nationality") or "",
                    "date_of_birth": data.get("date_of_birth") or "",
                    "gender": data.get("gender") or "",
                    "photo": self.image
                })
                passenger.insert(ignore_permissions=True)
                self.passenger = passenger.name
                self.save(ignore_permissions=True)
            except Exception as e:
                frappe.log_error(f"PassengerOCR: error creating passenger: {e}")

        def extract_passenger_data(self, text):
            # naive extraction - tune patterns to your card layout
            data = {}

            # CPR: 9 digits
            m = re.search(r"(\\d{9})", text)
            if m: data["cpr_number"] = m.group(1)

            # Passport: alphanumeric 6-9 chars (naive)
            m = re.search(r"\\b([A-Z0-9]{6,9})\\b", text)
            if m: data["passport_number"] = m.group(1)

            # Date formats like DD/MM/YYYY
            m = re.search(r"(\\d{2}/\\d{2}/\\d{4})", text)
            if m: data["date_of_birth"] = m.group(1)
            else:
                m = re.search(r"(\\d{4}-\\d{2}-\\d{2})", text)
                if m: data["date_of_birth"] = m.group(1)

            # Name heuristics
            m = re.search(r"Name[:\\-\\s]*([A-Za-z\\u0600-\\u06FF\\s]+)", text, re.IGNORECASE)
            if m:
                full = m.group(1).strip()
                parts = full.split()
                if len(parts) >= 2:
                    data["first_name"] = parts[0]
                    data["last_name"] = " ".join(parts[1:])
                else:
                    data["first_name"] = full

            up = text.upper()
            if "MALE" in up or " M " in up:
                data["gender"] = "Male"
            elif "FEMALE" in up or " F " in up:
                data["gender"] = "Female"

            m = re.search(r"Nationality[:\\-\\s]*([A-Za-z\\u0600-\\u06FF\\s]+)", text, re.IGNORECASE)
            if m:
                data["nationality"] = m.group(1).strip()

            return data
