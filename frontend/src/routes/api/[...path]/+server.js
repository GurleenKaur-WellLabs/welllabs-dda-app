/** Dev proxy: forward /api/* to the FastAPI backend (Vite server.proxy is unreliable with SvelteKit). */

const API_BASE = process.env.API_URL || 'http://localhost:8080';

/** @param {import('@sveltejs/kit').RequestEvent} event */
async function proxy(event) {
	const { params, request, url } = event;
	const target = `${API_BASE}/api/${params.path}${url.search}`;

	const headers = new Headers(request.headers);
	headers.delete('host');
	headers.delete('connection');

	const init = {
		method: request.method,
		headers
	};

	if (request.method !== 'GET' && request.method !== 'HEAD') {
		init.body = await request.arrayBuffer();
	}

	const res = await fetch(target, init);
	const outHeaders = new Headers(res.headers);
	outHeaders.delete('content-encoding');

	return new Response(res.body, {
		status: res.status,
		statusText: res.statusText,
		headers: outHeaders
	});
}

export const GET = proxy;
export const POST = proxy;
export const PATCH = proxy;
export const PUT = proxy;
export const DELETE = proxy;
