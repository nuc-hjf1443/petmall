import { request } from './request'

export const userApi = {
	me: () => request({ url: '/users/me', auth: true }),
	updateProfile: data => request({
		url: '/users/me/profile',
		method: 'PUT',
		data,
		auth: true
	}),
	changePassword: data => request({
		url: '/users/me/change-password',
		method: 'POST',
		data,
		auth: true
	}),
	listAddresses: () => request({ url: '/users/me/addresses', auth: true }),
	createAddress: data => request({
		url: '/users/me/addresses',
		method: 'POST',
		data,
		auth: true
	}),
	updateAddress: (addressId, data) => request({
		url: `/users/me/addresses/${addressId}`,
		method: 'PUT',
		data,
		auth: true
	}),
	deleteAddress: addressId => request({
		url: `/users/me/addresses/${addressId}`,
		method: 'DELETE',
		auth: true
	}),
	setDefaultAddress: addressId => request({
		url: `/users/me/addresses/${addressId}/default`,
		method: 'POST',
		auth: true
	})
}
