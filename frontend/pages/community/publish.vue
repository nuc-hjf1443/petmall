<template>
	<AppShell active="community"><view class="page-container">
		<view class="page-heading"><view><text class="page-title">发布动态</text><text class="page-subtitle">最多 9 张图片，或一个 MP4 视频</text></view></view>
		<view class="card panel">
			<label class="form-field"><text>分享内容</text><textarea v-model="content" maxlength="2000" placeholder="记录今天与毛孩子的故事…"/></label>
			<text class="label">选择话题</text><view class="topics"><view v-for="item in topics" :key="item.id" :class="{active:topicIds.includes(item.id)}" @click="toggleTopic(item.id)"># {{item.name}}</view></view>
			<text class="label">媒体文件 {{filePaths.length}}/9</text><view class="files"><view v-for="(path,i) in filePaths" :key="path"><image :src="path" mode="aspectFill"/><text @click="filePaths.splice(i,1)">×</text></view><view class="picker" @click="choose">＋</view></view>
			<view class="button-row"><button class="action-button" :loading="publishing" @click="publish">发布动态</button></view>
		</view>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue';import{communityApi}from'../../api'
export default{components:{AppShell},data(){return{content:'',topics:[],topicIds:[],filePaths:[],publishing:false}},onLoad(){communityApi.topics().then(v=>this.topics=v||[]).catch(()=>{})},methods:{toggleTopic(id){const i=this.topicIds.indexOf(id);if(i>=0)this.topicIds.splice(i,1);else this.topicIds.push(id)},choose(){uni.chooseImage({count:9-this.filePaths.length,success:r=>this.filePaths.push(...r.tempFilePaths)})},async publish(){if(!this.content.trim()&&!this.filePaths.length)return uni.showToast({title:'请填写内容或选择图片',icon:'none'});this.publishing=true;try{const post=await communityApi.publish({content:this.content,topicIds:this.topicIds,filePaths:this.filePaths});uni.showToast({title:'动态已发布'});setTimeout(()=>uni.redirectTo({url:`/pages/community/detail?id=${post.id}`}),400)}catch(e){}finally{this.publishing=false}}}}
</script>
<style scoped>.label{display:block;margin:20px 0 10px;font-size:13px;font-weight:700}.topics{display:flex;flex-wrap:wrap;gap:8px}.topics view{padding:7px 12px;border-radius:15px;background:#f5f1ed;color:var(--color-text-secondary);font-size:11px}.topics view.active{background:var(--color-primary-soft);color:var(--color-primary)}.files{display:flex;flex-wrap:wrap;gap:10px}.files view{position:relative;width:90px;height:90px}.files image{width:100%;height:100%;border-radius:10px}.files view>text{position:absolute;top:-6px;right:-6px;display:flex;width:20px;height:20px;align-items:center;justify-content:center;border-radius:50%;background:#333;color:#fff}.files .picker{display:flex;align-items:center;justify-content:center;border:1px dashed var(--color-border);border-radius:10px;color:#aaa;font-size:30px}</style>
