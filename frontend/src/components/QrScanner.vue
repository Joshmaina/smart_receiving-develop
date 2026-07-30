<template>
	<div class="qr-scanner-overlay" @click.self="$emit('close')">
		<div class="qr-scanner-panel">
			<div class="qr-scanner-header">
				<span>Scan the receipt's QR code</span>
				<button type="button" class="qr-scanner-close" @click="$emit('close')">&times;</button>
			</div>
			<div class="qr-scanner-video-wrap">
				<video ref="videoEl" autoplay playsinline muted></video>
				<div class="qr-scanner-frame"></div>
			</div>
			<p v-if="error" class="qr-scanner-error">{{ error }}</p>
			<p v-else class="qr-scanner-hint">Point the camera at the QR code - it's read automatically.</p>
		</div>
	</div>
</template>

<script setup>
import { onMounted, onBeforeUnmount, ref } from "vue";
import jsQR from "jsqr";

const emit = defineEmits(["scanned", "close"]);

const videoEl = ref(null);
const error = ref("");

let stream = null;
let canvas = null;
let ctx = null;
let rafId = null;
let stopped = false;

function stopCamera() {
	stopped = true;
	if (rafId) cancelAnimationFrame(rafId);
	if (stream) {
		stream.getTracks().forEach((track) => track.stop());
		stream = null;
	}
}

function tick() {
	if (stopped) return;
	const video = videoEl.value;
	if (video && video.readyState === video.HAVE_ENOUGH_DATA) {
		canvas.width = video.videoWidth;
		canvas.height = video.videoHeight;
		ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
		const imageData = ctx.getImageData(0, 0, canvas.width, canvas.height);
		const code = jsQR(imageData.data, imageData.width, imageData.height);
		if (code && code.data) {
			stopCamera();
			emit("scanned", code.data);
			return;
		}
	}
	rafId = requestAnimationFrame(tick);
}

onMounted(async () => {
	canvas = document.createElement("canvas");
	ctx = canvas.getContext("2d", { willReadFrequently: true });

	if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
		error.value = "Camera access isn't available in this browser (requires HTTPS).";
		return;
	}

	try {
		stream = await navigator.mediaDevices.getUserMedia({
			video: { facingMode: { ideal: "environment" } },
		});
		videoEl.value.srcObject = stream;
		rafId = requestAnimationFrame(tick);
	} catch (e) {
		error.value = "Could not access the camera: " + (e.message || e.name || "permission denied");
	}
});

onBeforeUnmount(() => {
	stopCamera();
});
</script>

<style scoped>
.qr-scanner-overlay {
	position: fixed;
	inset: 0;
	background: rgba(0, 0, 0, 0.7);
	display: flex;
	align-items: center;
	justify-content: center;
	z-index: 1000;
}
.qr-scanner-panel {
	background: var(--card-bg, #fff);
	border-radius: 10px;
	padding: 16px;
	width: 100%;
	max-width: 420px;
}
.qr-scanner-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	font-weight: 600;
	margin-bottom: 12px;
}
.qr-scanner-close {
	border: none;
	background: transparent;
	font-size: 22px;
	line-height: 1;
	cursor: pointer;
	padding: 0 4px;
}
.qr-scanner-video-wrap {
	position: relative;
	width: 100%;
	aspect-ratio: 1 / 1;
	background: #000;
	border-radius: 8px;
	overflow: hidden;
}
.qr-scanner-video-wrap video {
	width: 100%;
	height: 100%;
	object-fit: cover;
}
.qr-scanner-frame {
	position: absolute;
	inset: 12%;
	border: 3px solid #fff;
	border-radius: 8px;
	box-shadow: 0 0 0 999px rgba(0, 0, 0, 0.25);
	pointer-events: none;
}
.qr-scanner-hint,
.qr-scanner-error {
	margin: 12px 0 0;
	text-align: center;
	font-size: 13px;
}
.qr-scanner-error {
	color: var(--red-500, #c0392b);
}
</style>
