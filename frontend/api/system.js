import { request } from './request'

export const systemApi = {
	root: () => request({ url: '/' }),
	hello: name => request({ url: `/hello/${encodeURIComponent(name)}` })
}
