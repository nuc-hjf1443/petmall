<template>
	<AppShell active="mall">
		<view class="page-container mall-page">
			<view class="page-heading">
				<view><text class="page-title">宠物商城</text><text class="page-subtitle">严选好物，认真照顾每一份陪伴</text></view>
				<view class="search-box">⌕ <input v-model="keyword" placeholder="搜索商品" confirm-type="search" @confirm="loadProducts" /></view>
			</view>
			<scroll-view class="category-scroll" scroll-x>
				<view class="category-row">
					<view class="category-chip" :class="{active: !categoryId}" @click="selectCategory(null)">全部</view>
					<view v-for="item in categories" :key="item.id" class="category-chip" :class="{active: categoryId === item.id}" @click="selectCategory(item.id)">{{ item.name }}</view>
				</view>
			</scroll-view>
			<view v-if="loading" class="product-grid">
				<view v-for="i in 8" :key="i" class="skeleton card"></view>
			</view>
			<StatePanel v-else-if="error" icon="⚠" title="商品加载失败" :description="error" action="重新加载" @action="loadProducts" />
			<StatePanel v-else-if="!products.length" icon="🛍" title="暂时没有商品" description="换个关键词或分类看看吧" />
			<view v-else class="product-grid">
				<view v-for="(product,index) in products" :key="product.id" class="product-card card" @click="detail(product.id)">
					<image v-if="product.cover_image" class="product-image" :src="product.cover_image" mode="aspectFill" />
					<view v-else class="product-image placeholder">{{ ['🥫','🦴','🧸','🧴','🍖'][index%5] }}</view>
					<view class="product-body">
						<text class="product-title">{{ product.title }}</text>
						<text class="product-tag">{{ product.applicable_pet_type || '猫犬通用' }}</text>
						<view class="product-bottom"><text class="price">{{ money(product.price) }}</text><button class="cart-add" @click.stop="detail(product.id)">＋</button></view>
					</view>
				</view>
			</view>
		</view>
	</AppShell>
</template>
<script>
import AppShell from '../../components/AppShell.vue'
import StatePanel from '../../components/StatePanel.vue'
import { productApi } from '../../api'
import { formatMoney } from '../../utils/format'
export default {
	components:{AppShell,StatePanel},
	data(){return{keyword:'',categoryId:null,categories:[],products:[],loading:true,error:''}},
	onLoad(){this.keyword=uni.getStorageSync('mall_keyword')||'';uni.removeStorageSync('mall_keyword');this.load()},
	methods:{
		money:formatMoney,
		async load(){await Promise.allSettled([productApi.categories().then(v=>this.categories=v||[]),this.loadProducts()])},
		async loadProducts(){
			this.loading=true
			this.error=''
			try {
				const params={page:1,page_size:24}
				if(this.keyword)params.keyword=this.keyword
				if(this.categoryId)params.category_id=this.categoryId
				const res=await productApi.list(params)
				this.products=res?.items||[]
			}catch(e){
				this.error=e.message
			}finally{
				this.loading=false
			}
		},
		selectCategory(id){this.categoryId=id;this.loadProducts()},
		detail(id){uni.navigateTo({url:`/pages/mall/detail?id=${id}`})}
	}
}
</script>
<style scoped lang="scss">
.page-heading{display:flex;align-items:flex-end;justify-content:space-between;margin:12px 0 24px}.page-title,.page-subtitle{display:block}.page-title{font-size:30px;font-weight:800}.page-subtitle{margin-top:8px;color:var(--color-text-secondary);font-size:14px}
.search-box{display:flex;align-items:center;width:330px;height:44px;padding:0 16px;border:1px solid var(--color-border);border-radius:23px;background:#fff;color:#999}.search-box input{width:100%;margin-left:8px;font-size:14px}
.category-scroll{width:100%;white-space:nowrap}.category-row{display:flex;gap:10px;padding-bottom:18px}.category-chip{padding:9px 20px;border:1px solid var(--color-border);border-radius:20px;background:#fff;color:var(--color-text-secondary);font-size:13px}.category-chip.active{border-color:var(--color-primary);background:var(--color-primary-soft);color:var(--color-primary);font-weight:700}
.product-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:18px}.product-card{overflow:hidden;transition:.2s}.product-card:hover{transform:translateY(-3px);box-shadow:0 12px 32px rgba(89,56,29,.12)}.product-image{width:100%;height:220px;background:#f7efe7}.placeholder{display:flex;align-items:center;justify-content:center;font-size:76px}.product-body{display:flex;flex-direction:column;padding:15px}.product-title{display:-webkit-box;overflow:hidden;min-height:42px;font-size:15px;font-weight:700;line-height:1.45;-webkit-box-orient:vertical;-webkit-line-clamp:2}.product-tag{align-self:flex-start;margin-top:8px;padding:3px 8px;border-radius:5px;background:#f7f3ef;color:#8a8179;font-size:10px}.product-bottom{display:flex;align-items:center;justify-content:space-between;margin-top:12px}.price{color:var(--color-primary);font-size:18px;font-weight:800}.cart-add{display:flex;width:30px;height:30px;align-items:center;justify-content:center;margin:0;border-radius:50%;background:var(--color-primary);color:#fff;font-size:18px;line-height:30px}.skeleton{height:330px;background:linear-gradient(90deg,#f7f0e9 25%,#fff8f2 37%,#f7f0e9 63%);background-size:400% 100%;animation:pulse 1.4s infinite}@keyframes pulse{0%{background-position:100% 0}100%{background-position:0 0}}
@media(max-width:1200px){.product-grid{grid-template-columns:repeat(4,1fr)}}@media(max-width:900px){.page-heading{display:block;margin:6px 0 14px}.page-title{font-size:23px}.page-subtitle{font-size:12px}.search-box{width:100%;margin-top:14px}.product-grid{grid-template-columns:repeat(2,1fr);gap:10px}.product-image{height:165px}.placeholder{font-size:55px}.product-body{padding:11px}.product-title{min-height:38px;font-size:13px}.price{font-size:16px}.skeleton{height:255px}}
</style>
