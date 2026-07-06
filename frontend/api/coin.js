import { request } from './request'

export const coinApi = {
	account: () => request({ url: '/coins/account', auth: true }),
	logs: params => request({ url: '/coins/logs', data: params, auth: true }),
	checkin: () => request({
		url: '/coins/checkin',
		method: 'POST',
		auth: true
	}),
	tasks: () => request({ url: '/coins/tasks', auth: true }),
	claimTask: taskId => request({
		url: `/coins/tasks/${taskId}/claim`,
		method: 'POST',
		auth: true
	})
}
