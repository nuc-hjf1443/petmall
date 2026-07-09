<template>
	<AppShell active="profile">
		<view class="page-container">
			<view v-if="loading" class="card empty-inline">正在加载宠物档案...</view>
			<StatePanel v-else-if="!pet" icon="!" title="档案加载失败" action="重试" @action="load" />
			<template v-else>
				<view class="page-heading">
					<view>
						<text class="page-title">{{ pet.name }} 的档案</text>
						<text class="page-subtitle">资料完整度 {{ completeness.completeness || 0 }}%</text>
					</view>
					<button class="danger-button" @click="removePet">删除档案</button>
				</view>

				<view class="content-grid pet-detail-layout">
					<view class="profile-column">
					<view class="card panel">
						<text class="panel-title">基础资料</text>
						<view class="avatar-editor">
							<view class="avatar-preview" @click="chooseAvatar">
								<image v-if="base.avatar" :src="assetUrl(base.avatar)" mode="aspectFill" />
								<text v-else>{{ petEmoji(base.pet_type) }}</text>
							</view>
							<view class="avatar-copy">
								<text class="avatar-title">宠物头像</text>
								<text class="avatar-desc">上传 JPG、PNG 或 WEBP 图片，用于档案和首页展示</text>
								<button class="secondary-button" :loading="uploadingAvatar" :disabled="uploadingAvatar" @click="chooseAvatar">
									{{ uploadingAvatar ? '上传中...' : '上传宠物图片' }}
								</button>
							</view>
						</view>

						<view class="form-grid">
							<label v-for="field in baseFields" :key="field.key" class="form-field">
								<text>{{ field.label }}</text>
								<input v-model="base[field.key]" :type="field.type || 'text'" />
							</label>
						</view>
						<view class="button-row">
							<button class="action-button" @click="saveBase">保存基础资料</button>
						</view>
					</view>

					<view class="card panel">
						<text class="panel-title">成长记录</text>
						<view v-if="!growth.length" class="empty-inline">还没有成长记录</view>
						<view v-else class="data-list">
							<view v-for="item in growth" :key="item.id" class="data-row">
								<view class="data-main">
									<text class="data-title">{{ item.title || growthTypeLabel(item.record_type) }}</text>
									<text class="data-meta">{{ item.content || '无补充内容' }}</text>
								</view>
								<button class="danger-button" @click="deleteGrowth(item.id)">删除</button>
							</view>
						</view>
						<view class="form-grid">
							<label class="form-field">
								<text>记录类型</text>
								<picker :range="growthTypeOptions" range-key="label" :value="growthTypeIndex" @change="selectGrowthType">
									<view class="picker-value">{{ growthTypeLabel(growthForm.record_type) }}</view>
								</picker>
							</label>
							<label class="form-field"><text>标题</text><input v-model="growthForm.title" /></label>
							<label class="form-field full"><text>内容</text><textarea v-model="growthForm.content" /></label>
						</view>
						<view class="button-row">
							<button class="action-button" @click="addGrowth">添加记录</button>
						</view>
					</view>

					<view class="card panel">
						<text class="panel-title">健康提醒</text>
						<view v-if="!reminders.length" class="empty-inline">还没有健康提醒</view>
						<view v-else class="data-list">
							<view v-for="item in reminders" :key="item.id" class="data-row">
								<view class="data-main">
									<text class="data-title">{{ item.title }}</text>
									<text class="data-meta">{{ item.due_at }} · {{ item.status }}</text>
								</view>
								<button class="secondary-button" @click="completeReminder(item)">完成</button>
								<button class="danger-button" @click="deleteReminder(item.id)">删除</button>
							</view>
						</view>
						<view class="form-grid">
							<label class="form-field">
								<text>提醒类型</text>
								<picker :range="reminderTypeOptions" range-key="label" :value="reminderTypeIndex" @change="selectReminderType">
									<view class="picker-value">{{ reminderTypeLabel(reminderForm.reminder_type) }}</view>
								</picker>
							</label>
							<label class="form-field"><text>标题</text><input v-model="reminderForm.title" /></label>
							<label class="form-field full"><text>时间（ISO 格式）</text><input v-model="reminderForm.due_at" placeholder="2026-07-30T09:00:00" /></label>
						</view>
						<view class="button-row">
							<button class="action-button" @click="addReminder">添加提醒</button>
						</view>
					</view>
					</view>

					<view class="detail-column">
					<view class="card panel">
						<text class="panel-title">健康与偏好</text>
						<view class="form-grid">
							<label v-for="field in detailFields" :key="field.key" class="form-field" :class="{ full: field.full }">
								<text>{{ field.label }}</text>
								<textarea v-if="field.full" v-model="detail[field.key]" />
								<input v-else v-model="detail[field.key]" />
							</label>
						</view>
						<view class="button-row">
							<button class="action-button" @click="saveDetail">保存详细资料</button>
							<button class="secondary-button" @click="previewDocument">预览知识文档</button>
						</view>
					</view>
					</view>
				</view>
			</template>
		</view>
	</AppShell>
