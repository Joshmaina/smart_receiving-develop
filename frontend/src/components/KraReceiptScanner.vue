<template>
	<div class="kra-scanner-card card p-3 mb-3 border-secondary">
		<h6 class="fw-bold mb-2 text-primary">🛡️ KRA eTIMS/TIMS Document Verification</h6>

		<!-- Mode Selector: Camera Scan vs File Upload vs Manual Entry -->
		<div class="btn-group btn-group-sm mb-3 w-100">
			<button
				type="button"
				class="btn"
				:class="scanMode === 'camera' ? 'btn-primary' : 'btn-outline-primary'"
				@click="setMode('camera')"
			>
				📷 Camera Scan
			</button>
			<button
				type="button"
				class="btn"
				:class="scanMode === 'file' ? 'btn-primary' : 'btn-outline-primary'"
				@click="setMode('file')"
			>
				📁 Upload Receipt Image
			</button>
			<button
				type="button"
				class="btn"
				:class="scanMode === 'manual' ? 'btn-primary' : 'btn-outline-primary'"
				@click="setMode('manual')"
			>
				⌨️ Manual CU No.
			</button>
		</div>

		<!-- Live Camera Scanner Container -->
		<div v-show="scanMode === 'camera'" class="text-center mb-2">
			<div class="qr-scanner-video-wrap" style="width: 100%; max-width: 350px; margin: auto;">
				<video ref="videoEl" autoplay playsinline muted></video>
				<div class="qr-scanner-frame"></div>
			</div>
			<p v-if="cameraError" class="text-danger small mt-1">{{ cameraError }}</p>
			<p v-else class="text-muted small mt-1">Point camera at the fiscal receipt QR code.</p>
		</div>

		<!-- File Image Scanner Input -->
		<div v-if="scanMode === 'file'" class="mb-2">
			<label class="form-label small fw-semibold">Select Fiscal Receipt Image</label>
			<input
				type="file"
				accept="image/*"
				@change="onFileScan"
				class="form-control form-control-sm"
			/>
			<p v-if="fileScanStatus" class="small mt-1 text-muted">{{ fileScanStatus }}</p>
		</div>

		<!-- Extracted or Manual Form Fields -->
		<div class="row g-2 mt-1">
			<div class="col-md-6">
				<label class="form-label small fw-semibold">CU INVOICE NUMBER</label>
				<input
					type="text"
					v-model="cuInvoiceNumber"
					placeholder="e.g. 0040128640000152718"
					class="form-control form-control-sm font-monospace"
				/>
			</div>
			<div class="col-md-6">
				<label class="form-label small fw-semibold">CU SERIAL NO</label>
				<input
					type="text"
					v-model="cuSerialNo"
					placeholder="e.g. KRAMW004202112012864"
					class="form-control form-control-sm font-monospace"
				/>
			</div>
		</div>

		<button
			type="button"
			@click="validateDocument"
			class="btn btn-sm btn-success mt-3 w-100 fw-bold"
			:disabled="!cuInvoiceNumber || isValidating"
		>
			{{ isValidating ? 'Authenticating with KRA...' : 'Verify KRA Authenticity' }}
		</button>

		<!-- Verification Badge -->
		<div
			v-if="validationResult"
			class="mt-2 p-2 rounded small text-center"
			:class="validationResult.valid ? 'bg-success-subtle text-success border border-success' : 'bg-danger-subtle text-danger border border-danger'"
		>
			<strong>{{ validationResult.valid ? '✓ VERIFIED FISCAL RECEIPT' : '❌ AUTHENTICATION FAILED' }}</strong>
			<div>{{ validationResult.message }}</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick } from "vue";
import jsQR from "jsqr";
import { call } from "../api";

const emit = defineEmits(["validated"]);

const scanMode = ref("manual");
const cuInvoiceNumber = ref("");
const cuSerialNo = ref("");
const qrUrl = ref("");
const isValidating = ref(false);
const validationResult = ref(null);
const fileScanStatus = ref("");

const videoEl = ref(null);
const cameraError = ref("");

let stream = null;
let canvas = null;
let ctx = null;
let rafId = null;
let stopped = false;

function setMode(mode) {
	scanMode.value = mode;
	if (mode === "camera") {
		startCamera();
	} else {
		stopCamera();
	}
}

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
			parseQrPayload(code.data);
			return;
		}
	}
	rafId = requestAnimationFrame(tick);
}

