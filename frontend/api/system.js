import { request, upload } from './request'

export const systemApi = {
	root: () => request({ url: '/' }),
	hello: name => request({ url: `/hello/${encodeURIComponent(name)}` }),
	uploadImage: (filePath, usage = 'general') => upload({
		url: '/uploads/images',
		filePath,
		formData: { usage },
		auth: true,
		showLoading: true,
		loadingText: '上传中...'
	})
}
