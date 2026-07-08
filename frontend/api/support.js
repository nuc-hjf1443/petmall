import { request } from './request'

export const supportApi = {
	list: params => request({ url: '/support/conversations', data: params, auth: true }),
	detail: conversationId => request({ url: `/support/conversations/${conversationId}`, auth: true }),
	send: (conversationId, data) => request({
		url: `/support/conversations/${conversationId}/messages`,
		method: 'POST',
		data,
		auth: true
	}),
	platform: () => request({ url: '/support/platform', method: 'POST', auth: true }),
	merchantByProduct: productId => request({
		url: `/support/products/${productId}/merchant`,
		method: 'POST',
		auth: true
	}),
	adoption: (adoptionId, applicationId) => request({
		url: applicationId ? `/support/adoptions/${adoptionId}?application_id=${applicationId}` : `/support/adoptions/${adoptionId}`,
		method: 'POST',
		auth: true
	}),
	publishedAdoptions: params => request({ url: '/support/adoptions/published', data: params, auth: true }),

	merchantList: params => request({ url: '/merchants/me/support/conversations', data: params, auth: true }),
	merchantSend: (conversationId, data) => request({
		url: `/merchants/me/support/conversations/${conversationId}/messages`,
		method: 'POST',
		data,
		auth: true
	}),
	merchantStatus: (conversationId, status) => request({
		url: `/merchants/me/support/conversations/${conversationId}/status`,
		method: 'PUT',
		data: { status },
		auth: true
	}),
	merchantTransfer: conversationId => request({
		url: `/merchants/me/support/conversations/${conversationId}/transfer`,
		method: 'POST',
		auth: true
	}),

	adminList: params => request({ url: '/admin/support/conversations', data: params, auth: true }),
	adminSend: (conversationId, data) => request({
		url: `/admin/support/conversations/${conversationId}/messages`,
		method: 'POST',
		data,
		auth: true
	}),
	adminStatus: (conversationId, status) => request({
		url: `/admin/support/conversations/${conversationId}/status`,
		method: 'PUT',
		data: { status },
		auth: true
	})
}
