<template>
	<AppShell active="profile">
		<view class="page-container product-edit-page">
			<view class="page-heading">
				<view>
					<text class="page-title">{{ id ? '编辑商品' : '发布商品' }}</text>
					<text class="page-subtitle">{{ id ? '更新商品基础资料' : '填写完成后将以草稿状态保存，可继续修改后提交审核' }}</text>
				</view>
				<button class="secondary-button" @click="back">返回商家中心</button>
			</view>

			<view class="form-section card">
				<view class="section-heading">
					<view class="section-index">1</view>
					<view>
						<text class="section-name">基础信息</text>
						<text class="section-description">用于商品展示和分类检索</text>
					</view>
				</view>
				<view class="form-grid">
					<view class="form-field category-field">
						<text>商品分类 <text class="required">*</text></text>
						<view class="select-control" :class="{ open: categoryOpen }" @click="categoryOpen=!categoryOpen">
							<text :class="{ placeholder: !categoryId }">{{ categoryName }}</text>
							<text class="select-arrow">⌄</text>
						</view>
						<view v-if="categoryOpen" class="category-options">
							<view v-if="!categories.length" class="category-empty">暂无可用分类</view>
							<view
								v-for="item in categories"
								:key="item.id"
								class="category-option"
								:class="{ active: categoryId === item.id }"
								@click.stop="selectCategory(item)"
							>
								<text>{{ item.name }}</text>
								<text v-if="categoryId === item.id">✓</text>
							</view>
						</view>
					</view>
					<label class="form-field">
						<text>适用宠物</text>
						<input v-model.trim="form.applicable_pet_type" maxlength="64" placeholder="例如：猫、犬、猫犬通用" />
					</label>
					<label class="form-field full">
						<text>商品标题 <text class="required">*</text></text>
						<input v-model.trim="form.title" maxlength="255" placeholder="请输入清晰、简洁的商品标题" />
					</label>
					<label class="form-field full">
						<text>商品描述</text>
						<textarea v-model.trim="form.description" maxlength="2000" placeholder="介绍商品特点、适用场景和使用说明" />
						<text class="field-hint">{{ (form.description || '').length }}/2000</text>
					</label>
				</view>
			</view>

			<view v-if="!id" class="form-section card">
				<view class="section-heading">
					<view class="section-index">2</view>
					<view>
						<text class="section-name">规格与库存</text>
						<text class="section-description">当前版本先创建一个默认 SKU</text>
					</view>
				</view>
				<view class="form-grid">
					<label class="form-field">
						<text>SKU 编码 <text class="required">*</text></text>
						<input v-model.trim="sku.sku_code" maxlength="64" placeholder="例如：FOOD-CAT-001" />
					</label>
					<label class="form-field">
						<text>规格名称 <text class="required">*</text></text>
						<input v-model.trim="sku.name" maxlength="128" placeholder="例如：鸡肉味 1.5kg" />
					</label>
					<label class="form-field">
						<text>销售价格 <text class="required">*</text></text>
						<view class="input-with-suffix">
							<input v-model.number="priceYuan" type="digit" placeholder="0.00" />
							<text>元</text>
						</view>
					</label>
					<label class="form-field">
						<text>库存数量 <text class="required">*</text></text>
						<view class="input-with-suffix">
							<input v-model.number="sku.stock" type="number" placeholder="0" />
							<text>件</text>
						</view>
					</label>
				</view>
			</view>

			<view v-if="!id" class="form-section card">
				<view class="section-heading">
					<view class="section-index">3</view>
					<view>
						<text class="section-name">商品图片</text>
						<text class="section-description">当前版本使用图片 URL，后续可接入上传服务</text>
					</view>
				</view>
				<label class="form-field">
					<text>主图 URL <text class="required">*</text></text>
					<input v-model.trim="imageUrl" maxlength="512" placeholder="https://example.com/product.jpg" />
				</label>
				<view v-if="imageUrl" class="image-preview">
					<image :src="imageUrl" mode="aspectFill" @error="imagePreviewError=true" @load="imagePreviewError=false" />
					<text v-if="imagePreviewError">图片无法加载，请检查 URL</text>
				</view>
			</view>

			<view class="submit-bar">
				<text>带 <text class="required">*</text> 的项目为必填项</text>
				<view class="submit-actions">
					<button class="secondary-button" @click="back">取消</button>
					<button class="action-button save-button" :loading="saving" :disabled="saving" @click="save">
						{{ saving ? '保存中…' : '保存商品' }}
					</button>
				</view>
			</view>
		</view>
	</AppShell>
</template>

<script>
import AppShell from '../../components/AppShell.vue'
import { merchantApi, productApi } from '../../api'

