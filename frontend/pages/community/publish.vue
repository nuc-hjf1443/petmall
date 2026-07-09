<template>
	<AppShell active="community">
		<view class="page-container">
			<view class="page-heading">
				<view>
					<text class="page-title">发布动态</text>
					<text class="page-subtitle">最多 9 张图片，或一个 MP4 视频</text>
				</view>
			</view>
			<view class="card panel">
				<label class="form-field">
					<text>分享内容</text>
					<textarea v-model="content" maxlength="2000" placeholder="记录今天与毛孩子的故事..." />
				</label>

				<text class="label">选择话题</text>
				<view class="topics">
					<view
						v-for="item in topicOptions"
						:key="item.key"
						:class="{ active: selectedTopicKey === item.key }"
						@click="selectTopic(item)"
					>
						{{ item.label }}
					</view>
				</view>

				<text class="label">媒体文件 {{ filePaths.length }}/9</text>
				<view class="files">
					<view v-for="(path, index) in filePaths" :key="path">
						<image :src="path" mode="aspectFill" />
						<text @click="filePaths.splice(index, 1)">x</text>
					</view>
					<view class="picker" @click="choose">+</view>
				</view>
				<view class="button-row">
					<button class="action-button" :loading="publishing" @click="publish">发布动态</button>
				</view>
			</view>
		</view>
	</AppShell>
</template>

<script>
import AppShell from '../../components/AppShell.vue'
import { communityApi } from '../../api'

export default {
	components: { AppShell },
	data() {
		return {
			content: '',
			topics: [],
			defaultTopicNames: ['猫咪', '狗狗', '领养故事', '养宠经验'],
			selectedTopicKey: '',
			selectedTopicId: null,
			selectedTopicName: '',
			filePaths: [],
			publishing: false
		}
	},
	computed: {
		topicOptions() {
			const defaultOptions = this.defaultTopicNames.map(name => {
				const topic = this.topics.find(item => item.name === name)
				return {
					key: `topic:${name}`,
					label: `# ${name}`,
					id: topic?.id || null,
					name
				}
			})
			const extraOptions = this.topics
				.filter(topic => !this.defaultTopicNames.includes(topic.name))
				.map(topic => ({
					key: `topic:${topic.id}`,
					label: `# ${topic.name}`,
					id: topic.id,
					name: topic.name
				}))
			return [
				...defaultOptions,
				...extraOptions,
				{ key: 'other', label: '# 其他', id: null }
			]
		}
	},
	onLoad() {
		communityApi.topics()
			.then(value => {
				this.topics = value || []
			})
			.catch(() => {})
	},
	methods: {
		selectTopic(item) {
			if (this.selectedTopicKey === item.key) {
				this.selectedTopicKey = ''
				this.selectedTopicId = null
				this.selectedTopicName = ''
				return
			}
			this.selectedTopicKey = item.key
			this.selectedTopicId = item.id
			this.selectedTopicName = item.name || ''
		},
		choose() {
			uni.chooseImage({
				count: 9 - this.filePaths.length,
				success: result => this.filePaths.push(...result.tempFilePaths)
			})
		},
		async publish() {
			if (!this.content.trim() && !this.filePaths.length) {
				return uni.showToast({ title: '请填写内容或选择图片', icon: 'none' })
			}
			this.publishing = true
			try {
				const topicIds = this.selectedTopicId ? [this.selectedTopicId] : []
				const topicNames = !this.selectedTopicId && this.selectedTopicName ? [this.selectedTopicName] : []
				const post = await communityApi.publish({
					content: this.content,
					topicIds,
					topicNames,
					filePaths: this.filePaths
				})
				uni.showToast({ title: '动态已发布' })
				setTimeout(() => uni.redirectTo({ url: `/pages/community/detail?id=${post.id}` }), 400)
			} catch (error) {
			} finally {
				this.publishing = false
			}
		}
	}
}
</script>

<style scoped>
.label{display:block;margin:20px 0 10px;font-size:13px;font-weight:700}.topics{display:flex;flex-wrap:wrap;gap:8px}.topics view{padding:7px 12px;border-radius:15px;background:#f5f1ed;color:var(--color-text-secondary);font-size:11px}.topics view.active{background:var(--color-primary-soft);color:var(--color-primary);font-weight:800}.files{display:flex;flex-wrap:wrap;gap:10px}.files view{position:relative;width:90px;height:90px;overflow:hidden;border-radius:10px}.files image{display:block;width:100%;height:100%;object-fit:cover}.files view>text{position:absolute;top:-6px;right:-6px;display:flex;width:20px;height:20px;align-items:center;justify-content:center;border-radius:50%;background:#333;color:#fff}.files .picker{display:flex;align-items:center;justify-content:center;border:1px dashed var(--color-border);border-radius:10px;color:#aaa;font-size:30px}
</style>
