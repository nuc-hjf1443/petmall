import { request } from './request'

export const orderApi = {
	create: data => request({ url: '/orders', method: 'POST', data, auth: true }),
	list: () => request({ url: '/orders', auth: true }),
	detail: orderId => request({ url: `/orders/${orderId}`, auth: true }),
	pay: orderId => request({
		url: `/orders/${orderId}/pay`,
		method: 'POST',
		auth: true
	}),
	cancel: orderId => request({
		url: `/orders/${orderId}/cancel`,
		method: 'POST',
		auth: true
	}),
	confirmReceipt: orderId => request({
		url: `/orders/${orderId}/confirm-receipt`,
		method: 'POST',
		auth: true
	})
}
