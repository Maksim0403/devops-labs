import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createRouter, createMemoryHistory } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import { useToastStore } from '@/stores/toast'

const { mockPost, mockGetTemplates } = vi.hoisted(() => ({
  mockPost: vi.fn(),
  mockGetTemplates: vi.fn(),
}))

vi.mock('@/api/axios', () => ({
  default: { post: mockPost },
}))

vi.mock('@/api/orders', () => ({
  ordersApi: { getTemplates: mockGetTemplates },
}))

import CreateDelivery from '../CreateDelivery.vue'

const createWrapper = () => {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/recipient/orders', component: { template: '<div />' } },
    ],
  })

  const pinia = createPinia()
  setActivePinia(pinia)

  const wrapper = mount(CreateDelivery, { global: { plugins: [pinia, router] } })
  return { wrapper, router, toastStore: useToastStore(pinia) }
}

const fillOrderForm = async (
  wrapper: ReturnType<typeof createWrapper>['wrapper'],
  options: { title?: string; weight?: string; description?: string } = {},
) => {
  const textInputs = wrapper.findAll('input[type="text"]')
  const numberInputs = wrapper.findAll('input[type="number"]')

  await textInputs.at(0)!.setValue(options.title ?? 'Electronics to Kyiv')
  await textInputs.at(1)!.setValue('Warehouse A')
  await textInputs.at(2)!.setValue('Kyiv')
  await numberInputs.at(0)!.setValue('10')
  await numberInputs.at(1)!.setValue(options.weight ?? '5.5')

  if (options.description) {
    await wrapper.find('textarea').setValue(options.description)
  }
}

describe('CreateDelivery', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    localStorage.clear()
    mockGetTemplates.mockResolvedValue([])
  })

  describe('rendering', () => {
    it('displays the page heading', () => {
      const { wrapper } = createWrapper()
      expect(wrapper.find('h1').text()).toBe('Create New Delivery')
    })

    it('renders the title input field', () => {
      const { wrapper } = createWrapper()
      expect(wrapper.find('input[type="text"]').exists()).toBe(true)
    })

    it('renders the weight input field', () => {
      const { wrapper } = createWrapper()
      expect(wrapper.find('input[type="number"]').exists()).toBe(true)
    })

    it('renders the description textarea', () => {
      const { wrapper } = createWrapper()
      expect(wrapper.find('textarea').exists()).toBe(true)
    })

    it('submit button shows "Create Shipment" by default', () => {
      const { wrapper } = createWrapper()
      expect(wrapper.find('button[type="submit"]').text()).toContain('Create Shipment')
    })

    it('renders the Cancel button', () => {
      const { wrapper } = createWrapper()
      expect(wrapper.find('button[type="button"]').text()).toContain('Cancel')
    })
  })

  describe('successful order creation', () => {
    it('sends POST to /orders/ with form data', async () => {
      mockPost.mockResolvedValueOnce({ data: { id: 1 } })
      const { wrapper } = createWrapper()

      await fillOrderForm(wrapper, { description: 'Fragile items' })
      await wrapper.find('form').trigger('submit')
      await flushPromises()

      expect(mockPost).toHaveBeenCalledWith('/orders/', {
        title: 'Electronics to Kyiv',
        description: 'Quantity: N/A, Volume: N/A. Fragile items',
        weight: 5.5,
        distance: 10,
        total_amount: 247.5,
        origin_address: 'Warehouse A',
        destination_address: 'Kyiv',
        is_template: false,
      })
    })

    it('redirects to /recipient/orders on success', async () => {
      mockPost.mockResolvedValueOnce({ data: { id: 1 } })
      const { wrapper, router } = createWrapper()

      await fillOrderForm(wrapper, { title: 'Test order', weight: '1.0' })

      await wrapper.find('form').trigger('submit')
      await flushPromises()

      expect(router.currentRoute.value.path).toBe('/recipient/orders')
    })
  })

  describe('error handling', () => {
    it('does not redirect if request fails', async () => {
      mockPost.mockRejectedValueOnce(new Error('Network Error'))
      const { wrapper, router, toastStore } = createWrapper()

      await fillOrderForm(wrapper, { title: 'Valid title', weight: '1.0' })

      await wrapper.find('form').trigger('submit')
      await flushPromises()

      expect(router.currentRoute.value.path).toBe('/')
      expect(toastStore.toasts[0]?.message).toBe('Something went wrong. Please try again.')
    })

    it('re-enables the submit button after a failed request', async () => {
      mockPost.mockRejectedValueOnce(new Error('Network Error'))
      const { wrapper } = createWrapper()

      await fillOrderForm(wrapper, { title: 'Valid title', weight: '1.0' })

      await wrapper.find('form').trigger('submit')
      await flushPromises()

      expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
    })
  })

  describe('loading state', () => {
    it('shows "Processing..." while request is pending', async () => {
      mockPost.mockReturnValueOnce(new Promise(() => {}))
      const { wrapper } = createWrapper()

      await fillOrderForm(wrapper, { title: 'Valid title', weight: '1.0' })

      await wrapper.find('form').trigger('submit')

      expect(wrapper.find('button[type="submit"]').text()).toContain('Processing...')
    })

    it('disables the submit button while loading', async () => {
      mockPost.mockReturnValueOnce(new Promise(() => {}))
      const { wrapper } = createWrapper()

      await fillOrderForm(wrapper, { title: 'Valid title', weight: '1.0' })

      await wrapper.find('form').trigger('submit')

      expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeDefined()
    })

    it('re-enables the submit button after request completes', async () => {
      mockPost.mockResolvedValueOnce({ data: {} })
      const { wrapper } = createWrapper()

      await fillOrderForm(wrapper, { title: 'Valid title', weight: '1.0' })

      await wrapper.find('form').trigger('submit')
      await flushPromises()

      expect(wrapper.find('button[type="submit"]').attributes('disabled')).toBeUndefined()
    })
  })
})