export default {
	components: { AppShell },
	data() {
		return {
			id: null,
			categories: [],
			categoryId: null,
			categoryOpen: false,
			priceYuan: null,
			form: {
				title: '',
				description: '',
				applicable_pet_type: ''
			},
			sku: {
				sku_code: '',
				name: '',
				price: 0,
				stock: 0,
				specs: {},
				is_enabled: true
			},
			imageUrl: '',
			imagePreviewError: false,
			saving: false
		}
	},
	computed: {
		categoryName() {
			return this.categories.find(item => item.id === this.categoryId)?.name || '请选择商品分类'
		}
	},
	onLoad(query) {
		this.id = query.id || null
		productApi.categories()
			.then(categories => {
				this.categories = categories || []
			})
			.catch(() => {})
	},
	methods: {
		selectCategory(item) {
			this.categoryId = item.id
			this.categoryOpen = false
		},
		back() {
			uni.navigateBack()
		},
		async save() {
			if (!this.form.title) {
				return uni.showToast({ title: '请填写商品标题', icon: 'none' })
			}
			if (!this.id && (!this.categoryId || !this.sku.sku_code || !this.sku.name || !this.imageUrl)) {
				return uni.showToast({ title: '请完整填写必填项', icon: 'none' })
			}
			const price = Math.round(Number(this.priceYuan) * 100)
			if (!this.id && (this.priceYuan === null || this.priceYuan === '' || !Number.isFinite(price) || price < 0)) {
				return uni.showToast({ title: '请填写正确的销售价格', icon: 'none' })
			}
			if (!this.id && (!Number.isInteger(Number(this.sku.stock)) || Number(this.sku.stock) < 0)) {
				return uni.showToast({ title: '请填写正确的库存数量', icon: 'none' })
			}

			this.saving = true
			try {
				if (this.id) {
					await merchantApi.updateProduct(this.id, this.form)
				} else {
					await merchantApi.createProduct({
						...this.form,
						category_id: this.categoryId,
						skus: [{ ...this.sku, price, stock: Number(this.sku.stock) }],
						images: [{ image_url: this.imageUrl, is_primary: true, sort_order: 0 }]
					})
				}
				uni.showToast({ title: '商品已保存' })
				setTimeout(() => uni.navigateBack(), 400)
			} catch (error) {
				// 请求层统一展示错误信息。
			} finally {
				this.saving = false
			}
		}
	}
}
</script>

<style scoped>
.product-edit-page{max-width:1120px}.page-heading{align-items:center}.form-section{margin-bottom:16px;padding:24px}.section-heading{display:flex;align-items:center;gap:12px;margin-bottom:22px;padding-bottom:17px;border-bottom:1px solid var(--color-border)}.section-index{display:flex;width:32px;height:32px;align-items:center;justify-content:center;flex-shrink:0;border-radius:50%;background:var(--color-primary-soft);color:var(--color-primary);font-size:14px;font-weight:800}.section-name,.section-description{display:block}.section-name{font-size:17px;font-weight:800}.section-description{margin-top:4px;color:var(--color-text-secondary);font-size:11px}.required{color:var(--color-danger)}.category-field{position:relative;z-index:3}.select-control{display:flex;width:100%;min-height:42px;align-items:center;justify-content:space-between;padding:10px 13px;border:1px solid var(--color-border);border-radius:11px;background:#fff;color:var(--color-text);font-size:14px;cursor:pointer;transition:.2s}.select-control.open{border-color:var(--color-primary);box-shadow:0 0 0 3px var(--color-primary-soft)}.select-control .placeholder{color:#999}.select-arrow{color:var(--color-text-secondary);font-size:18px;transition:.2s}.select-control.open .select-arrow{transform:rotate(180deg)}.category-options{position:absolute;top:70px;right:0;left:0;z-index:10;overflow:hidden;padding:6px;border:1px solid var(--color-border);border-radius:12px;background:#fff;box-shadow:0 14px 34px rgba(56,38,22,.16)}.category-option,.category-empty{display:flex;min-height:40px;align-items:center;justify-content:space-between;padding:8px 11px;border-radius:8px;color:var(--color-text);font-size:13px}.category-option{cursor:pointer}.category-option:hover,.category-option.active{background:var(--color-primary-soft);color:var(--color-primary)}.category-empty{color:var(--color-text-secondary)}.form-field input,.form-field textarea{transition:border-color .2s,box-shadow .2s}.form-field input:focus,.form-field textarea:focus{border-color:var(--color-primary);box-shadow:0 0 0 3px var(--color-primary-soft);outline:none}.form-field textarea{min-height:120px}.field-hint{align-self:flex-end;margin-top:-2px;color:#aaa;font-size:10px}.input-with-suffix{display:flex;align-items:center;border:1px solid var(--color-border);border-radius:11px;background:#fff;transition:.2s}.input-with-suffix:focus-within{border-color:var(--color-primary);box-shadow:0 0 0 3px var(--color-primary-soft)}.input-with-suffix input{min-width:0;flex:1;border:0;box-shadow:none}.input-with-suffix input:focus{border:0;box-shadow:none}.input-with-suffix>text{padding-right:13px;color:var(--color-text-secondary);font-size:12px}.image-preview{position:relative;width:180px;height:135px;margin-top:14px;overflow:hidden;border:1px solid var(--color-border);border-radius:12px;background:#f7f3ef}.image-preview image{width:100%;height:100%}.image-preview>text{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:15px;background:#f7f3ef;color:var(--color-danger);font-size:11px;text-align:center}.submit-bar{position:sticky;bottom:16px;z-index:5;display:flex;align-items:center;justify-content:space-between;gap:20px;padding:14px 18px;border:1px solid var(--color-border);border-radius:16px;background:rgba(255,255,255,.94);box-shadow:0 10px 32px rgba(56,38,22,.12);backdrop-filter:blur(10px)}.submit-bar>text{color:var(--color-text-secondary);font-size:11px}.submit-actions{display:flex;gap:10px}.save-button{min-width:120px}.action-button[disabled]{opacity:.65}
@media(max-width:767px){.form-section{padding:17px}.page-heading{align-items:flex-start}.page-heading>.secondary-button{height:34px;padding:0 13px;line-height:34px}.submit-bar{bottom:74px;padding:11px 12px}.submit-bar>text{display:none}.submit-actions{width:100%}.submit-actions button{flex:1}.image-preview{width:140px;height:105px}}
</style>