async function startCamera() {
	stopped = false;
	cameraError.value = "";
	await nextTick();

	if (!canvas) {
		canvas = document.createElement("canvas");
		ctx = canvas.getContext("2d", { willReadFrequently: true });
	}

	if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
		cameraError.value = "Camera access requires HTTPS or localhost.";
		return;
	}

	try {
		stream = await navigator.mediaDevices.getUserMedia({
			video: { facingMode: { ideal: "environment" } },
		});
		if (videoEl.value) {
			videoEl.value.srcObject = stream;
			rafId = requestAnimationFrame(tick);
		}
	} catch (e) {
		cameraError.value = "Camera access failed: " + (e.message || "Permission denied");
	}
}

function parseQrPayload(qrText) {
	qrUrl.value = qrText;
	stopCamera();

	try {
		const searchString = qrText.includes("?") ? qrText.split("?")[1] : qrText;
		const urlParams = new URLSearchParams(searchString);

		if (urlParams.has("invoiceNo")) {
			cuInvoiceNumber.value = urlParams.get("invoiceNo");
		} else if (urlParams.has("invoice_no")) {
			cuInvoiceNumber.value = urlParams.get("invoice_no");
		} else if (qrText.match(/\b\d{19}\b/)) {
			cuInvoiceNumber.value = qrText.match(/\b\d{19}\b/)[0];
		} else if (qrText.match(/KRACU\w+/i)) {
			cuInvoiceNumber.value = qrText.match(/KRACU\w+/i)[0];
		}

		if (urlParams.has("serialNo")) {
			cuSerialNo.value = urlParams.get("serialNo");
		} else if (urlParams.has("serial_no")) {
			cuSerialNo.value = urlParams.get("serial_no");
		} else if (qrText.match(/KRA\w{10,20}/i)) {
			cuSerialNo.value = qrText.match(/KRA\w{10,20}/i)[0];
		}
	} catch (err) {
		console.error("QR Payload parsing error:", err);
	}

	validateDocument();
}

function onFileScan(event) {
	const file = event.target.files[0];
	if (!file) return;

	fileScanStatus.value = "Scanning image for KRA QR code...";
	const reader = new FileReader();

	reader.onload = (e) => {
		const img = new Image();
		img.onload = () => {
			const fileCanvas = document.createElement("canvas");
			fileCanvas.width = img.width;
			fileCanvas.height = img.height;
			const fileCtx = fileCanvas.getContext("2d");
			fileCtx.drawImage(img, 0, 0);

			const imageData = fileCtx.getImageData(0, 0, img.width, img.height);
			const code = jsQR(imageData.data, imageData.width, imageData.height);

			if (code && code.data) {
				fileScanStatus.value = "✓ QR code extracted successfully!";
				parseQrPayload(code.data);
			} else {
				fileScanStatus.value = "⚠️ Could not auto-detect a QR code in image. Please enter CU numbers manually below.";
			}
		};
		img.src = e.target.result;
	};

	reader.readAsDataURL(file);
}

async function validateDocument() {
	if (!cuInvoiceNumber.value) return;

	isValidating.value = true;
	validationResult.value = null;

	try {
		const res = await call("smart_receiving.smart_receiving.api.receiving.validate_kra_cu_invoice", {
			cu_invoice_number: cuInvoiceNumber.value,
			cu_serial_no: cuSerialNo.value,
			qr_url: qrUrl.value,
		});

		validationResult.value = res;
		emit("validated", {
			cuInvoiceNumber: cuInvoiceNumber.value,
			cuSerialNo: cuSerialNo.value,
			isValid: res.valid,
			message: res.message,
		});
	} catch (err) {
		validationResult.value = {
			valid: false,
			message: err.message || "KRA verification failed.",
		};
	} finally {
		isValidating.value = false;
	}
}

onBeforeUnmount(() => {
	stopCamera();
});
</script>

<style scoped>
.kra-scanner-card {
	background: #f8fafc;
	border-radius: 8px;
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
	border: 3px solid #5e64ff;
	border-radius: 8px;
	box-shadow: 0 0 0 999px rgba(0, 0, 0, 0.3);
	pointer-events: none;
}
.font-monospace {
	font-family: SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
}
</style>
