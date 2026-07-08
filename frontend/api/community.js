import { request, upload } from './request'

export const communityApi = {
	list: (params = {}) => request({ url: '/posts', data: params }),

	publish({ content, topicIds = [], topicNames = [], filePaths = [] }) {
		const formData = {
			...(content ? { content } : {}),
			...(topicIds.length ? { topic_ids: JSON.stringify(topicIds) } : {}),
			...(topicNames.length ? { topic_names: JSON.stringify(topicNames) } : {})
		}
		if (!filePaths.length) {
			return request({
				url: '/posts',
				method: 'POST',
				data: formData,
				header: { 'Content-Type': 'application/x-www-form-urlencoded' },
				auth: true
			})
		}
		return upload({
			url: '/posts',
			files: filePaths.map(uri => ({ name: 'files', uri })),
			formData,
			auth: true
		})
	},

	detail: postId => request({ url: `/posts/${postId}` }),
	remove: postId => request({
		url: `/posts/${postId}`,
		method: 'DELETE',
		auth: true
	}),
	like: postId => request({
		url: `/posts/${postId}/likes`,
		method: 'POST',
		auth: true
	}),
	unlike: postId => request({
		url: `/posts/${postId}/likes`,
		method: 'DELETE',
		auth: true
	}),
	favorite: postId => request({
		url: `/posts/${postId}/favorites`,
		method: 'POST',
		auth: true
	}),
	unfavorite: postId => request({
		url: `/posts/${postId}/favorites`,
		method: 'DELETE',
		auth: true
	}),
	comments: postId => request({ url: `/posts/${postId}/comments` }),
	createComment: (postId, data) => request({
		url: `/posts/${postId}/comments`,
		method: 'POST',
		data,
		auth: true
	}),
	deleteComment: (postId, commentId) => request({
		url: `/posts/${postId}/comments/${commentId}`,
		method: 'DELETE',
		auth: true
	}),
	report: (postId, data) => request({
		url: `/posts/${postId}/reports`,
		method: 'POST',
		data,
		auth: true
	}),
	topics: (options = {}) => request({ ...options, url: '/topics' }),
	follow: userId => request({
		url: `/users/${userId}/follow`,
		method: 'POST',
		auth: true
	}),
	unfollow: userId => request({
		url: `/users/${userId}/follow`,
		method: 'DELETE',
		auth: true
	})
}
