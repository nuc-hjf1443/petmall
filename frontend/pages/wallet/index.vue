<template>
	<AppShell active="profile"><view class="page-container wallet-page">
		<view class="wallet-head card">
			<view>
				<text class="page-title">账户余额</text>
				<text class="page-subtitle">充值支持本地测试支付和支付宝沙箱支付</text>
			</view>
			<view class="balance-box">
				<text>可用余额</text>
				<text>{{ money(wallet.balance) }}</text>
				<text>冻结 {{ money(wallet.frozen_balance) }}</text>
			</view>
		</view>

		<view class="content-grid">
			<view class="card panel">
				<text class="panel-title">充值</text>
				<view class="amount-grid">
					<view
						v-for="item in amounts"
						:key="item"
						:class="{ active: rechargeAmount === item }"
						@click="rechargeAmount = item"
					>{{ money(item) }}</view>
				</view>
				<input v-model.number="customAmount" class="input" type="number" placeholder="自定义金额，单位元" />
				<view class="pay-mode">
					<view :class="{ active: paymentMode === 'mock' }" @click="paymentMode = 'mock'">本地测试支付</view>
					<view :class="{ active: paymentMode === 'alipay_sandbox' }" @click="paymentMode = 'alipay_sandbox'">支付宝沙箱支付</view>
				</view>
				<button class="action-button block-button" :loading="recharging" @click="submitRecharge">确认充值</button>
			</view>

			<view class="card panel">
				<text class="panel-title">提现申请</text>
				<input v-model.number="withdrawForm.amountYuan" class="input" type="number" placeholder="提现金额，单位元" />
				<input v-model="withdrawForm.account_name" class="input" placeholder="支付宝实名姓名" />
				<input v-model="withdrawForm.alipay_account" class="input" placeholder="支付宝账号" />
				<button class="secondary-button block-button" :loading="withdrawing" @click="submitWithdrawal">提交审核</button>
				<text class="hint">提现为平台内模拟打款，通过后台审核后扣减冻结余额。</text>
			</view>
		</view>

		<view class="content-grid lower">
			<view class="card panel">
				<text class="panel-title">余额流水</text>
				<StatePanel v-if="!transactions.length" icon="-" title="暂无余额流水" />
				<view v-else class="data-list">
					<view v-for="item in transactions" :key="item.id" class="data-row">
						<view class="data-main">
							<text class="data-title">{{ typeLabel(item.type) }}</text>
							<text class="data-meta">{{ item.remark || item.source }} · 余额 {{ money(item.balance_after) }}</text>
						</view>
						<text :class="item.change_amount >= 0 ? 'income' : 'expense'">{{ signedMoney(item.change_amount) }}</text>
					</view>
				</view>
			</view>

			<view class="card panel">
				<text class="panel-title">提现记录</text>
				<StatePanel v-if="!withdrawals.length" icon="-" title="暂无提现记录" />
				<view v-else class="data-list">
					<view v-for="item in withdrawals" :key="item.id" class="data-row">
						<view class="data-main">
							<text class="data-title">{{ item.withdrawal_no }} · {{ money(item.amount) }}</text>
							<text class="data-meta">{{ item.account_name }} · {{ item.alipay_account }}</text>
						</view>
						<text class="status-chip">{{ statusLabel(item.status) }}</text>
					</view>
				</view>
			</view>
		</view>

		<view v-if="paymentDialogVisible" class="payment-mask">
			<view class="payment-dialog">
				<text class="payment-icon">{{ pendingPayment.status === 'paid' ? '✓' : '…' }}</text>
				<text class="payment-title">{{ pendingPayment.status === 'paid' ? '支付成功' : '支付进行中' }}</text>
				<text class="payment-desc">
					{{ pendingPayment.status === 'paid' ? '余额已更新，可返回原界面查看。' : '请在新打开的支付宝沙箱页面完成支付，完成后回到这里刷新支付状态。' }}
				</text>
				<view class="payment-meta">
					<text>交易号</text>
					<text>{{ pendingPayment.outTradeNo }}</text>
				</view>
				<view class="payment-actions">
					<button
						v-if="pendingPayment.status !== 'paid'"
						class="action-button"
						:loading="queryingPayment"
						@click="refreshPaymentStatus"
					>刷新支付状态</button>
					<button class="secondary-button" @click="closePaymentDialog">返回</button>
				</view>
			</view>
		</view>
	</view></AppShell>
