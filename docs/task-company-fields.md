# Project task fields at creation

Project administrators can configure ordinary scalar custom Task fields and require
values in selected task statuses. The full **New task** form shows configured custom
fields the creator can both read and write. Required fields are marked for the selected
status, including a field that would otherwise be hidden from the optional form.

The creation API accepts `field_values` as a JSON object alongside normal Task creation
arguments. Keys must be configured `custom_*` Task fields that are writable and
readable for the caller. The field must be an editable, unmasked supported scalar
field. Standard arguments such as `subject`, `project`, `priority`, dates and estimates
remain separate; metadata such as owner cannot be overridden through `field_values`.
Unsupported keys and non-scalar/non-finite values are rejected. Native Task validation
still checks field choices, required statuses and other invariants on the first save.

Native custom-field defaults are offered in the full form. Changing projects resets the
custom-field values, and a successful creation clears them for the next task. Inline
creation stays title-only; if the starting status requires a value, its error directs
the user to the full New task form. A creator who cannot access an initially required
field must ask a project administrator to correct the field permissions.

## Recurring template boundary

Scheduled templates currently store the native recurring fields: subject, description,
priority, type, assignee and schedule. They do not store project custom-field values.
Creating, updating or enabling a template is rejected when its actual initial task
status requires custom fields or approval. This check runs before template persistence,
so an unsuccessful initial generation does not leave an orphan template for this case.
Supported native field requirements are checked against the template before saving.

Create a one-off task when those initial requirements apply, or choose a compatible
project start status. A future custom-field template payload needs its own schema and
scheduler implementation; the UI does not claim that it is supported now.
