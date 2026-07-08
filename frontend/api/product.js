import { request } from './request'

export const productApi = {
	categories: () => request({ url: '/categories' }),
	list: params => request({ url: '/products', data: params }),
	detail: productId => request({ url: `/products/${productId}` }),
	favorites: params => request({ url: '/products/favorites', data: params, auth: true }),
	favorite: productId => request({
		url: `/products/${productId}/favorite`,
		method: 'POST',
		auth: true
	}),
	unfavorite: productId => request({
		url: `/products/${productId}/favorite`,
		method: 'DELETE',
		auth: true
	}),
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
