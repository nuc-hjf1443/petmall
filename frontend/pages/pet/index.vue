<template>
	<AppShell active="profile">
		<view class="page-container">
			<view class="page-head">
				<view>
					<text class="title">宠物档案</text>
					<text class="subtitle">认真记录，陪它健康长大</text>
				</view>
				<button class="add" @click="showAdd = true">+ 添加宠物</button>
			</view>

			<StatePanel v-if="!loggedIn" icon="🔒" title="登录后管理宠物档案" description="宠物资料仅你本人可见" action="去登录" @action="goLogin" />
			<StatePanel v-else-if="error" icon="!" title="档案加载失败" :description="error" action="重试" @action="load" />
			<StatePanel v-else-if="!pets.length" icon="🐾" title="还没有宠物档案" description="从名字开始，记录你们的故事" action="添加第一只宠物" @action="showAdd = true" />

			<view v-else class="pet-grid">
				<view v-for="pet in pets" :key="pet.id" class="pet-card card" @click="detail(pet.id)">
					<view class="cover">
						<image v-if="pet.avatar" :src="assetUrl(pet.avatar)" mode="aspectFill" />
						<text v-else>{{ petEmoji(pet.pet_type) }}</text>
					</view>
					<view class="pet-info">
						<view class="name-row">
							<text class="name">{{ pet.name }}</text>
							<text class="gender">{{ pet.gender || '未填写' }}</text>
						</view>
						<text class="meta">{{ pet.breed || pet.pet_type }} · {{ pet.weight ? `${pet.weight} kg` : '体重待记录' }}</text>
						<view class="health-row">
							<text>疫苗：{{ pet.vaccine_status || '待完善' }}</text>
							<text>驱虫：{{ pet.deworm_status || '待完善' }}</text>
						</view>
						<view class="actions">
							<button>成长记录</button>
							<button>健康资料</button>
						</view>
					</view>
				</view>
			</view>

			<view v-if="showAdd" class="modal-mask" @click.self="closeAdd">
				<view class="modal card">
					<text class="modal-title">添加宠物</text>
					<view class="avatar-upload">
						<view class="avatar-preview" @click="chooseCreateAvatar">
							<image v-if="form.avatar" :src="assetUrl(form.avatar)" mode="aspectFill" />
							<text v-else>{{ petEmoji(form.pet_type) }}</text>
						</view>
						<button class="secondary-button" :loading="uploadingAvatar" :disabled="uploadingAvatar" @click="chooseCreateAvatar">
							{{ uploadingAvatar ? '上传中...' : '上传宠物图片' }}
						</button>
					</view>
					<view class="pet-form-field"><text>名字</text><input v-model="form.name" placeholder="它叫什么？" /></view>
					<view class="pet-form-field">
						<text>类型</text>
						<picker :range="petTypeOptions" @change="form.pet_type = petTypeOptions[$event.detail.value]">
							<view>{{ form.pet_type }}</view>
						</picker>
					</view>
					<view class="modal-actions">
						<button @click="closeAdd">取消</button>
						<button class="confirm" @click="createPet">保存档案</button>
					</view>
				</view>
			</view>
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
			pets: [],
			error: '',
			showAdd: false,
			uploadingAvatar: false,
			petTypeOptions: ['狗', '猫', '其他'],
			form: { name: '', pet_type: '狗', avatar: '' }
		}
	},
	computed: {
		loggedIn() {
			return !!uni.getStorageSync('access_token')
		}
	},
	onShow() {
		if (this.loggedIn) this.load()
	},
	methods: {
		assetUrl,
		petEmoji(type) {
			return String(type || '').toLowerCase().includes('cat') || String(type || '').includes('猫') ? '🐱' : '🐶'
		},
		goLogin() {
			uni.navigateTo({ url: '/pages/auth/login' })
		},
		detail(id) {
			uni.navigateTo({ url: `/pages/pet/detail?id=${id}` })
		},
		closeAdd() {
			this.showAdd = false
			this.form = { name: '', pet_type: '狗', avatar: '' }
		},
		async load() {
			this.error = ''
			try {
				this.pets = await petApi.list() || []
			} catch (error) {
				this.error = error.message
			}
		},
		chooseCreateAvatar() {
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
						this.form.avatar = uploaded.file_url
						uni.showToast({ title: '宠物图片已上传' })
					} finally {
						this.uploadingAvatar = false
					}
				}
			})
		},
		async createPet() {
			if (!this.form.name) return uni.showToast({ title: '请填写宠物名字', icon: 'none' })
			try {
				await petApi.create(this.form)
				this.closeAdd()
				this.load()
				uni.showToast({ title: '档案已创建' })
			} catch (error) {}
		}
	}
}
</script>

