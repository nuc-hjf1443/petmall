import { request } from './request'

export const productApi = {
	categories: () => request({ url: '/categories' }),
	list: params => request({ url: '/products', data: params }),
	detail: productId => request({ url: `/products/${productId}` }),
	reviews: (productId, params) => request({
		url: `/products/${productId}/reviews`,
		data: params
	}),
	createReview: (productId, data) => request({
		url: `/products/${productId}/reviews`,
		method: 'POST',
		data,
		auth: true
	})
}
