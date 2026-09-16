(() => {
  const root = document.querySelector('.public-intake')
  const form = document.getElementById('public-request-form')
  const status = document.getElementById('request-status')
  const error = document.getElementById('request-error')
  const key = new URLSearchParams(window.location.search).get('key') || ''
  async function request(method, values, post = false) {
    const options = post ? { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Frappe-CSRF-Token': root.dataset.csrf }, body: JSON.stringify(values) } : {}
    const response = await fetch(`/api/method/pulse.api.public_intake.${method}${post ? '' : '?' + new URLSearchParams(values)}`, options)
    if (!response.ok) {
      if (response.status === 429) throw new Error('Too many requests. Wait a minute and try again.')
      throw new Error(post ? 'Your request could not be submitted. Your text is saved here; try again.' : 'This request form is unavailable. Ask the team for a current link.')
    }
    return (await response.json()).message
  }
  request('get_form', { key }).then(data => {
    document.getElementById('request-heading').textContent = data.title
    document.getElementById('request-instructions').textContent = data.description
    status.textContent = ''
    form.hidden = false
  }).catch(e => { status.textContent = e.message })
  form.addEventListener('submit', async event => {
    event.preventDefault()
    const button = form.querySelector('button')
    if (button.disabled) return
    button.disabled = true
    button.textContent = 'Submitting…'
    error.textContent = ''
    try {
      await request('submit', { key, title: form.elements.title.value.trim(), description: form.elements.description.value }, true)
      form.hidden = true
      status.textContent = 'Your request has been submitted for review. Thank you.'
    } catch (e) { error.textContent = e.message }
    finally { button.disabled = false; button.textContent = 'Submit request' }
  })
})()
