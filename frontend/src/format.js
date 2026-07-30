export function flt(v) {
	const n = parseFloat(v);
	return Number.isFinite(n) ? n : 0;
}

export function round2(v) {
	return Math.round(flt(v) * 100) / 100;
}

// 1234.5 -> "1,234.50"
export function money(v) {
	return round2(v).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

// crypto.randomUUID() only works in a secure context (HTTPS/localhost) - this
// test site is plain HTTP, so fall back to a Math.random()-based id. Only
// needs to be unique per submission attempt, not cryptographically secure.
export function generateRequestId() {
	if (window.crypto && typeof window.crypto.randomUUID === "function") {
		return window.crypto.randomUUID();
	}
	return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
		const r = (Math.random() * 16) | 0;
		const v = c === "x" ? r : (r & 0x3) | 0x8;
		return v.toString(16);
	});
}
