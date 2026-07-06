<template>
	<AppShell active="profile"><view class="page-container">
		<view v-if="loading" class="card empty-inline">正在加载订单…</view>
		<StatePanel v-else-if="!order" icon="⚠" title="订单不存在" action="返回订单列表" @action="goList"/>
		<template v-else>
			<view class="page-heading"><view><text class="page-title">订单详情</text><text class="page-subtitle">{{order.order_no}}</text></view><text class="status-chip">{{order.status}}</text></view>
			<view class="content-grid">
				<view class="card panel"><text class="panel-title">商品清单</text><view class="data-list"><view v-for="item in order.items" :key="item.id" class="data-row"><view class="data-main"><text class="data-title">{{item.product_title}}</text><text class="data-meta">{{item.sku_name}} × {{item.quantity}}</text></view><text>{{money(item.subtotal)}}</text></view></view></view>
				<view class="card panel"><text class="panel-title">订单信息</text>
					<view class="info"><text>收件人</text><text>{{order.address_snapshot.receiver_name}} {{order.address_snapshot.receiver_phone}}</text></view>
					<view class="info"><text>地址</text><text>{{address}}</text></view>
					<view class="info"><text>应付金额</text><text class="price">{{money(order.pay_amount)}}</text></view>
					<view class="button-row">
						<button v-if="order.status==='pending_payment'" class="action-button" :loading="working" @click="pay">立即支付</button>
						<button v-if="order.status==='pending_payment'" class="danger-button" @click="cancel">取消订单</button>
						<button v-if="order.status==='shipped'" class="action-button" @click="confirm">确认收货</button>
						<button class="secondary-button" @click="goList">订单列表</button>
					</view>
				</view>
			</view>
		</template>
	</view></AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue';import StatePanel from '../../components/StatePanel.vue';import{orderApi,paymentApi}from'../../api';import{formatMoney}from'../../utils/format'
export default{components:{AppShell,StatePanel},data(){return{id:null,order:null,loading:true,working:false}},computed:{address(){const a=this.order?.address_snapshot||{};return `${a.province||''}${a.city||''}${a.district||''}${a.detail_address||''}`}},onLoad(q){this.id=q.id;this.load()},methods:{money:formatMoney,async load(){this.loading=true;try{this.order=await orderApi.detail(this.id)}catch(e){this.order=null}finally{this.loading=false}},async pay(){this.working=true;try{const p=await paymentApi.create(this.id);if(p.payment_mode==='mock'){await paymentApi.confirmMock(p.out_trade_no);uni.showToast({title:'模拟支付成功'})}else if(p.pay_url){if(typeof window!=='undefined'){window.location.href=p.pay_url;return}uni.setClipboardData({data:p.pay_url});uni.showToast({title:'支付链接已复制',icon:'none'})}setTimeout(()=>uni.navigateTo({url:`/pages/payment/result?out_trade_no=${p.out_trade_no}`}),400)}catch(e){}finally{this.working=false}},async cancel(){try{this.order=await orderApi.cancel(this.id);uni.showToast({title:'订单已取消'})}catch(e){}},async confirm(){try{this.order=await orderApi.confirmReceipt(this.id);uni.showToast({title:'已确认收货'})}catch(e){}},goList(){uni.redirectTo({url:'/pages/order/index'})}}}
</script>
<style scoped>.info{display:flex;justify-content:space-between;gap:18px;padding:11px 0;color:var(--color-text-secondary);font-size:12px}.info text:last-child{color:var(--color-text);text-align:right}.info .price{color:var(--color-primary);font-size:20px;font-weight:800}</style>
