<template>
	<AppShell active="mall"><view class="page-container">
		<view class="page-heading"><view><text class="page-title">确认订单</text><text class="page-subtitle">请选择收货地址，订单将按商家自动拆分</text></view></view>
		<view class="card panel">
			<text class="panel-title">收货地址</text>
			<view v-if="loading" class="empty-inline">正在加载地址…</view>
			<StatePanel v-else-if="!addresses.length" icon="⌖" title="请先添加收货地址" action="管理地址" @action="goAddress"/>
			<view v-else class="address-grid"><view v-for="item in addresses" :key="item.id" class="address" :class="{active:addressId===item.id}" @click="addressId=item.id"><text>{{item.receiver_name}}　{{item.receiver_phone}}</text><text>{{item.province}}{{item.city}}{{item.district}}{{item.detail_address}}</text></view></view>
			<view class="button-row"><button class="secondary-button" @click="goAddress">管理地址</button><button class="action-button" :loading="submitting" @click="submit">提交订单</button></view>
		</view>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue';import StatePanel from '../../components/StatePanel.vue';import{userApi,orderApi}from'../../api'
export default{components:{AppShell,StatePanel},data(){return{cartItemIds:[],addresses:[],addressId:null,loading:true,submitting:false}},onLoad(q){this.cartItemIds=String(q.items||'').split(',').map(Number).filter(Boolean)},onShow(){this.load()},methods:{async load(){this.loading=true;try{this.addresses=await userApi.listAddresses()||[];this.addressId=this.addressId||this.addresses.find(v=>v.is_default)?.id||this.addresses[0]?.id}catch(e){}finally{this.loading=false}},goAddress(){uni.navigateTo({url:'/pages/address/index'})},async submit(){if(!this.addressId||!this.cartItemIds.length)return uni.showToast({title:'地址或商品无效',icon:'none'});this.submitting=true;try{const orders=await orderApi.create({address_id:this.addressId,cart_item_ids:this.cartItemIds});uni.showToast({title:'订单已创建'});setTimeout(()=>uni.redirectTo({url:`/pages/order/detail?id=${orders[0].id}`}),400)}catch(e){}finally{this.submitting=false}}}}
</script>
<style scoped>.address-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:12px}.address{display:flex;flex-direction:column;gap:8px;padding:16px;border:1px solid var(--color-border);border-radius:12px;font-size:12px}.address.active{border-color:var(--color-primary);background:var(--color-primary-soft)}@media(max-width:767px){.address-grid{grid-template-columns:1fr}}</style>
