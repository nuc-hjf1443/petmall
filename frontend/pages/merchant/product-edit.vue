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
						<view class="category-cascader">
							<view class="category-select">
								<view class="select-control" :class="{ open: categoryOpen.first }" @click="toggleCategory('first')">
									<text :class="{ placeholder: !firstCategoryId }">{{ firstCategoryName }}</text>
									<text class="select-arrow">⌄</text>
								</view>
								<view v-if="categoryOpen.first" class="category-options">
									<view v-if="!firstCategories.length" class="category-empty">暂无一级分类</view>
									<view v-for="item in firstCategories" :key="item.id" class="category-option" :class="{ active: firstCategoryId === item.id }" @click.stop="selectFirstCategory(item)">
										<text>{{ item.name }}</text>
										<text v-if="firstCategoryId === item.id">✓</text>
									</view>
								</view>
							</view>
							<view class="category-select">
								<view class="select-control" :class="{ open: categoryOpen.second, disabled: !firstCategoryId }" @click="toggleCategory('second')">
									<text :class="{ placeholder: !secondCategoryId }">{{ secondCategoryName }}</text>
									<text class="select-arrow">⌄</text>
								</view>
								<view v-if="categoryOpen.second" class="category-options">
									<view v-if="!secondCategories.length" class="category-empty">请先选择一级分类</view>
									<view v-for="item in secondCategories" :key="item.id" class="category-option" :class="{ active: secondCategoryId === item.id }" @click.stop="selectSecondCategory(item)">
										<text>{{ item.name }}</text>
										<text v-if="secondCategoryId === item.id">✓</text>
									</view>
								</view>
							</view>
							<view class="category-select">
								<view class="select-control" :class="{ open: categoryOpen.third, disabled: !secondCategoryId }" @click="toggleCategory('third')">
									<text :class="{ placeholder: !categoryId }">{{ thirdCategoryName }}</text>
									<text class="select-arrow">⌄</text>
								</view>
								<view v-if="categoryOpen.third" class="category-options">
									<view v-if="!thirdCategories.length" class="category-empty">请先选择二级分类</view>
									<view v-for="item in thirdCategories" :key="item.id" class="category-option" :class="{ active: categoryId === item.id }" @click.stop="selectThirdCategory(item)">
										<text>{{ item.name }}</text>
										<text v-if="categoryId === item.id">✓</text>
									</view>
								</view>
							</view>
						</view>
						<text v-if="categoryId" class="category-path">{{ categoryName }}</text>
					</view>
					<view class="form-field">
						<text>适用宠物</text>
						<view class="choice-row">
							<view
								v-for="item in petTypeOptions"
								:key="item"
								class="choice-chip"
								:class="{ active: selectedPetTypeOption === item }"
								@click="selectPetTypeOption(item)"
							>
								{{ item }}
							</view>
						</view>
						<input
							v-if="selectedPetTypeOption === '其他'"
							v-model.trim="form.applicable_pet_type"
							maxlength="64"
							placeholder="请输入其他宠物类别"
						/>
					</view>
					<view class="form-field">
						<text>品牌</text>
						<view class="choice-row">
							<view
								v-for="item in brandOptions"
								:key="item"
								class="choice-chip"
								:class="{ active: selectedBrandOption === item }"
								@click="selectBrandOption(item)"
							>
								{{ item }}
							</view>
						</view>
						<input
							v-if="selectedBrandOption === '其他'"
							v-model.trim="form.brand"
							maxlength="100"
							placeholder="请输入其他品牌"
						/>
					</view>
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

			<view class="form-section card">
				<view class="section-heading">
					<view class="section-index">{{ id ? 2 : 3 }}</view>
					<view>
						<text class="section-name">商品图片</text>
						<text class="section-description">选择本地图片上传，保存后作为商城展示主图</text>
					</view>
				</view>
				<view class="upload-field">
					<text>商品主图 <text class="required">*</text></text>
					<view class="upload-box" @click="chooseImage">
						<image v-if="imageUrl" :src="displayImageUrl" mode="aspectFill" @error="imagePreviewError=true" @load="imagePreviewError=false" />
						<view v-else class="upload-placeholder">
							<text class="upload-plus">+</text>
							<text>选择本地图片</text>
						</view>
					</view>
					<view class="upload-actions">
						<button class="secondary-button" :loading="uploadingImage" :disabled="uploadingImage" @click.stop="chooseImage">
							{{ imageUrl ? '重新选择' : '上传图片' }}
						</button>
						<button v-if="imageUrl" class="secondary-button" @click.stop="clearImage">移除</button>
					</view>
					<text class="field-hint">支持 JPG、PNG、WEBP，上传后会作为商品封面保存</text>
				</view>
				<view v-if="imageUrl" class="image-preview">
					<image :src="displayImageUrl" mode="aspectFill" @error="imagePreviewError=true" @load="imagePreviewError=false" />
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
import { assetUrl, merchantApi, productApi, systemApi } from '../../api'

