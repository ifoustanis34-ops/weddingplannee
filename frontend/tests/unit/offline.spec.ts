import { AxiosHeaders, type InternalAxiosRequestConfig } from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '@/api/errors'

const request = vi.fn()
vi.mock('@/api/client', () => ({ api: { request: (config: unknown) => request(config) } }))

const queue = await import('@/offline/queue')

function config(method: string, url: string, data?: unknown): InternalAxiosRequestConfig {
  return { method, url, data, headers: new AxiosHeaders() } as InternalAxiosRequestConfig
}

describe('offline queue', () => {
  beforeEach(() => {
    request.mockReset()
    for (const change of [...queue.pending.value, ...queue.failed.value]) queue.discard(change.id)
    queue.setUser('u1')
  })

  it('keeps only writes of a signed-in person, never the session nor files', () => {
    expect(queue.canQueue(config('post', '/clients', { name: 'Awa' }))).toBe(true)
    expect(queue.canQueue(config('patch', '/floor-plans/1', {}))).toBe(true)
    expect(queue.canQueue(config('get', '/clients'))).toBe(false)
    expect(queue.canQueue(config('post', '/auth/login', {}))).toBe(false)
    expect(queue.canQueue(config('post', '/expenses/1/receipt', new FormData()))).toBe(false)
    queue.setUser(null)
    expect(queue.canQueue(config('post', '/clients', {}))).toBe(false)
  })

  it('keeps a change made twice only once', () => {
    queue.enqueue(config('post', '/clients', '{"name":"Awa"}'), 'maison')
    queue.enqueue(config('post', '/clients', '{"name":"Awa"}'), 'maison')

    expect(queue.pending.value).toHaveLength(1)
    expect(queue.pending.value[0]).toMatchObject({
      method: 'post',
      url: '/clients',
      slug: 'maison',
      data: { name: 'Awa' },
    })
  })

  it('sends the changes in order when the network is back, in their own space', async () => {
    const synced = vi.fn()
    queue.onQueueSynced(synced)
    queue.enqueue(config('post', '/clients', { name: 'Awa' }), 'maison')
    queue.enqueue(config('patch', '/clients/1', { phone: '+237' }), 'maison')
    request.mockResolvedValue({ data: {} })

    await queue.flush()

    expect(request.mock.calls.map(([c]) => [c.method, c.url])).toEqual([
      ['post', '/clients'],
      ['patch', '/clients/1'],
    ])
    expect(request.mock.calls[0]![0].headers).toEqual({ 'X-Organization': 'maison' })
    expect(queue.pending.value).toHaveLength(0)
    expect(synced).toHaveBeenCalledWith(2)
  })

  it('stops at a network failure and keeps a refused change aside with its reason', async () => {
    queue.enqueue(config('post', '/clients', { name: 'A' }), 'maison')
    queue.enqueue(config('post', '/clients', { name: 'B' }), 'maison')
    request.mockRejectedValueOnce(new ApiError('network_error', 'Connexion impossible.'))

    await queue.flush()
    expect(queue.pending.value).toHaveLength(2)

    request
      .mockRejectedValueOnce(new ApiError('invalid', 'Ce client existe déjà.', 400))
      .mockResolvedValueOnce({ data: {} })
    await queue.flush()

    expect(queue.pending.value).toHaveLength(0)
    expect(queue.failed.value).toHaveLength(1)
    expect(queue.failed.value[0]!.error).toBe('Ce client existe déjà.')
  })
})
