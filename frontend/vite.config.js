import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	server: {
		proxy: {
			'/api': 'http://localhost:8080',
			'/titiler': {
				target: 'http://localhost:8000',
				rewrite: (path) => path.replace(/^\/titiler/, '')
			}
		}
	}
});