export default {
	components: { AppShell },
	data() {
		return {
			id: null,
			categories: [],
			categoryId: null,
			firstCategoryId: null,
			secondCategoryId: null,
			categoryOpen: {
				first: false,
				second: false,
				third: false
			},
			priceYuan: null,
			form: {
				title: '',
				description: '',
				brand: '',
				applicable_pet_type: ''
			},
			selectedPetTypeOption: '',
			selectedBrandOption: '',
			petTypeOptions: ['猫', '狗', '猫犬通用', '小宠', '水族', '其他'],
			brandOptions: ['皇家', '伯纳天纯', '麦富迪', '网易严选', 'pidan', '卫仕', '其他'],
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
			uploadingImage: false,
			saving: false
		}
	},
	computed: {
		displayImageUrl() {
			return assetUrl(this.imageUrl)
		},
		firstCategories() {
			return this.categories.filter(item => !item.parent_id)
		},
		secondCategories() {
			if (!this.firstCategoryId) return []
			return this.categories.filter(item => item.parent_id === this.firstCategoryId)
		},
		thirdCategories() {
			if (!this.secondCategoryId) return []
			return this.categories.filter(item => item.parent_id === this.secondCategoryId)
		},
		firstCategoryName() {
			return this.categories.find(item => item.id === this.firstCategoryId)?.name || '一级分类'
		},
		secondCategoryName() {
			return this.categories.find(item => item.id === this.secondCategoryId)?.name || '二级分类'
		},
		thirdCategoryName() {
			return this.categories.find(item => item.id === this.categoryId)?.name || '三级分类'
		},
		categoryName() {
			const selected = this.categories.find(item => item.id === this.categoryId)
			if (!selected) return '请选择商品分类'
			const names = [selected.name]
			let current = selected
			while (current.parent_id) {
				current = this.categories.find(item => item.id === current.parent_id)
				if (!current) break
				names.unshift(current.name)
			}
			return names.join(' / ')
		}
	},
	onLoad(query) {
		this.id = query.id || null
		productApi.categories()
			.then(categories => {
				this.categories = categories || []
				if (this.id) this.loadProduct()
			})
			.catch(() => {})
	},
	methods: {
		async loadProduct() {
			try {
				const response = await merchantApi.product(this.id)
				const product = response.product || response
				this.form.title = product.title || ''
				this.form.description = product.description || ''
				this.form.brand = product.brand || ''
				this.form.applicable_pet_type = product.applicable_pet_type || ''
				this.categoryId = product.category_id || null
				this.applyCategoryPath(product.category_id)
				this.syncChoiceOptions()
				const primary = (product.images || []).find(item => item.is_primary)
				const first = (product.images || [])[0]
				this.imageUrl = product.cover_image || (primary && primary.image_url) || (first && first.image_url) || ''
				this.imagePreviewError = false
			} catch (error) {
				uni.showToast({ title: '商品信息加载失败', icon: 'none' })
			}
		},
		applyCategoryPath(categoryId) {
			const third = this.categories.find(item => item.id === categoryId)
			if (!third) return
			this.categoryId = third.id
			this.secondCategoryId = third.parent_id || null
			const second = this.categories.find(item => item.id === this.secondCategoryId)
			this.firstCategoryId = second ? second.parent_id : null
		},
		syncChoiceOptions() {
			this.selectedPetTypeOption = this.petTypeOptions.includes(this.form.applicable_pet_type)
				? this.form.applicable_pet_type
				: (this.form.applicable_pet_type ? '其他' : '')
			this.selectedBrandOption = this.brandOptions.includes(this.form.brand)
				? this.form.brand
				: (this.form.brand ? '其他' : '')
		},
		closeCategoryDropdowns() {
			this.categoryOpen = { first: false, second: false, third: false }
		},
		toggleCategory(level) {
			if (level === 'second' && !this.firstCategoryId) return
			if (level === 'third' && !this.secondCategoryId) return
			this.categoryOpen = {
				first: level === 'first' ? !this.categoryOpen.first : false,
				second: level === 'second' ? !this.categoryOpen.second : false,
				third: level === 'third' ? !this.categoryOpen.third : false
			}
		},
		selectFirstCategory(item) {
			this.firstCategoryId = item.id
			this.secondCategoryId = null
			this.categoryId = null
			this.closeCategoryDropdowns()
		},
		selectSecondCategory(item) {
			this.secondCategoryId = item.id
			this.categoryId = null
			this.closeCategoryDropdowns()
		},
		selectThirdCategory(item) {
			this.categoryId = item.id
			this.closeCategoryDropdowns()
		},
		selectPetTypeOption(item) {
			this.selectedPetTypeOption = item
			this.form.applicable_pet_type = item === '其他' ? '' : item
		},
		selectBrandOption(item) {
			this.selectedBrandOption = item
			this.form.brand = item === '其他' ? '' : item
		},
		back() {
			uni.navigateBack()
		},
		chooseImage() {
			uni.chooseImage({
				count: 1,
				sizeType: ['compressed'],
				success: async result => {
					const filePath = result.tempFilePaths?.[0]
					if (!filePath) return
					this.uploadingImage = true
					try {
						const uploaded = await systemApi.uploadImage(filePath, 'product')
						this.imageUrl = uploaded.file_url
						this.imagePreviewError = false
					} catch (error) {
						// 请求层统一提示
					} finally {
						this.uploadingImage = false
					}
				}
			})
		},
		clearImage() {
			this.imageUrl = ''
			this.imagePreviewError = false
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
				const payloadForm = {
					...this.form,
					brand: this.form.brand || null,
					applicable_pet_type: this.form.applicable_pet_type || null
				}
				let savedProduct = null
				if (this.id) {
					const updatePayload = { ...payloadForm }
					if (this.imageUrl) {
						updatePayload.images = [{ image_url: this.imageUrl, is_primary: true, sort_order: 0 }]
					}
					const response = await merchantApi.updateProduct(this.id, updatePayload)
					savedProduct = response?.product
				} else {
					const response = await merchantApi.createProduct({
						...payloadForm,
						category_id: this.categoryId,
						skus: [{ ...this.sku, price, stock: Number(this.sku.stock) }],
						images: [{ image_url: this.imageUrl, is_primary: true, sort_order: 0 }]
					})
					savedProduct = response?.product
				}
				if (savedProduct?.id) {
					uni.setStorageSync('merchantProductChange', {
						id: savedProduct.id,
						type: this.id ? 'updated' : 'created',
						at: Date.now()
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
.product-edit-page{max-width:1120px}.page-heading{align-items:center}.form-section{margin-bottom:16px;padding:24px}.section-heading{display:flex;align-items:center;gap:12px;margin-bottom:22px;padding-bottom:17px;border-bottom:1px solid var(--color-border)}.section-index{display:flex;width:32px;height:32px;align-items:center;justify-content:center;flex-shrink:0;border-radius:50%;background:var(--color-primary-soft);color:var(--color-primary);font-size:14px;font-weight:800}.section-name,.section-description{display:block}.section-name{font-size:17px;font-weight:800}.section-description{margin-top:4px;color:var(--color-text-secondary);font-size:11px}.required{color:var(--color-danger)}.category-field{position:relative;z-index:3}.category-cascader{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px}.category-select{position:relative;min-width:0}.select-control{display:flex;width:100%;min-height:42px;align-items:center;justify-content:space-between;padding:10px 13px;border:1px solid var(--color-border);border-radius:11px;background:#fff;color:var(--color-text);font-size:14px;cursor:pointer;transition:.2s}.select-control.open{border-color:var(--color-primary);box-shadow:0 0 0 3px var(--color-primary-soft)}.select-control.disabled{cursor:not-allowed;background:#faf8f5;color:#aaa}.select-control .placeholder{color:#999}.select-arrow{color:var(--color-text-secondary);font-size:18px;transition:.2s}.select-control.open .select-arrow{transform:rotate(180deg)}.category-options{position:absolute;top:48px;right:0;left:0;z-index:10;max-height:260px;overflow:auto;padding:6px;border:1px solid var(--color-border);border-radius:12px;background:#fff;box-shadow:0 14px 34px rgba(56,38,22,.16)}.category-option,.category-empty{display:flex;min-height:40px;align-items:center;justify-content:space-between;padding:8px 11px;border-radius:8px;color:var(--color-text);font-size:13px}.category-option{cursor:pointer}.category-option:hover,.category-option.active{background:var(--color-primary-soft);color:var(--color-primary)}.category-empty{color:var(--color-text-secondary)}.category-path{display:block;margin-top:8px;color:var(--color-text-secondary);font-size:11px}.choice-row{display:flex;flex-wrap:wrap;gap:8px}.choice-chip{min-height:34px;padding:7px 13px;border:1px solid var(--color-border);border-radius:8px;background:#fff;color:var(--color-text-secondary);font-size:12px;line-height:18px;cursor:pointer}.choice-chip.active{border-color:var(--color-primary);background:var(--color-primary-soft);color:var(--color-primary);font-weight:800}.form-field input,.form-field textarea{transition:border-color .2s,box-shadow .2s}.form-field input:focus,.form-field textarea:focus{border-color:var(--color-primary);box-shadow:0 0 0 3px var(--color-primary-soft);outline:none}.form-field textarea{min-height:120px}.field-hint{align-self:flex-end;margin-top:-2px;color:#aaa;font-size:10px}.input-with-suffix{display:flex;align-items:center;border:1px solid var(--color-border);border-radius:11px;background:#fff;transition:.2s}.input-with-suffix:focus-within{border-color:var(--color-primary);box-shadow:0 0 0 3px var(--color-primary-soft)}.input-with-suffix input{min-width:0;flex:1;border:0;box-shadow:none}.input-with-suffix input:focus{border:0;box-shadow:none}.input-with-suffix>text{padding-right:13px;color:var(--color-text-secondary);font-size:12px}.upload-field{display:flex;flex-direction:column;align-items:flex-start;gap:10px}.upload-field>text:first-child{font-size:13px;color:var(--color-text-secondary)}.upload-box{display:flex;width:180px;height:135px;align-items:center;justify-content:center;overflow:hidden;border:1px dashed var(--color-primary);border-radius:12px;background:#fffaf6;cursor:pointer}.upload-box image{width:100%;height:100%}.upload-placeholder{display:flex;flex-direction:column;align-items:center;gap:6px;color:var(--color-primary);font-size:12px}.upload-plus{font-size:28px;line-height:1}.upload-actions{display:flex;gap:10px}.image-preview{position:relative;width:180px;height:135px;margin-top:14px;overflow:hidden;border:1px solid var(--color-border);border-radius:12px;background:#f7f3ef}.image-preview image{width:100%;height:100%}.image-preview>text{position:absolute;inset:0;display:flex;align-items:center;justify-content:center;padding:15px;background:#f7f3ef;color:var(--color-danger);font-size:11px;text-align:center}.submit-bar{position:sticky;bottom:16px;z-index:5;display:flex;align-items:center;justify-content:space-between;gap:20px;padding:14px 18px;border:1px solid var(--color-border);border-radius:16px;background:rgba(255,255,255,.94);box-shadow:0 10px 32px rgba(56,38,22,.12);backdrop-filter:blur(10px)}.submit-bar>text{color:var(--color-text-secondary);font-size:11px}.submit-actions{display:flex;gap:10px}.save-button{min-width:120px}.action-button[disabled]{opacity:.65}
@media(max-width:767px){.form-section{padding:17px}.page-heading{align-items:flex-start}.page-heading>.secondary-button{height:34px;padding:0 13px;line-height:34px}.category-cascader{grid-template-columns:1fr}.submit-bar{bottom:74px;padding:11px 12px}.submit-bar>text{display:none}.submit-actions{width:100%}.submit-actions button{flex:1}.image-preview{width:140px;height:105px}}
</style>
