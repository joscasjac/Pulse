/** Bind rich-editor uploads to the saved parent using Frappe UI's `private`
 * option. `is_private` is the HTTP field, not a useFileUpload option.
 */
import { __ } from '../translation.js'

export function createPrivateEditorUpload(upload, reference) {
  return async file => {
    const { doctype, docname } = reference() || {}
    if (!['Task', 'Pulse Document'].includes(doctype) || typeof docname !== 'string' || !docname.trim()) {
      throw new Error(__('Save the task or create the page before uploading images or files.'))
    }
    const result = await upload(file, { doctype, docname, private: true })
    if (!result || Number(result.is_private) !== 1 || typeof result.file_url !== 'string' || !result.file_url || result.file_url.startsWith('/files/')) {
      throw new Error(__('The upload did not return a private attachment. The image was not inserted.'))
    }
    return result
  }
}