</template>

<script>
import AppShell from '../../components/AppShell.vue'
import StatePanel from '../../components/StatePanel.vue'
import { paymentApi, walletApi } from '../../api'
import { formatMoney } from '../../utils/format'

export default {
	components: { AppShell, StatePanel },
	data() {
		return {
			wallet: {},
			transactions: [],
			withdrawals: [],
			amounts: [1000, 3000, 5000, 10000],
			rechargeAmount: 3000,
			customAmount: '',
			paymentMode: 'mock',
			withdrawForm: {
				amountYuan: '',
				account_name: '',
				alipay_account: ''
			},
			recharging: false,
			withdrawing: false,
			queryingPayment: false,
			paymentDialogVisible: false,
			pendingPayment: {
				outTradeNo: '',
				status: ''
			}
		}
	},
	onShow() {
		this.load()
	},
	methods: {
		money: formatMoney,
		signedMoney(value) {
			return `${value >= 0 ? '+' : '-'}${formatMoney(Math.abs(value))}`
		},
		typeLabel(type) {
			return {
				recharge: '充值入账',
				freeze_withdrawal: '提现冻结',
				withdrawal_paid: '提现通过',
				withdrawal_rejected: '提现退回'
			}[type] || type
		},
		statusLabel(status) {
			return { pending: '待审核', approved: '已通过', rejected: '已驳回' }[status] || status
		},
		async load() {
			const result = await Promise.allSettled([
				walletApi.account(),
				walletApi.transactions({ limit: 50 }),
				walletApi.withdrawals()
			])
			if (result[0].status === 'fulfilled') this.wallet = result[0].value || {}
			if (result[1].status === 'fulfilled') this.transactions = result[1].value || []
			if (result[2].status === 'fulfilled') this.withdrawals = result[2].value || []
		},
		selectedAmount() {
			const custom = Number(this.customAmount || 0)
			return custom > 0 ? Math.round(custom * 100) : this.rechargeAmount
		},
		async submitRecharge() {
			const amount = this.selectedAmount()
			if (!amount || amount < 100) return uni.showToast({ title: '充值金额至少 1 元', icon: 'none' })
			let cashierWindow = null
			if (this.paymentMode === 'alipay_sandbox') {
				// #ifdef H5
				cashierWindow = window.open('', '_blank')
				// #endif
			}
			this.recharging = true
			try {
				const result = await walletApi.recharge({ amount, payment_mode: this.paymentMode })
				const tradeNo = result.payment.out_trade_no
				if (this.paymentMode === 'mock') {
					await paymentApi.confirmMock(tradeNo)
					uni.showToast({ title: '充值成功' })
					await this.load()
				} else if (result.payment.pay_url) {
					this.openPaymentDialog(tradeNo)
					// #ifdef H5
					if (cashierWindow) cashierWindow.location.href = result.payment.pay_url
					else window.open(result.payment.pay_url, '_blank')
					// #endif
					// #ifndef H5
					uni.setClipboardData({ data: result.payment.pay_url })
					uni.showToast({ title: '支付链接已复制', icon: 'none' })
					// #endif
				} else {
					uni.navigateTo({ url: `/pages/payment/result?out_trade_no=${tradeNo}` })
				}
			} catch (error) {
				// #ifdef H5
				if (cashierWindow) cashierWindow.close()
				// #endif
				throw error
			} finally {
				this.recharging = false
			}
		},
		openPaymentDialog(outTradeNo) {
			this.pendingPayment = { outTradeNo, status: 'paying' }
			this.paymentDialogVisible = true
		},
		closePaymentDialog() {
			this.paymentDialogVisible = false
			this.pendingPayment = { outTradeNo: '', status: '' }
		},
		async refreshPaymentStatus() {
			if (!this.pendingPayment.outTradeNo) return
			this.queryingPayment = true
			try {
				const payment = await paymentApi.query(this.pendingPayment.outTradeNo)
				if (payment.status === 'paid') {
					this.pendingPayment = { outTradeNo: payment.out_trade_no, status: 'paid' }
					await this.load()
					uni.showToast({ title: '支付成功' })
				} else {
					uni.showToast({ title: '刷新成功', icon: 'none' })
				}
			} finally {
				this.queryingPayment = false
			}
		},
		async submitWithdrawal() {
			const amount = Math.round(Number(this.withdrawForm.amountYuan || 0) * 100)
			if (!amount || amount < 100) return uni.showToast({ title: '提现金额至少 1 元', icon: 'none' })
			if (!this.withdrawForm.account_name || !this.withdrawForm.alipay_account) {
				return uni.showToast({ title: '请填写支付宝账号信息', icon: 'none' })
			}
			this.withdrawing = true
			try {
				await walletApi.withdraw({
					amount,
					account_name: this.withdrawForm.account_name,
					alipay_account: this.withdrawForm.alipay_account
				})
				this.withdrawForm = { amountYuan: '', account_name: '', alipay_account: '' }
				uni.showToast({ title: '提现申请已提交' })
				await this.load()
			} finally {
				this.withdrawing = false
			}
		}
	}
}
</script>

