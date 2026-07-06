import { request } from './request'

export const adoptionApi = {
	list: () => request({ url: '/adoptions' }),
	detail: adoptionId => request({ url: `/adoptions/${adoptionId}` }),
	create: data => request({
		url: '/adoptions',
		method: 'POST',
		data,
		auth: true
	}),
	myApplications: () => request({
		url: '/adoptions/applications/my',
		auth: true
	}),
	apply: (adoptionId, data) => request({
		url: `/adoptions/${adoptionId}/applications`,
		method: 'POST',
		data,
		auth: true
	})
}
