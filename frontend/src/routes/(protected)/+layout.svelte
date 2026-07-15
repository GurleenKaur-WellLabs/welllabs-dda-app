<script>
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { session } from '$lib/shared/session.svelte.js';

	let { children } = $props();

	$effect(() => {
		if (session.loaded && !session.user) {
			const next = encodeURIComponent(page.url.pathname + page.url.search);
			goto(`/login?next=${next}`);
		}
	});
</script>

{#if !session.loaded}
	<div class="flex h-screen items-center justify-center bg-white font-body text-brand-steel">
		Loading…
	</div>
{:else if session.user}
	{@render children?.()}
{:else}
	<div class="flex h-screen items-center justify-center bg-white font-body text-brand-steel">
		Redirecting to login…
	</div>
{/if}
