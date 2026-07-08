import { request } from './request'

export const merchantApi = {
	apply: data => request({
		url: '/merchants/apply',
		method: 'POST',
		data,
		auth: true
	}),
	me: () => request({
		url: '/merchants/me',
		auth: true,
		silentStatuses: [404]
	}),
	update: data => request({
		url: '/merchants/me',
		method: 'PUT',
		data,
		auth: true
	}),
	follow: merchantId => request({
		url: `/merchants/${merchantId}/follow`,
		method: 'POST',
		auth: true
	}),
	unfollow: merchantId => request({
		url: `/merchants/${merchantId}/follow`,
		method: 'DELETE',
		auth: true
	}),
	dashboard: () => request({ url: '/merchants/me/dashboard', auth: true }),
	products: () => request({ url: '/merchants/me/products', auth: true }),
	createProduct: data => request({
		url: '/merchants/me/products',
		method: 'POST',
		data,
		auth: true
	}),
	updateProduct: (productId, data) => request({
		url: `/merchants/me/products/${productId}`,
		method: 'PUT',
		data,
		auth: true
	}),
	submitProduct: (productId, data = {}) => request({
		url: `/merchants/me/products/${productId}/submit`,
		method: 'POST',
		data,
		auth: true
	}),
	putProductOnSale: (productId, data = {}) => request({
		url: `/merchants/me/products/${productId}/on-sale`,
		method: 'POST',
		data,
		auth: true
	}),
	takeProductOffSale: (productId, data = {}) => request({
		url: `/merchants/me/products/${productId}/off-sale`,
		method: 'POST',
		data,
		auth: true
	}),
	setProductDiscount: (productId, data) => request({
		url: `/merchants/me/products/${productId}/discount`,
		method: 'POST',
		data,
		auth: true
	})
}
