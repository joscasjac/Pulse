import { createApp } from 'vue'
import {
  FrappeUI,
  Button,
  setConfig,
  frappeRequest,
  resourcesPlugin,
} from 'frappe-ui'
import './index.css'
import './theme'
import { loadTranslations, translationPlugin } from './translation'

// Route all resource fetches through Frappe's request layer (session auth, CSRF).
setConfig('resourceFetcher', frappeRequest)

// Load translations before importing the app so module-level __() calls see them.
loadTranslations().finally(async () => {
  const [{ default: router }, { default: App }] = await Promise.all([import('./router'), import('./App.vue')])
  const app = createApp(App)
  app.use(router)
  app.use(resourcesPlugin)
  app.use(FrappeUI)
  app.use(translationPlugin)
  app.component('Button', Button)
  app.mount('#app')
})
