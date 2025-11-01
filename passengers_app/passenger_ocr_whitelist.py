import frappe

@frappe.whitelist()
def run_ocr_from_button(name):
    doc = frappe.get_doc("Passenger OCR Reader", name)
    doc.run_ocr()
    return "ok"
