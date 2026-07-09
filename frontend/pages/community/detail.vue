<template>
	<AppShell active="community">
		<view class="page-container community-detail-page">
			<view v-if="loading" class="card empty-inline">正在加载动态...</view>
			<StatePanel v-else-if="!post" icon="-" title="动态不存在" action="返回社区" @action="back" />
			<template v-else>
				<view class="detail-layout">
					<view class="card post-panel">
						<view class="author">
							<text class="avatar">宠</text>
							<view>
								<text class="data-title">宠友 {{ post.user_id }}</text>
								<text class="data-meta">{{ formatTime(post.created_at) }}</text>
							</view>
							<button v-if="!post.can_delete" class="secondary-button compact" @click="toggleFollow">
								{{ post.following_author ? '取消关注' : '关注' }}
							</button>
						</view>
						<text class="content">{{ post.content || '分享了一组宠物照片' }}</text>
						<view class="media">
							<video v-for="media in videos" :key="media.id" :src="assetUrl(media.file_url)" class="post-video" controls />
							<image v-for="media in images" :key="media.id" :src="assetUrl(media.file_url)" mode="aspectFill" />
							<view v-if="!images.length && !videos.length" class="media-placeholder">宠物日常</view>
						</view>
						<view class="button-row">
							<button class="secondary-button" @click="toggleLike">点赞 {{ post.like_count }}</button>
							<button class="secondary-button" @click="toggleFavorite">收藏 {{ post.favorite_count }}</button>
							<button class="secondary-button">分享</button>
							<button v-if="post.can_delete" class="text-danger" @click="removePost">删除</button>
							<button v-else class="text-danger" @click="report">举报</button>
						</view>
					</view>

					<view class="card comments-panel">
						<text class="panel-title">评论 {{ comments.length }}</text>
						<view v-if="!comments.length" class="empty-comment">还没有评论，来聊两句吧。</view>
						<view v-else class="comment-list">
							<view v-for="item in comments" :key="item.id" class="comment-item" :class="{ reply: item.parent_id }">
								<view class="comment-avatar">用</view>
								<view class="comment-main">
									<view class="comment-head">
										<text>用户 {{ item.user_id }}</text>
										<text>{{ formatTime(item.created_at) }}</text>
									</view>
									<text v-if="item.parent_id" class="reply-target">回复 #{{ item.parent_id }}</text>
									<text class="comment-content">{{ item.content }}</text>
									<view class="comment-actions">
										<button @click="replyTo(item)">回复</button>
										<button class="weak-danger" @click="deleteComment(item.id)">删除</button>
									</view>
								</view>
							</view>
						</view>

						<view v-if="replyingTo" class="replying-bar">
							<text>正在回复 #{{ replyingTo.id }}</text>
							<button @click="cancelReply">取消</button>
						</view>
						<view class="comment-composer">
							<textarea v-model="comment" placeholder="输入你的评论..." />
							<button class="action-button" @click="sendComment">{{ replyingTo ? '发布回复' : '发布评论' }}</button>
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
import { assetUrl, communityApi } from '../../api'

