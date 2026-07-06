import { request, upload } from './request'

export const knowledgeApi = {
	create: data => request({
		url: '/knowledge-bases',
		method: 'POST',
		data,
		auth: true
	}),
	list: () => request({ url: '/knowledge-bases', auth: true }),
	detail: kbId => request({ url: `/knowledge-bases/${kbId}`, auth: true }),
	remove: kbId => request({
		url: `/knowledge-bases/${kbId}`,
		method: 'DELETE',
		auth: true
	}),
	uploadDocument: (kbId, filePath) => upload({
		url: `/knowledge-bases/${kbId}/documents`,
		filePath,
		name: 'file',
		auth: true
	}),
	previewGeneratedDocument: (kbId, petId) => request({
		url: `/knowledge-bases/${kbId}/documents/generated-preview`,
		method: 'POST',
		data: { pet_id: petId },
		auth: true
	}),
	generateFromPet: (kbId, petId) => request({
		url: `/knowledge-bases/${kbId}/documents/generate-from-pet`,
		method: 'POST',
		data: { pet_id: petId },
		auth: true
	}),
	documents: kbId => request({
		url: `/knowledge-bases/${kbId}/documents`,
		auth: true
	}),
	deleteDocument: (kbId, documentId) => request({
		url: `/knowledge-bases/${kbId}/documents/${documentId}`,
		method: 'DELETE',
		auth: true
	}),
	reindexDocument: (kbId, documentId) => request({
		url: `/knowledge-bases/${kbId}/documents/${documentId}/reindex`,
		method: 'POST',
		auth: true
	})
}
