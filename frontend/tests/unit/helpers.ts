import { QueryClient, VueQueryPlugin } from '@tanstack/vue-query'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import type { Component } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'

import { i18n } from '@/i18n'

/** Mount with the app plugins (Pinia, i18n, Vue Query, an in-memory router). */
export function mountWithPlugins(
  component: Component,
  options: { props?: Record<string, unknown> } = {},
) {
  const pinia = createPinia()
  setActivePinia(pinia)
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'dashboard', component: { template: '<div />' } },
      { path: '/connexion', name: 'login', component: { template: '<div />' } },
      { path: '/profil', name: 'profile', component: { template: '<div />' } },
      { path: '/inscription', name: 'signup', component: { template: '<div />' } },
      { path: '/mot-de-passe-oublie', name: 'forgot-password', component: { template: '<div />' } },
      { path: '/invitation/:token', name: 'invitation', component: { template: '<div />' } },
      {
        path: '/mariages/:id/billets',
        name: 'wedding-tickets',
        component: { template: '<div />' },
      },
      { path: '/t/:token', name: 'public-ticket', component: { template: '<div />' } },
      // Menu destinations, so that the shell can render its links.
      ...[
        'clients',
        'quotes',
        'reservations',
        'stock',
        'movements',
        'finance',
        'reports',
        'staff',
        'tasks',
        'pay',
        'attendance',
        'missions',
        'catalog',
        'settings',
        'weddings',
        'calendar',
        'vendors',
        'floorplans',
      ].map((name) => ({
        path: `/${name}`,
        name,
        component: { template: '<div />' },
      })),
    ],
  })
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = mount(component, {
    props: options.props,
    attachTo: document.body,
    global: { plugins: [pinia, i18n, router, [VueQueryPlugin, { queryClient }]] },
  })
  return { wrapper, router, pinia }
}

/** vee-validate validates asynchronously: let validation and submit handlers settle. */
export async function settle(): Promise<void> {
  for (let i = 0; i < 5; i++) await new Promise((resolve) => setTimeout(resolve, 0))
}
