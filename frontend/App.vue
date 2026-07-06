<script>
export default {
	onLaunch() {
		console.log('PetMall launched')
	}
}
</script>

<style lang="scss">
@import "./styles/tokens.scss";

page {
	background: var(--color-bg);
	color: var(--color-text);
	font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
	font-size: 28rpx;
}

view, text, image, input, button, scroll-view, textarea {
	box-sizing: border-box;
}

button::after {
	border: 0;
}

.page-container {
	width: 100%;
	max-width: 1440px;
	margin: 0 auto;
	padding: 24px 28px 48px;
}

.section-title {
	display: flex;
	align-items: center;
	justify-content: space-between;
	margin: 28px 0 16px;
	font-size: 21px;
	font-weight: 700;
}

.section-more {
	color: var(--color-text-secondary);
	font-size: 14px;
	font-weight: 400;
}

.card {
	background: var(--color-surface);
	border: 1px solid var(--color-border);
	border-radius: var(--radius-lg);
	box-shadow: var(--shadow-card);
}

.primary-button {
	display: flex;
	align-items: center;
	justify-content: center;
	height: 48px;
	margin: 0;
	border-radius: var(--radius-pill);
	background: linear-gradient(135deg, #ff963f, #ff6b14);
	color: #fff;
	font-size: 16px;
	font-weight: 700;
	box-shadow: 0 8px 18px rgba(255, 107, 20, .2);
}

.muted {
	color: var(--color-text-secondary);
}

.page-heading {
	display: flex;
	align-items: flex-end;
	justify-content: space-between;
	gap: 16px;
	margin: 8px 0 22px;
}

.page-title {
	display: block;
	font-size: 28px;
	font-weight: 800;
}

.page-subtitle {
	display: block;
	margin-top: 7px;
	color: var(--color-text-secondary);
	font-size: 13px;
}

.content-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 16px;
}

.panel {
	padding: 22px;
}

.panel-title {
	display: block;
	margin-bottom: 16px;
	font-size: 18px;
	font-weight: 800;
}

.form-grid {
	display: grid;
	grid-template-columns: repeat(2, minmax(0, 1fr));
	gap: 14px;
}

.form-field {
	display: flex;
	flex-direction: column;
	gap: 7px;
	color: var(--color-text-secondary);
	font-size: 12px;
}

.form-field.full {
	grid-column: 1 / -1;
}

.form-field input,
.form-field textarea,
.form-field picker,
.form-control {
	width: 100%;
	min-height: 42px;
	padding: 10px 13px;
	border: 1px solid var(--color-border);
	border-radius: 11px;
	background: #fff;
	color: var(--color-text);
	font-size: 14px;
}

.form-field textarea {
	min-height: 100px;
}

.button-row {
	display: flex;
	flex-wrap: wrap;
	gap: 10px;
	margin-top: 18px;
}

.action-button,
.secondary-button,
.danger-button {
	height: 38px;
	margin: 0;
	padding: 0 18px;
	border-radius: 20px;
	font-size: 12px;
	line-height: 38px;
}

.action-button {
	background: var(--color-primary);
	color: #fff;
}

.secondary-button {
	border: 1px solid var(--color-border);
	background: #fff;
	color: var(--color-text);
}

.danger-button {
	background: #fff0f0;
	color: var(--color-danger);
}

.data-list {
	display: flex;
	flex-direction: column;
}

.data-row {
	display: flex;
	align-items: center;
	gap: 14px;
	padding: 16px 0;
}

.data-row + .data-row {
	border-top: 1px solid var(--color-border);
}

.data-main {
	flex: 1;
	min-width: 0;
}

.data-title,
.data-meta {
	display: block;
}

.data-title {
	font-size: 15px;
	font-weight: 700;
}

.data-meta {
	margin-top: 6px;
	color: var(--color-text-secondary);
	font-size: 11px;
	line-height: 1.6;
}

.status-chip {
	padding: 4px 9px;
	border-radius: 12px;
	background: var(--color-primary-soft);
	color: var(--color-primary);
	font-size: 10px;
	white-space: nowrap;
}

.empty-inline {
	padding: 36px 16px;
	color: var(--color-text-secondary);
	text-align: center;
}

@media (max-width: 767px) {
	.page-container {
		padding: 12px 14px calc(82px + env(safe-area-inset-bottom));
	}

	.section-title {
		margin: 22px 0 12px;
		font-size: 18px;
	}

	.page-heading {
		align-items: flex-start;
		margin-top: 4px;
	}

	.page-title {
		font-size: 22px;
	}

	.content-grid,
	.form-grid {
		grid-template-columns: 1fr;
	}

	.form-field.full {
		grid-column: auto;
	}

	.panel {
		padding: 17px;
	}
}
</style>
