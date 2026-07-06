<template>
	<AppShell active="agent"><view class="page-container">
		<view class="page-heading"><view><text class="page-title">AI 智能导购</text><text class="page-subtitle">推荐只引用商城真实商品，不编造库存与价格</text></view></view>
		<view class="card guide">
			<view class="messages"><view v-if="!messages.length" class="empty-inline">描述宠物类型、年龄、需求和预算，开始获取推荐</view><view v-for="(m,i) in messages" :key="i" class="message" :class="m.role"><text>{{m.content}}</text></view></view>
			<view v-if="recommendations.length" class="recommendations"><view v-for="item in recommendations" :key="item.product_id" class="card recommendation" @click="detail(item.product_id)"><text class="data-title">#{{item.rank}} {{item.product.title}}</text><text class="data-meta">{{item.reason}}</text><text v-if="item.caution" class="caution">{{item.caution}}</text></view></view>
			<view class="composer"><input v-model="input" placeholder="例如：2 岁柯基，需要低敏狗粮，预算 300 元" @confirm="send"/><button class="action-button" :loading="sending" @click="send">发送</button></view>
		</view>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue';import{aiApi}from'../../api'
export default{components:{AppShell},data(){return{sessionId:null,input:'',messages:[],recommendations:[],sending:false}},methods:{async send(){const content=this.input.trim();if(!content||this.sending)return;this.messages.push({role:'user',content});this.input='';this.sending=true;try{if(!this.sessionId)this.sessionId=(await aiApi.createGuideSession({})).id;const r=await aiApi.sendGuideMessage(this.sessionId,{content,limit:5});this.messages.push(r.assistant_message);this.recommendations=r.recommendations||[];uni.showToast({title:'推荐已更新'})}catch(e){}finally{this.sending=false}},detail(id){uni.navigateTo({url:`/pages/mall/detail?id=${id}`})}}}
</script>
<style scoped>.guide{padding:22px}.messages{min-height:260px}.message{max-width:76%;margin:12px 0;padding:12px 15px;border-radius:14px;background:#f7f2ed;font-size:13px;line-height:1.7}.message.user{margin-left:auto;background:var(--color-primary);color:#fff}.recommendations{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0}.recommendation{padding:15px}.caution{display:block;margin-top:8px;color:var(--color-warning);font-size:10px}.composer{display:flex;gap:10px;padding-top:16px;border-top:1px solid var(--color-border)}.composer input{flex:1;height:40px;padding:0 14px;border:1px solid var(--color-border);border-radius:20px}@media(max-width:767px){.recommendations{grid-template-columns:1fr}}</style>
