<template>
	<AppShell active="adoption">
		<view class="page-container">
			<view class="page-heading">
				<view>
					<text class="page-title">发布领养信息</text>
					<text class="page-subtitle">请真实描述健康情况与领养要求</text>
				</view>
			</view>
			<view class="card panel">
				<view class="form-grid">
					<label v-for="f in fields" :key="f.key" class="form-field" :class="{full:f.full}">
						<text>{{f.label}}</text>
						<textarea v-if="f.full" v-model="form[f.key]"/>
						<input v-else v-model="form[f.key]"/>
					</label>
					<view class="form-field full">
						<text>封面图片</text>
						<view class="upload-row">
							<view class="cover-uploader" @click="chooseCover">
								<image v-if="form.cover_image" :src="coverPreview" mode="aspectFill" />
								<view v-else class="upload-placeholder">
									<text class="upload-plus">+</text>
									<text>选择本地图片</text>
								</view>
							</view>
							<view class="upload-side">
								<button class="secondary-button" :loading="uploadingCover" :disabled="uploadingCover" @click="chooseCover">
									{{ form.cover_image ? '重新选择' : '上传封面' }}
								</button>
								<button v-if="form.cover_image" class="secondary-button" @click="clearCover">移除</button>
								<text>支持 JPG、PNG、WEBP，上传后会在领养列表和详情中展示</text>
							</view>
						</view>
					</view>
				</view>
				<view class="button-row"><button class="action-button" :loading="saving" @click="save">发布</button></view>
			</view>
		</view>
	</AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue'
import { adoptionApi, assetUrl, systemApi } from '../../api'

export default {
	components: { AppShell },
	data() {
		return {
			saving: false,
			uploadingCover: false,
			form: { name: '', species: '', breed: '', age_text: '', gender: '', city: '', description: '', health_status: '', requirements: '', cover_image: '' },
			fields: [
				{ key: 'name', label: '名字' },
				{ key: 'species', label: '物种' },
				{ key: 'breed', label: '品种' },
				{ key: 'age_text', label: '年龄' },
				{ key: 'gender', label: '性别' },
				{ key: 'city', label: '城市' },
				{ key: 'description', label: '详细介绍', full: true },
				{ key: 'health_status', label: '健康情况', full: true },
				{ key: 'requirements', label: '领养要求', full: true }
			]
		}
	},
	computed: {
		coverPreview() {
			return assetUrl(this.form.cover_image)
		}
	},
	methods: {
		chooseCover() {
			uni.chooseImage({
				count: 1,
				sizeType: ['compressed'],
				success: async result => {
					const filePath = result.tempFilePaths?.[0]
					if (!filePath) return
					this.uploadingCover = true
					try {
						const uploaded = await systemApi.uploadImage(filePath, 'adoption')
						this.form.cover_image = uploaded.file_url
					} catch (e) {
						// 请求层统一提示
					} finally {
						this.uploadingCover = false
					}
				}
			})
		},
		clearCover() {
			this.form.cover_image = ''
		},
		async save() {
			if (['name', 'species', 'city', 'description'].some(k => !this.form[k])) return uni.showToast({ title: '请填写必填信息', icon: 'none' })
			this.saving = true
			try {
				const item = await adoptionApi.create(this.form)
				uni.showToast({ title: '领养信息已发布' })
				setTimeout(() => uni.redirectTo({ url: `/pages/adoption/detail?id=${item.id}` }), 400)
			} catch (e) {
			} finally {
				this.saving = false
			}
		}
	}
}
</script>

<style scoped>
.upload-row{display:flex;gap:16px;align-items:flex-start}.cover-uploader{display:flex;width:180px;height:135px;align-items:center;justify-content:center;overflow:hidden;border:1px dashed var(--color-primary);border-radius:12px;background:#fffaf6;cursor:pointer}.cover-uploader image{width:100%;height:100%}.upload-placeholder{display:flex;flex-direction:column;align-items:center;gap:6px;color:var(--color-primary);font-size:12px}.upload-plus{font-size:28px;line-height:1}.upload-side{display:flex;flex-direction:column;gap:10px}.upload-side button{margin:0}.upload-side text{color:var(--color-text-secondary);font-size:11px;line-height:1.6}@media(max-width:767px){.upload-row{display:block}.upload-side{margin-top:10px}.cover-uploader{width:150px;height:112px}}
</style>
