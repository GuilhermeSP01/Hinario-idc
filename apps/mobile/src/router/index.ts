import { createRouter, createWebHistory } from 'vue-router';
import HomeView from '@/views/HomeView.vue';
import CurrentHymnView from '@/views/CurrentHymnView.vue';
import FavoritesView from '@/views/FavoritesView.vue';
import SettingsView from '@/views/SettingsView.vue';

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: HomeView,
    },
    {
      path: '/hymn',
      name: 'hymn',
      component: CurrentHymnView,
    },
    {
      path: '/favorites',
      name: 'favorites',
      component: FavoritesView,
    },
    {
      path: '/settings',
      name: 'settings',
      component: SettingsView,
    },
  ],
});