<style scoped lang="scss">
.page-head{display:flex;align-items:center;justify-content:space-between;margin:12px 0 24px}.title,.subtitle{display:block}.title{font-size:30px;font-weight:800}.subtitle{margin-top:7px;color:var(--color-text-secondary);font-size:13px}.add{margin:0;padding:0 20px;border-radius:22px;background:var(--color-primary);color:#fff;font-size:13px}.pet-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}.pet-card{display:grid;overflow:hidden;grid-template-columns:150px 1fr}.cover{display:flex;min-height:210px;align-items:center;justify-content:center;overflow:hidden;background:linear-gradient(145deg,#fff0df,#f4dfca);font-size:76px}.cover image{display:block;width:100%;height:100%;object-fit:cover}.pet-info{padding:20px}.name-row{display:flex;align-items:center;justify-content:space-between}.name{font-size:20px;font-weight:800}.gender{padding:3px 8px;border-radius:10px;background:#eef5ff;color:#5680ac;font-size:10px}.meta{display:block;margin-top:8px;color:var(--color-text-secondary);font-size:12px}.health-row{display:flex;flex-direction:column;gap:7px;margin-top:20px;color:#5f8a6f;font-size:11px}.actions{display:flex;gap:8px;margin-top:20px}.actions button{flex:1;height:32px;margin:0;padding:0;border:1px solid var(--color-border);border-radius:16px;background:#fff;color:var(--color-primary);font-size:10px;line-height:32px}.modal-mask{position:fixed;inset:0;z-index:100;display:flex;align-items:center;justify-content:center;padding:18px;background:rgba(39,29,21,.38)}.modal{width:430px;padding:28px}.modal-title{display:block;margin-bottom:20px;font-size:22px;font-weight:800}.avatar-upload{display:flex;align-items:center;gap:16px;margin-bottom:16px}.avatar-preview{display:flex;width:92px;height:92px;align-items:center;justify-content:center;overflow:hidden;border-radius:18px;background:linear-gradient(145deg,#fff0df,#f4dfca);font-size:42px}.avatar-preview image{display:block;width:100%;height:100%;object-fit:cover}.avatar-upload button{margin:0}.pet-form-field{display:flex;height:48px;align-items:center;margin-top:12px;padding:0 14px;border:1px solid var(--color-border);border-radius:12px}.pet-form-field>text{width:70px;flex-shrink:0;color:var(--color-text-secondary);font-size:13px}.pet-form-field input,.pet-form-field picker{min-width:0;flex:1;font-size:14px}.pet-form-field picker{line-height:48px}.modal-actions{display:flex;gap:12px;margin-top:22px}.modal-actions button{flex:1;height:42px;border-radius:21px;background:#f4f0ec;font-size:13px;line-height:42px}.modal-actions .confirm{background:var(--color-primary);color:#fff}
@media(max-width:1100px){.pet-grid{grid-template-columns:1fr 1fr}}@media(max-width:900px){.page-head{margin:5px 0 16px}.title{font-size:23px}.add{height:36px;line-height:36px}.pet-grid{grid-template-columns:1fr;gap:12px}.pet-card{grid-template-columns:115px 1fr}.cover{min-height:180px;font-size:58px}.pet-info{padding:15px}.modal{width:100%}}
</style>
