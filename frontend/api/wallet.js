import { request } from './request'

export const walletApi = {
	account: () => request({
		url: '/wallet/me',
		auth: true
	}),
	transactions: params => request({
		url: '/wallet/transactions',
		data: params,
		auth: true
	}),
	recharge: data => request({
		url: '/wallet/recharges',
		method: 'POST',
		data,
		auth: true
	}),
	withdraw: data => request({
		url: '/wallet/withdrawals',
		method: 'POST',
		data,
		auth: true
	}),
	withdrawals: () => request({
		url: '/wallet/withdrawals',
		auth: true
	}),
	adminWithdrawals: params => request({
		url: '/wallet/admin/withdrawals',
		data: params,
		auth: true
	}),
	approveWithdrawal: (withdrawalId, data = {}) => request({
		url: `/wallet/admin/withdrawals/${withdrawalId}/approve`,
		method: 'POST',
		data,
		auth: true
	}),
	rejectWithdrawal: (withdrawalId, data = {}) => request({
		url: `/wallet/admin/withdrawals/${withdrawalId}/reject`,
		method: 'POST',
		data,
		auth: true
	})
}
