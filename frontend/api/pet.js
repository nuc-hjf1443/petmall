import { request } from './request'

export const petApi = {
	list: () => request({ url: '/pets', auth: true }),
	create: data => request({ url: '/pets', method: 'POST', data, auth: true }),
	detail: petId => request({ url: `/pets/${petId}`, auth: true }),
	update: (petId, data) => request({
		url: `/pets/${petId}`,
		method: 'PUT',
		data,
		auth: true
	}),
	remove: petId => request({ url: `/pets/${petId}`, method: 'DELETE', auth: true }),

	listGrowthRecords: petId => request({
		url: `/pets/${petId}/growth-records`,
		auth: true
	}),
	createGrowthRecord: (petId, data) => request({
		url: `/pets/${petId}/growth-records`,
		method: 'POST',
		data,
		auth: true
	}),
	deleteGrowthRecord: (petId, recordId) => request({
		url: `/pets/${petId}/growth-records/${recordId}`,
		method: 'DELETE',
		auth: true
	}),

	listReminders: petId => request({ url: `/pets/${petId}/reminders`, auth: true }),
	createReminder: (petId, data) => request({
		url: `/pets/${petId}/reminders`,
		method: 'POST',
		data,
		auth: true
	}),
	updateReminder: (petId, reminderId, data) => request({
		url: `/pets/${petId}/reminders/${reminderId}`,
		method: 'PUT',
		data,
		auth: true
	}),
	deleteReminder: (petId, reminderId) => request({
		url: `/pets/${petId}/reminders/${reminderId}`,
		method: 'DELETE',
		auth: true
	}),

	detailProfile: petId => request({ url: `/pets/${petId}/detail-profile`, auth: true }),
	updateDetailProfile: (petId, data) => request({
		url: `/pets/${petId}/detail-profile`,
		method: 'PUT',
		data,
		auth: true
	}),
	profileCompleteness: petId => request({
		url: `/pets/${petId}/profile-completeness`,
		auth: true
	}),
	previewProfileDocument: petId => request({
		url: `/pets/${petId}/profile-document/preview`,
		method: 'POST',
		auth: true
	})
}
