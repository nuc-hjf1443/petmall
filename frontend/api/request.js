const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
	|| (import.meta.env.DEV ? 'http://127.0.0.1:8000' : '/api')

const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'
let redirectingToLogin = false

function getAccessToken() {
	return uni.getStorageSync(ACCESS_TOKEN_KEY)
}

function setTokens(payload) {
	if (payload?.access_token) {
		uni.setStorageSync(ACCESS_TOKEN_KEY, payload.access_token)
	}
	if (payload?.refresh_token) {
		uni.setStorageSync(REFRESH_TOKEN_KEY, payload.refresh_token)
	}
}

function clearTokens() {
	uni.removeStorageSync(ACCESS_TOKEN_KEY)
	uni.removeStorageSync(REFRESH_TOKEN_KEY)
}

function unwrap(data) {
	return data?.data ?? data
}

function assetUrl(url) {
	if (!url || typeof url !== 'string') return ''
	if (/^(https?:|data:|blob:|file:)/i.test(url)) return url
	if (url.startsWith('/generated/')) return `${API_BASE_URL}${url}`
	return url
}

function parseResponseData(data) {
	if (typeof data !== 'string') return data
	try {
		return JSON.parse(data)
	} catch (_) {
		return data
	}
}

function cleanQueryData(data) {
	if (!data || typeof data !== 'object' || Array.isArray(data)) return data
	return Object.keys(data).reduce((result, key) => {
		if (data[key] !== undefined && data[key] !== null && data[key] !== '') {
			result[key] = data[key]
		}
		return result
	}, {})
}

function validationMessage(detail) {
	if (!Array.isArray(detail)) return ''
	return detail
		.map(item => {
			const location = Array.isArray(item?.loc)
				? item.loc.filter(part => !['body', 'query', 'path'].includes(part)).join('.')
				: ''
			return `${location ? `${location}: ` : ''}${item?.msg || '参数格式错误'}`
		})
		.filter(Boolean)
		.join('；')
}

function errorMessage(statusCode, data) {
	const detail = data?.detail
	const backendMessage = typeof detail === 'string'
		? detail
		: detail?.message || validationMessage(detail) || data?.message

	if (statusCode === 401) return backendMessage || '登录状态已过期，请重新登录'
	if (statusCode === 400 || statusCode === 422) return backendMessage || '请求参数有误'
	if (statusCode >= 500) return '服务器错误，请稍后重试'
	return backendMessage || `请求失败（${statusCode}）`
}

function notify(message) {
	uni.showToast({ title: message, icon: 'none', duration: 2500 })
}

function redirectToLogin() {
	if (redirectingToLogin) return
	redirectingToLogin = true
	clearTokens()
	notify('登录状态已过期，请重新登录')
	setTimeout(() => {
		uni.reLaunch({
			url: '/pages/auth/login',
			complete: () => {
				redirectingToLogin = false
			}
		})
	}, 300)
}

function createHttpError(statusCode, data) {
	const error = new Error(errorMessage(statusCode, data))
	error.statusCode = statusCode
	error.data = data
	return error
}

function handleResponse(statusCode, rawData, auth, silentStatuses = []) {
	const data = parseResponseData(rawData)
	if (statusCode >= 200 && statusCode < 300) return unwrap(data)

	const error = createHttpError(statusCode, data)
	if (statusCode === 401 && auth) {
		redirectToLogin()
	} else if (!silentStatuses.includes(statusCode)) {
		notify(error.message)
	}
	throw error
}

function handleNetworkError(error, { url, silentNetworkError = false } = {}) {
	const networkError = new Error('网络请求失败，请检查后端服务是否已启动')
	networkError.cause = error
	if (typeof console !== 'undefined' && console.warn) {
		console.warn('[request network error]', { url, error })
	}
	if (!silentNetworkError) notify(networkError.message)
	throw networkError
}

export function request({
	url,
	method = 'GET',
	data,
	header = {},
	auth = false,
	silentStatuses = [],
	silentNetworkError = false,
	showLoading = false,
	loadingText = '加载中'
}) {
	const token = getAccessToken()
	const requestData = method.toUpperCase() === 'GET' ? cleanQueryData(data) : data
	const fullUrl = `${API_BASE_URL}${url}`
	if (showLoading) uni.showLoading({ title: loadingText, mask: true })

	return new Promise((resolve, reject) => {
		uni.request({
			url: fullUrl,
			method,
			data: requestData,
			header: {
				'Content-Type': 'application/json',
				...(token ? { Authorization: `Bearer ${token}` } : {}),
				...header
			},
			success: response => {
				try {
					resolve(handleResponse(response.statusCode, response.data, auth, silentStatuses))
				} catch (error) {
					reject(error)
				}
			},
			fail: error => {
				try {
					handleNetworkError(error, { url: fullUrl, silentNetworkError })
				} catch (networkError) {
					reject(networkError)
				}
			},
			complete: () => {
				if (showLoading) uni.hideLoading()
			}
		})
	})
}

export function upload({
	url,
	method = 'POST',
	filePath,
	files,
	name = 'file',
	formData = {},
	header = {},
	auth = true,
	silentNetworkError = false,
	showLoading = false,
	loadingText = '上传中'
}) {
	const token = getAccessToken()
	const fullUrl = `${API_BASE_URL}${url}`
	if (showLoading) uni.showLoading({ title: loadingText, mask: true })

	return new Promise((resolve, reject) => {
		const options = {
			url: fullUrl,
			method,
			name,
			formData,
			header: {
				...(token ? { Authorization: `Bearer ${token}` } : {}),
				...header
			},
			success: response => {
				try {
					resolve(handleResponse(response.statusCode, response.data, auth))
				} catch (error) {
					reject(error)
				}
			},
			fail: error => {
				try {
					handleNetworkError(error, { url: fullUrl, silentNetworkError })
				} catch (networkError) {
					reject(networkError)
				}
			},
			complete: () => {
				if (showLoading) uni.hideLoading()
			}
		}
		if (files?.length) options.files = files
		else options.filePath = filePath
		uni.uploadFile(options)
	})
}

export {
	ACCESS_TOKEN_KEY,
	API_BASE_URL,
	assetUrl,
	clearTokens,
	getAccessToken,
	setTokens
}
