<template>
	<AppShell active="profile"><view class="page-container">
		<view class="page-heading"><view><text class="page-title">收货地址</text><text class="page-subtitle">订单会保存地址快照，修改不会影响历史订单</text></view><button class="action-button" @click="startCreate">新增地址</button></view>
		<view class="content-grid">
			<view class="card panel">
				<text class="panel-title">地址列表</text>
				<view v-if="loading" class="empty-inline">正在加载地址…</view>
				<StatePanel v-else-if="!items.length" icon="⌖" title="还没有收货地址" description="新增地址后即可提交商城订单" action="新增地址" @action="startCreate"/>
				<view v-else class="data-list"><view v-for="item in items" :key="item.id" class="data-row">
					<view class="data-main"><text class="data-title">{{item.receiver_name}}　{{item.receiver_phone}}</text><text class="data-meta">{{item.province}}{{item.city}}{{item.district}}{{item.detail_address}}</text></view>
					<text v-if="item.is_default" class="status-chip">默认</text>
					<button class="secondary-button" @click="edit(item)">编辑</button>
					<button v-if="!item.is_default" class="secondary-button" @click="setDefault(item.id)">设为默认</button>
					<button class="danger-button" @click="remove(item.id)">删除</button>
				</view></view>
			</view>
			<view class="card panel">
				<text class="panel-title">{{form.id?'编辑地址':'新增地址'}}</text>
				<view class="form-grid">
					<label class="form-field"><text>收件人</text><input v-model="form.receiver_name"/></label>
					<label class="form-field"><text>手机号</text><input v-model="form.receiver_phone" maxlength="11"/></label>
					<label class="form-field"><text>省</text><input v-model="form.province"/></label>
					<label class="form-field"><text>市</text><input v-model="form.city"/></label>
					<label class="form-field"><text>区/县</text><input v-model="form.district"/></label>
					<label class="form-field"><text>邮编</text><input v-model="form.postal_code"/></label>
					<label class="form-field full"><text>详细地址</text><input v-model="form.detail_address"/></label>
				</view>
				<view class="button-row"><button class="action-button" :loading="saving" @click="save">保存</button><button class="secondary-button" @click="startCreate">清空</button></view>
			</view>
		</view>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue';import StatePanel from '../../components/StatePanel.vue';import{userApi}from'../../api'
const empty=()=>({id:null,receiver_name:'',receiver_phone:'',province:'',city:'',district:'',detail_address:'',postal_code:'',is_default:false})
export default{components:{AppShell,StatePanel},data(){return{items:[],form:empty(),loading:true,saving:false}},onShow(){this.load()},methods:{
	async load(){this.loading=true;try{this.items=await userApi.listAddresses()||[]}catch(e){}finally{this.loading=false}},
	startCreate(){this.form=empty()},edit(item){this.form={...item}},
	async save(){const required=['receiver_name','receiver_phone','province','city','district','detail_address'];if(required.some(k=>!this.form[k]))return uni.showToast({title:'请完整填写地址',icon:'none'});this.saving=true;try{const data={...this.form};delete data.id;if(this.form.id)await userApi.updateAddress(this.form.id,data);else await userApi.createAddress(data);uni.showToast({title:'地址已保存'});this.startCreate();this.load()}catch(e){}finally{this.saving=false}},
	async setDefault(id){try{await userApi.setDefaultAddress(id);uni.showToast({title:'默认地址已更新'});this.load()}catch(e){}},
	async remove(id){try{await userApi.deleteAddress(id);uni.showToast({title:'地址已删除'});this.load()}catch(e){}}
}}
</script>
