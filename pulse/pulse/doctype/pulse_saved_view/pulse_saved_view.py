import json
import frappe
from frappe.model.document import Document
from pulse.api.views import configuration


class PulseSavedView(Document):
    def validate(self):
        original_owner = frappe.db.get_value(self.doctype, self.name, 'owner') if not self.is_new() else frappe.session.user
        if original_owner != frappe.session.user or self.owner != original_owner:
            frappe.throw('Only the view owner can change it.', frappe.PermissionError)
        self.title = (self.title or '').strip()
        if not self.title:
            frappe.throw('Give this view a name.')
        self.configuration = json.dumps(configuration(self.configuration))
