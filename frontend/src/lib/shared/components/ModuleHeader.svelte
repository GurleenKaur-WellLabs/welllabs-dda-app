<script>
	import { goto } from '$app/navigation';
	import UserMenu from '$lib/shared/components/UserMenu.svelte';

	/** @type {{ title: string, subtitle?: string, homeHref?: string }} */
	let { title, subtitle = '', homeHref = '/home' } = $props();
</script>

<header class="border-b border-brand-navy/20 bg-brand-navy px-6 py-4 text-white">
	<div class="flex items-center justify-between gap-3">
		<div class="flex items-center gap-3">
			<button
				class="cursor-pointer rounded border border-brand-sky/40 bg-transparent px-2 py-1 font-body text-sm text-white hover:bg-white/10"
				onclick={() => goto(homeHref)}
			>
				← Home
			</button>
			<h1 class="m-0 font-headline text-xl font-semibold">{title}</h1>
		</div>

		<UserMenu />
	</div>
	{#if subtitle}
		<p class="m-0 mt-2 font-body text-sm text-brand-sky/90">{subtitle}</p>
	{/if}
</header>