</template>

<script>
import AppShell from '../../components/AppShell.vue'
import StatePanel from '../../components/StatePanel.vue'
import { assetUrl, petApi, systemApi } from '../../api'

export default {
	components: { AppShell, StatePanel },
	data() {
		return {
			id: null,
			pet: null,
			base: {},
			detail: {},
			growth: [],
			reminders: [],
			completeness: {},
			loading: true,
			uploadingAvatar: false,
			growthForm: { record_type: 'note', title: '', content: '' },
			reminderForm: { reminder_type: 'health', title: '', due_at: '' },
			growthTypeOptions: [
				{ label: '日常记录', value: 'note' },
				{ label: '体重记录', value: 'weight' },
				{ label: '饮食记录', value: 'diet' },
				{ label: '运动记录', value: 'exercise' },
				{ label: '就医记录', value: 'medical' },
				{ label: '洗护记录', value: 'grooming' }
			],
			reminderTypeOptions: [
				{ label: '健康提醒', value: 'health' },
				{ label: '疫苗提醒', value: 'vaccine' },
				{ label: '驱虫提醒', value: 'deworm' },
				{ label: '复诊提醒', value: 'checkup' },
				{ label: '用药提醒', value: 'medicine' },
				{ label: '洗护提醒', value: 'grooming' }
			],
			baseFields: [
				{ key: 'name', label: '名字' },
				{ key: 'pet_type', label: '类型' },
				{ key: 'breed', label: '品种' },
				{ key: 'gender', label: '性别' },
				{ key: 'weight', label: '体重', type: 'number' },
				{ key: 'vaccine_status', label: '疫苗状态' },
				{ key: 'deworm_status', label: '驱虫状态' }
			],
			detailFields: [
				{ key: 'body_size', label: '体型' },
				{ key: 'health_notes', label: '健康说明', full: true },
				{ key: 'allergy_notes', label: '过敏说明', full: true },
				{ key: 'diet_preference', label: '饮食偏好', full: true },
				{ key: 'product_preference', label: '用品偏好', full: true },
				{ key: 'behavior_notes', label: '行为特点', full: true },
				{ key: 'care_notes', label: '照护说明', full: true }
			]
		}
	},
	onLoad(query) {
		this.id = query.id
		this.load()
	},
	computed: {
		growthTypeIndex() {
			return Math.max(0, this.growthTypeOptions.findIndex(item => item.value === this.growthForm.record_type))
		},
		reminderTypeIndex() {
			return Math.max(0, this.reminderTypeOptions.findIndex(item => item.value === this.reminderForm.reminder_type))
		}
	},
	methods: {
		assetUrl,
		petEmoji(type) {
			return String(type || '').toLowerCase().includes('cat') || String(type || '').includes('猫') ? '🐱' : '🐶'
		},
		growthTypeLabel(value) {
			return (this.growthTypeOptions.find(item => item.value === value) || this.growthTypeOptions[0]).label
		},
		reminderTypeLabel(value) {
			return (this.reminderTypeOptions.find(item => item.value === value) || this.reminderTypeOptions[0]).label
		},
		selectGrowthType(event) {
			this.growthForm.record_type = this.growthTypeOptions[Number(event.detail.value) || 0].value
		},
		selectReminderType(event) {
			this.reminderForm.reminder_type = this.reminderTypeOptions[Number(event.detail.value) || 0].value
		},
		async load() {
			this.loading = true
			const result = await Promise.allSettled([
				petApi.detail(this.id),
				petApi.detailProfile(this.id),
				petApi.listGrowthRecords(this.id),
				petApi.listReminders(this.id),
				petApi.profileCompleteness(this.id)
			])
			if (result[0].status === 'fulfilled') {
				this.pet = result[0].value
				this.base = { ...result[0].value }
			}
			if (result[1].status === 'fulfilled') this.detail = { ...result[1].value }
			if (result[2].status === 'fulfilled') this.growth = result[2].value || []
			if (result[3].status === 'fulfilled') this.reminders = result[3].value || []
			if (result[4].status === 'fulfilled') this.completeness = result[4].value || {}
			this.loading = false
		},
		chooseAvatar() {
			if (this.uploadingAvatar) return
			uni.chooseImage({
				count: 1,
				sizeType: ['compressed'],
				sourceType: ['album', 'camera'],
				success: async response => {
					const filePath = response.tempFilePaths && response.tempFilePaths[0]
					if (!filePath) return
					this.uploadingAvatar = true
					try {
						const uploaded = await systemApi.uploadImage(filePath, 'pet')
						this.base.avatar = uploaded.file_url
						await this.saveBase()
						uni.showToast({ title: '宠物图片已上传' })
					} finally {
						this.uploadingAvatar = false
					}
				}
			})
		},
		async saveBase() {
			try {
				const data = {}
				this.baseFields.forEach(field => {
					data[field.key] = this.base[field.key] || null
				})
				data.avatar = this.base.avatar || null
				if (data.weight) data.weight = Number(data.weight)
				this.pet = await petApi.update(this.id, data)
				uni.showToast({ title: '基础资料已保存' })
				this.load()
			} catch (error) {}
		},
		async saveDetail() {
			try {
				await petApi.updateDetailProfile(this.id, this.detail)
				uni.showToast({ title: '详细资料已保存' })
				this.load()
			} catch (error) {}
		},
		async addGrowth() {
			if (!this.growthForm.record_type) return uni.showToast({ title: '请填写记录类型', icon: 'none' })
			try {
				await petApi.createGrowthRecord(this.id, this.growthForm)
				this.growthForm = { record_type: 'note', title: '', content: '' }
				uni.showToast({ title: '成长记录已添加' })
				this.load()
			} catch (error) {}
		},
		async deleteGrowth(id) {
			try {
				await petApi.deleteGrowthRecord(this.id, id)
				uni.showToast({ title: '记录已删除' })
				this.load()
			} catch (error) {}
		},
		async addReminder() {
			if (!this.reminderForm.title || !this.reminderForm.due_at) {
				return uni.showToast({ title: '请填写提醒标题和时间', icon: 'none' })
			}
			try {
				await petApi.createReminder(this.id, this.reminderForm)
				this.reminderForm = { reminder_type: 'health', title: '', due_at: '' }
				uni.showToast({ title: '提醒已添加' })
				this.load()
			} catch (error) {}
		},
		async completeReminder(item) {
			try {
				await petApi.updateReminder(this.id, item.id, { status: 'completed' })
				uni.showToast({ title: '提醒已完成' })
				this.load()
			} catch (error) {}
		},
		async deleteReminder(id) {
			try {
				await petApi.deleteReminder(this.id, id)
				uni.showToast({ title: '提醒已删除' })
				this.load()
			} catch (error) {}
		},
		async previewDocument() {
			try {
				const response = await petApi.previewProfileDocument(this.id)
				uni.showModal({ title: '档案文档预览', content: response.content, showCancel: false })
			} catch (error) {}
		},
		async removePet() {
			uni.showModal({
				title: '删除宠物档案',
				content: '删除后相关资料也会受到影响，确认继续吗？',
				success: async result => {
					if (!result.confirm) return
					try {
						await petApi.remove(this.id)
						uni.showToast({ title: '档案已删除' })
						setTimeout(() => uni.navigateBack(), 400)
					} catch (error) {}
				}
			})
		}
	}
}
</script>

