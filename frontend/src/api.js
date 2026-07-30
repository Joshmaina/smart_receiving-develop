// Thin promise wrapper around frappe.call, mirroring posawesome's api service.
export function call(method, args = {}) {
	return new Promise((resolve, reject) => {
		frappe.call({
			method,
			args,
			callback: (response) => resolve(response.message),
			error: (error) => reject(error),
		});
	});
}
