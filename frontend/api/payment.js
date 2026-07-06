import { request } from './request'

export const paymentApi = {
	create: orderId => request({
		url: `/payments/orders/${orderId}/pay`,
		method: 'POST',
		auth: true
	}),
	confirmMock: outTradeNo => request({
		url: `/payments/mock/${encodeURIComponent(outTradeNo)}/confirm`,
		method: 'POST',
		auth: true
	}),
	alipayPage: outTradeNo => request({
		url: `/payments/alipay/${encodeURIComponent(outTradeNo)}/page-pay`,
		auth: true
	}),
	alipayNotify: data => request({
		url: '/payments/alipay/notify',
		method: 'POST',
		data,
		header: { 'Content-Type': 'application/x-www-form-urlencoded' }
	}),
	alipayReturn: outTradeNo => request({
		url: '/payments/alipay/return',
		data: { out_trade_no: outTradeNo }
	}),
	result: outTradeNo => request({
		url: `/payments/${encodeURIComponent(outTradeNo)}/result`,
		auth: true
	}),
	query: outTradeNo => request({
		url: `/payments/${encodeURIComponent(outTradeNo)}/query`,
		method: 'POST',
		auth: true
	})
}