<style scoped lang="scss">
.pet-detail-layout{align-items:start}.profile-column,.detail-column{display:flex;min-width:0;flex-direction:column;gap:16px}.pet-detail-layout .form-field{min-width:0}.avatar-editor{display:flex;align-items:center;gap:18px;margin:14px 0 20px;padding:16px;border:1px solid var(--color-border);border-radius:12px;background:#fffaf6}.avatar-preview{display:flex;width:112px;height:112px;flex:none;align-items:center;justify-content:center;overflow:hidden;border-radius:18px;background:linear-gradient(145deg,#fff0df,#f4dfca);font-size:48px;cursor:pointer}.avatar-preview image{display:block;width:100%;height:100%;object-fit:cover}.avatar-copy{display:flex;min-width:0;flex:1;flex-direction:column;align-items:flex-start}.avatar-title{font-size:16px;font-weight:800}.avatar-desc{margin:6px 0 12px;color:var(--color-text-secondary);font-size:12px;line-height:1.6}.avatar-copy button{margin:0}.form-field picker,.form-field :deep(uni-picker){display:block;width:100%;max-width:100%;min-width:0;box-sizing:border-box}.picker-value{overflow:hidden;color:var(--color-text);font-size:14px;line-height:20px;text-overflow:ellipsis;white-space:nowrap}
@media(max-width:900px){.profile-column,.detail-column{gap:12px}.avatar-editor{align-items:flex-start}.avatar-preview{width:88px;height:88px;border-radius:14px;font-size:38px}}
</style>