export default {
	components: { AppShell, StatePanel },
	data() {
		return {
			id: null,
			post: null,
			comments: [],
			comment: '',
			replyingTo: null,
			loading: true
		}
	},
	onLoad(query) {
		this.id = query.id
		this.load()
	},
	computed: {
		images() {
			return (this.post?.media || []).filter(item => item.media_type !== 'video')
		},
		videos() {
			return (this.post?.media || []).filter(item => item.media_type === 'video')
		}
	},
	methods: {
		assetUrl,
		formatTime(value) {
			return value ? String(value).replace('T', ' ').slice(0, 16) : ''
		},
		async load() {
			this.loading = true
			const result = await Promise.allSettled([
				communityApi.detail(this.id),
				communityApi.comments(this.id)
			])
			this.post = result[0].status === 'fulfilled' ? result[0].value : null
			this.comments = result[1].status === 'fulfilled' ? result[1].value : []
			this.loading = false
		},
		async toggleLike() {
			await (this.post.liked_by_me ? communityApi.unlike(this.id) : communityApi.like(this.id))
			this.load()
		},
		async toggleFavorite() {
			await (this.post.favorited_by_me ? communityApi.unfavorite(this.id) : communityApi.favorite(this.id))
			this.load()
		},
		async toggleFollow() {
			await (this.post.following_author ? communityApi.unfollow(this.post.user_id) : communityApi.follow(this.post.user_id))
			this.load()
		},
		removePost() {
			uni.showModal({
				title: '删除动态',
				content: '确认删除这条动态吗？',
				success: async result => {
					if (!result.confirm) return
					await communityApi.remove(this.id)
					uni.showToast({ title: '动态已删除' })
					setTimeout(() => this.back(), 300)
				}
			})
		},
		replyTo(item) {
			this.replyingTo = item
			this.comment = ''
		},
		cancelReply() {
			this.replyingTo = null
		},
		async sendComment() {
			if (!this.comment.trim()) return
			const payload = { content: this.comment }
			if (this.replyingTo) payload.parent_id = this.replyingTo.id
			await communityApi.createComment(this.id, payload)
			this.comment = ''
			this.replyingTo = null
			this.load()
		},
		async deleteComment(id) {
			await communityApi.deleteComment(this.id, id)
			this.load()
		},
		report() {
			uni.showModal({
				title: '举报动态',
				editable: true,
				placeholderText: '请输入举报原因',
				success: async result => {
					if (!result.confirm || !result.content) return
					await communityApi.report(this.id, { target_type: 'post', target_id: Number(this.id), reason: result.content })
					uni.showToast({ title: '举报已提交' })
				}
			})
		},
		back() {
			uni.navigateBack()
		}
	}
}
</script>

<style scoped lang="scss">
.community-detail-page{max-width:1180px}.detail-layout{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(360px,.95fr);gap:24px}.post-panel,.comments-panel{padding:24px}.author{display:flex;align-items:center;gap:12px}.author .compact{margin-left:auto}.avatar,.comment-avatar{display:flex;align-items:center;justify-content:center;flex-shrink:0;border-radius:50%;background:var(--color-primary-soft);color:var(--color-primary);font-weight:900}.avatar{width:44px;height:44px}.content{display:block;margin:24px 0;font-size:16px;line-height:1.9}.media{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.media image,.post-video,.media-placeholder{width:100%;height:260px;overflow:hidden;border-radius:14px;background:#f7eee6}.media image{display:block;object-fit:cover}.post-video{grid-column:1/-1;height:360px}.media-placeholder{display:flex;grid-column:1/-1;align-items:center;justify-content:center;color:var(--color-primary);font-size:28px;font-weight:900}.text-danger{height:38px;margin:0;padding:0 10px;border:0;background:transparent;color:#d66767;font-size:12px;line-height:38px}.empty-comment{padding:24px;border-radius:12px;background:#fff8f2;color:var(--color-text-secondary);font-size:13px}.comment-list{display:grid;gap:16px}.comment-item{display:flex;gap:11px;padding-bottom:16px;border-bottom:1px solid var(--color-border)}.comment-item.reply{margin-left:28px;padding-left:12px;border-left:3px solid var(--color-primary-soft)}.comment-avatar{width:34px;height:34px;font-size:12px}.comment-main{flex:1;min-width:0}.comment-head{display:flex;justify-content:space-between;gap:12px}.comment-head text:first-child{font-size:13px;font-weight:800}.comment-head text:last-child{color:var(--color-text-secondary);font-size:10px}.reply-target{display:block;margin-top:6px;color:var(--color-primary);font-size:11px}.comment-content{display:block;margin-top:7px;color:var(--color-text);font-size:14px;line-height:1.7}.comment-actions{display:flex;gap:12px;margin-top:8px}.comment-actions button,.replying-bar button{height:auto;margin:0;padding:0;border:0;background:transparent;color:var(--color-primary);font-size:12px;line-height:1.4}.comment-actions .weak-danger{color:#d66767}.replying-bar{display:flex;align-items:center;justify-content:space-between;margin-top:16px;padding:10px 12px;border-radius:10px;background:var(--color-primary-soft);color:var(--color-primary);font-size:12px}.comment-composer{margin-top:16px}.comment-composer textarea{width:100%;min-height:88px;padding:12px;border:1px solid var(--color-border);border-radius:12px;background:#fff;font-size:14px}.comment-composer .action-button{margin-top:10px}@media(max-width:900px){.detail-layout{grid-template-columns:1fr}.media image,.media-placeholder{height:210px}.post-video{height:260px}}@media(max-width:560px){.media{grid-template-columns:1fr}.comment-item.reply{margin-left:8px}.post-panel,.comments-panel{padding:18px}}
</style>
