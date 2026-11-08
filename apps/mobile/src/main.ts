import { createApp } from 'vue';
import { configureLogging, reportError } from '@hinario/observability';
import { createPinia } from 'pinia';
import App from './App.vue';
import { router } from './router';
import './styles/main.css';

configureLogging({
  environment: import.meta.env.MODE === 'test' ? 'test' : import.meta.env.DEV ? 'development' : 'production',
  level: import.meta.env.VITE_LOG_LEVEL,
});
const app = createApp(App);
app.config.errorHandler = (error) => reportError('app.unhandled', error);
window.addEventListener('error', event => {
  reportError('app.unhandled', event.error);
  event.preventDefault();
});
window.addEventListener('unhandledrejection', event => {
  reportError('app.unhandled', event.reason);
  event.preventDefault();
});

app.use(createPinia());
app.use(router);

app.mount('#app');
