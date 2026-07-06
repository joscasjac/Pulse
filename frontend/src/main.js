import { createApp } from 'vue'
import {
  FrappeUI,
  Button,
  setConfig,
  frappeRequest,
  resourcesPlugin,
} from 'frappe-ui'
import router from './router'
import App from './App.vue'
import './index.css'
import './theme'

// Route all resource fetches through Frappe's request layer (session auth, CSRF).
setConfig('resourceFetcher', frappeRequest)

const app = createApp(App)
app.use(router)
app.use(resourcesPlugin)
app.use(FrappeUI)
app.component('Button', Button)
app.mount('#app')
