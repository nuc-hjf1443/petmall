import { request, upload } from './request'

export const adminApi = {
	users: params => request({ url: '/admin/users', data: params, auth: true }),
	freezeUser: (userId, data = {}) => request({
		url: `/admin/users/${userId}/freeze`,
		method: 'POST',
		data,
		auth: true
	}),
	unfreezeUser: (userId, data = {}) => request({
		url: `/admin/users/${userId}/unfreeze`,
		method: 'POST',
		data,
		auth: true
	}),

	pendingProducts: params => request({
		url: '/admin/products/pending',
		data: params,
		auth: true
	}),
	approveProduct: (productId, data = {}) => request({
		url: `/admin/products/${productId}/approve`,
		method: 'POST',
		data,
		auth: true
	}),
	rejectProduct: (productId, data = {}) => request({
		url: `/admin/products/${productId}/reject`,
		method: 'POST',
		data,
		auth: true
	}),
	offSaleProduct: (productId, data = {}) => request({
		url: `/admin/products/${productId}/off-sale`,
		method: 'POST',
		data,
		auth: true
	}),
	pets: params => request({
		url: '/admin/pets',
		data: params,
		auth: true
	}),
	orders: params => request({
		url: '/admin/orders',
		data: params,
		auth: true
	}),
	orderDetail: orderId => request({
		url: `/admin/orders/${orderId}`,
		auth: true
	}),
	forceCancelOrder: (orderId, data = {}) => request({
		url: `/admin/orders/${orderId}/force-cancel`,
		method: 'POST',
		data,
		auth: true
	}),
	statisticsOverview: () => request({
		url: '/admin/statistics/overview',
		auth: true
	}),
	orderTrend: params => request({
		url: '/admin/statistics/orders-trend',
		data: params,
		auth: true
	}),

	platformKnowledge: () => request({
		url: '/admin/knowledge/platform',
		auth: true
	}),
	platformKnowledgeDocuments: () => request({
		url: '/admin/knowledge/platform/documents',
		auth: true
	}),
	uploadPlatformKnowledgeDocument: filePath => upload({
		url: '/admin/knowledge/platform/documents',
		filePath,
		name: 'file',
		auth: true
	}),
	replacePlatformKnowledgeDocument: (documentId, filePath) => upload({
		url: `/admin/knowledge/platform/documents/${documentId}`,
		filePath,
		name: 'file',
		auth: true,
		method: 'PUT'
	}),
	reindexPlatformKnowledgeDocument: documentId => request({
		url: `/admin/knowledge/platform/documents/${documentId}/reindex`,
		method: 'POST',
		auth: true
	}),
	deletePlatformKnowledgeDocument: documentId => request({
		url: `/admin/knowledge/platform/documents/${documentId}`,
		method: 'DELETE',
		auth: true
	}),

	reports: params => request({ url: '/admin/reports', data: params, auth: true }),
	resolveReport: (reportId, data) => request({
		url: `/admin/reports/${reportId}/resolve`,
		method: 'POST',
		data,
		auth: true
	}),

	adoptionApplications: params => request({
		url: '/admin/adoptions/applications',
		data: params,
		auth: true
	}),
	approveAdoptionApplication: (applicationId, data = {}) => request({
		url: `/admin/adoptions/applications/${applicationId}/approve`,
		method: 'POST',
		data,
		auth: true
	}),
	rejectAdoptionApplication: (applicationId, data = {}) => request({
		url: `/admin/adoptions/applications/${applicationId}/reject`,
		method: 'POST',
		data,
		auth: true
	}),

	pendingMerchants: params => request({ url: '/admin/merchants/pending', data: params, auth: true }),
	approveMerchant: (merchantId, data = {}) => request({
		url: `/admin/merchants/${merchantId}/approve`,
		method: 'POST',
		data,
		auth: true
	}),
	rejectMerchant: (merchantId, data = {}) => request({
		url: `/admin/merchants/${merchantId}/reject`,
		method: 'POST',
		data,
		auth: true
	})
}
