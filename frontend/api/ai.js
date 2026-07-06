import { request } from './request'

export const aiApi = {
	createQaSession: (data = {}) => request({
		url: '/agents/qa/sessions',
		method: 'POST',
		data,
		auth: true
	}),
	sendQaMessage: (sessionId, data) => request({
		url: `/agents/qa/sessions/${sessionId}/messages`,
		method: 'POST',
		data,
		auth: true
	}),
	createGuideSession: (data = {}) => request({
		url: '/agents/guide/sessions',
		method: 'POST',
		data,
		auth: true
	}),
	sendGuideMessage: (sessionId, data) => request({
		url: `/agents/guide/sessions/${sessionId}/messages`,
		method: 'POST',
		data,
		auth: true
	}),
	session: sessionId => request({
		url: `/agents/sessions/${sessionId}`,
		auth: true
	})
}

// 保留现有页面使用的方法名。
export const agentApi = {
	createSession: (data = {}) => aiApi.createQaSession(data),
	send: (sessionId, content) => aiApi.sendQaMessage(sessionId, { content }),
	createQaSession: aiApi.createQaSession,
	sendQaMessage: aiApi.sendQaMessage,
	createGuideSession: aiApi.createGuideSession,
	sendGuideMessage: aiApi.sendGuideMessage,
	session: aiApi.session
}
