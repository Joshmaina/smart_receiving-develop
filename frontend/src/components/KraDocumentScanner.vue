<template>
	<div class="kra-document-card card p-3 mb-3 border-secondary">
		<h6 class="fw-bold mb-2 text-primary">🛡️ KRA Document Authentication</h6>

		<!-- Input Mode Switcher -->
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
				📁 Upload Document
			</button>
			<button
				type="button"
				class="btn"
				:class="scanMode === 'manual' ? 'btn-primary' : 'btn-outline-primary'"
				@click="setMode('manual')"
			>
				⌨️ Manual Entry
			</button>
		</div>

		<!-- Live Camera Scanner View -->
		<div v-show="scanMode === 'camera'" class="text-center mb-2">
			<div class="qr-scanner-video-wrap" style="width: 100%; max-width: 350px; margin: auto;">
				<video ref="videoEl" autoplay playsinline muted></video>
				<div class="qr-scanner-frame"></div>
			</div>
			<p v-if="cameraError" class="text-danger small mt-1">{{ cameraError }}</p>
			<p v-else class="text-muted small mt-1">Point camera at the KRA eTIMS/TIMS document QR code.</p>
		</div>

		<!-- File Upload Input -->
		<div v-if="scanMode === 'file'" class="mb-2">
			<label class="form-label small fw-semibold">Select Fiscal Document Image</label>
			<input
				type="file"
				accept="image/*,.pdf"
				@change="onFileScan"
				class="form-control form-control-sm"
			/>
			<p v-if="fileScanStatus" class="small mt-1 text-muted">{{ fileScanStatus }}</p>
		</div>

		<!-- CU Invoice Number Field -->
		<div class="mt-2">
			<label class="form-label small fw-semibold">CU INVOICE NUMBER</label>
			<input
				type="text"
				v-model="cuInvoiceNumber"
				placeholder="e.g. KRACU0300003347/34984 (eTIMS) or 0040128640000152718 (TIMS)"
				class="form-control form-control-sm font-monospace"
			/>
			<small class="text-muted d-block mt-1" style="font-size: 0.72rem;">
				* eTIMS numbers include a slash (/); TIMS numbers are a continuous sequence.
			</small>
		</div>

		<!-- Authenticate Action -->
		<button
			type="button"
			@click="validateDocument"
			class="btn btn-sm btn-success mt-3 w-100 fw-bold"
			:disabled="!cuInvoiceNumber || isValidating"
		>
			{{ isValidating ? 'Authenticating Document...' : 'Verify KRA Authenticity' }}
		</button>

		<!-- Validation Status Display -->
		<div
			v-if="validationResult"
			class="mt-2 p-2 rounded small text-center"
			:class="validationResult.valid ? 'bg-success-subtle text-success border border-success' : 'bg-danger-subtle text-danger border border-danger'"
		>
			<strong>{{ validationResult.valid ? '✓ VERIFIED KRA DOCUMENT' : '❌ AUTHENTICATION FAILED' }}</strong>
			<div>{{ validationResult.message }}</div>
		</div>
	</div>
</template>

<script setup>
import { ref, onBeforeUnmount, nextTick } from "vue";
import jsQR from "jsqr";
import { call } from "../api";

const emit = defineEmits(["validated"]);

const scanMode = ref("manual");
const cuInvoiceNumber = ref("");
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
		if (!canvas) {
			canvas = document.createElement("canvas");
			ctx = canvas.getContext("2d", { willReadFrequently: true });
		}
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

	let extractedNumber = "";

	// 1. Check for standard URL Query Parameters
	if (qrText.includes("?")) {
		try {
			const searchString = qrText.split("?")[1];
			const urlParams = new URLSearchParams(searchString);
			if (urlParams.has("invoiceNo")) {
				extractedNumber = urlParams.get("invoiceNo");
			} else if (urlParams.has("invoice_no")) {
				extractedNumber = urlParams.get("invoice_no");
			}
		} catch (e) {
			console.error("Query param parsing error:", e);
		}
	}

	// 2. Fallback: Regex Match for eTIMS Format (contains slash: e.g. KRACU.../...)
	if (!extractedNumber) {
		const etimsMatch = qrText.match(/[A-Za-z0-9]+\/[0-9]+/);
		if (etimsMatch) {
			extractedNumber = etimsMatch[0];
		}
	}

	// 3. Fallback: Regex Match for TIMS Format (continuous digits)
	if (!extractedNumber) {
		const timsMatch = qrText.match(/\b[0-9]{15,20}\b/);
		if (timsMatch) {
			extractedNumber = timsMatch[0];
		}
	}

	cuInvoiceNumber.value = extractedNumber || qrText.trim();
	validateDocument();
}

function onFileScan(event) {
	const file = event.target.files[0];
	if (!file) return;

	fileScanStatus.value = "Scanning document for KRA QR code...";
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
				fileScanStatus.value = "⚠️ Could not auto-detect a QR code in document. Please enter CU Invoice Number manually below.";
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
			qr_url: qrUrl.value,
		});

		validationResult.value = res;
		emit("validated", {
			cuInvoiceNumber: cuInvoiceNumber.value,
			docType: res.doc_type,
			isValid: res.valid,
			message: res.message,
		});
	} catch (err) {
		validationResult.value = {
			valid: false,
			message: err.message || "KRA document verification failed.",
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
.kra-document-card {
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
