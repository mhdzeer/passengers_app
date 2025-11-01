frappe.ui.form.on('Passenger OCR Reader', {
        refresh: function(frm) {
            if (frm.doc.docstatus === 0) {
                frm.add_custom_button(__('Run OCR'), function() {
                    frappe.call({
                        method: 'passengers_app.passengers_app.passenger_ocr_whitelist.run_ocr_from_button',
                        args: { name: frm.doc.name },
                        callback: function(r) {
                            frm.reload_doc();
                            frappe.msgprint(__('OCR completed'));
                        }
                    });
                });
            }
        }
    });