<style scoped lang="scss">
.wallet-page{padding-bottom:24px}.wallet-head{display:flex;align-items:center;justify-content:space-between;padding:26px}.balance-box{display:flex;min-width:220px;flex-direction:column;gap:6px;text-align:right}.balance-box text:first-child,.balance-box text:last-child{color:var(--color-text-secondary);font-size:12px}.balance-box text:nth-child(2){color:var(--color-primary);font-size:34px;font-weight:800}.panel{padding:22px}.amount-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-top:18px}.amount-grid view,.pay-mode view{display:flex;height:42px;align-items:center;justify-content:center;border:1px solid var(--color-border);border-radius:8px;background:#fff;font-size:13px}.amount-grid view.active,.pay-mode view.active{border-color:var(--color-primary);background:var(--color-primary-soft);color:var(--color-primary);font-weight:800}.input{box-sizing:border-box;width:100%;height:42px;margin-top:12px;padding:0 12px;border:1px solid var(--color-border);border-radius:8px;background:#fff;font-size:13px}.pay-mode{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:12px}.block-button{width:100%;margin-top:14px}.hint{display:block;margin-top:12px;color:var(--color-text-secondary);font-size:11px}.lower{margin-top:18px}.income{color:var(--color-success);font-weight:800}.expense{color:var(--color-danger);font-weight:800}.payment-mask{position:fixed;z-index:99;top:0;right:0;bottom:0;left:0;display:flex;align-items:center;justify-content:center;padding:18px;background:rgba(31,28,25,.42)}.payment-dialog{box-sizing:border-box;width:min(430px,100%);padding:26px;border-radius:8px;background:#fff;text-align:center;box-shadow:0 18px 60px rgba(40,31,23,.18)}.payment-icon{display:flex;width:62px;height:62px;align-items:center;justify-content:center;margin:0 auto 16px;border-radius:50%;background:var(--color-primary-soft);color:var(--color-primary);font-size:34px;font-weight:800}.payment-title{display:block;font-size:20px;font-weight:800}.payment-desc{display:block;margin-top:10px;color:var(--color-text-secondary);font-size:13px;line-height:1.7}.payment-meta{display:grid;grid-template-columns:64px 1fr;gap:8px;margin-top:18px;padding:12px;border-radius:8px;background:#fffaf6;text-align:left;font-size:12px}.payment-meta text:first-child{color:var(--color-text-secondary)}.payment-meta text:last-child{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.payment-actions{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:20px}.payment-actions button{width:100%;margin:0}
@media(max-width:767px){.wallet-head{display:block;padding:20px}.balance-box{margin-top:18px;text-align:left}.content-grid{display:block}.content-grid .panel+.panel{margin-top:12px}.amount-grid{grid-template-columns:repeat(2,1fr)}.pay-mode{grid-template-columns:1fr}.payment-actions{grid-template-columns:1fr}}
</style>
