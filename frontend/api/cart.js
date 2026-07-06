import { request } from './request'

export const cartApi = {
	list: () => request({ url: '/cart/items', auth: true }),
	add: data => request({ url: '/cart/items', method: 'POST', data, auth: true }),
	update: (itemId, data) => request({
		url: `/cart/items/${itemId}`,
		method: 'PUT',
		data,
		auth: true
	}),
	remove: itemId => request({
		url: `/cart/items/${itemId}`,
		method: 'DELETE',
		auth: true
	})
}
