import { request } from './request'

export const aiApi = {
	createQaSession: (data = {}) => request({
		url: '/agents/qa/sessions',
		method: 'POST',
		data,
		auth: true
	}),
	listQaSessions: () => request({
		url: '/agents/qa/sessions',
		auth: true
	}),
	deleteQaSession: sessionId => request({
		url: `/agents/qa/sessions/${sessionId}`,
		method: 'DELETE',
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
	sessions: (data = {}) => request({
		url: '/agents/sessions',
		data,
		auth: true
	}),
	session: sessionId => request({
		url: `/agents/sessions/${sessionId}`,
		auth: true
	}),
	guideRecommendations: sessionId => request({
		url: `/agents/guide/sessions/${sessionId}/recommendations`,
		auth: true
	})
}

// 保留现有页面使用的方法名。
export const agentApi = {
	createSession: (data = {}) => aiApi.createQaSession(data),
	listSessions: aiApi.listQaSessions,
	deleteSession: aiApi.deleteQaSession,
	send: (sessionId, content, asyncMode = false) => aiApi.sendQaMessage(sessionId, { content, async_mode: asyncMode }),
	createQaSession: aiApi.createQaSession,
	listQaSessions: aiApi.listQaSessions,
	deleteQaSession: aiApi.deleteQaSession,
	sendQaMessage: aiApi.sendQaMessage,
	createGuideSession: aiApi.createGuideSession,
	sendGuideMessage: aiApi.sendGuideMessage,
	sessions: aiApi.sessions,
	guideRecommendations: aiApi.guideRecommendations,
	session: aiApi.session
}
