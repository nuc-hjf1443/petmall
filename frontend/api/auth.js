import { clearTokens, request, setTokens } from './request'

export const authApi = {
	sendCode: phone => request({
		url: '/auth/code',
		method: 'POST',
		data: { phone }
	}),

	register: data => request({
		url: '/auth/register',
		method: 'POST',
		data
	}),

	async login(data) {
		const tokens = await request({ url: '/auth/login', method: 'POST', data })
		setTokens(tokens)
		return tokens
	},

	async logout() {
		try {
			return await request({ url: '/auth/logout', method: 'POST' })
		} finally {
			clearTokens()
		}
	},

	async refresh() {
		const tokens = await request({ url: '/auth/refresh', method: 'POST', auth: true })
		setTokens(tokens)
		return tokens
	},

	changePassword: data => request({
		url: '/auth/change-password',
		method: 'POST',
		data,
		auth: true
	})
}
