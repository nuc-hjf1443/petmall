export function formatMoney(cents) {
	const value = Number(cents || 0)
	return `¥${(value / 100).toFixed(2)}`
}

export function resolveImage(url, fallback) {
	return url || fallback
}
