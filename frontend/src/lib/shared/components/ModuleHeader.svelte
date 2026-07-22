<script>
	import { goto } from '$app/navigation';
	import UserMenu from '$lib/shared/components/UserMenu.svelte';

	/** @type {{ title: string, subtitle?: string, homeHref?: string }} */
	let { title, subtitle = '', homeHref = '/home' } = $props();
</script>

<header
	class="sticky top-0 z-40 border-b border-hairline px-6 py-4 backdrop-blur-xl md:px-10"
	style="background-image: linear-gradient(90deg, rgba(75,85,99,0.7) 0%, rgba(148,163,184,0.45) 25%, rgba(255,255,255,0.92) 50%, rgba(148,163,184,0.45) 75%, rgba(75,85,99,0.7) 100%);"
>
	<div class="flex w-full items-center justify-between gap-4">
		<div class="flex items-center gap-3">
			<button
				class="inline-flex h-10 items-center justify-center rounded-lg border border-hairline bg-white/60 px-4 text-sm font-medium text-brand-navy transition hover:bg-white"
				onclick={() => goto(homeHref)}
			>
				← Home
			</button>
			<h1 class="m-0 font-headline text-xl font-semibold text-brand-navy">{title}</h1>
			{#if subtitle}
				<span class="hidden font-body text-sm text-ink-dim sm:inline">·</span>
				<p class="m-0 hidden font-body text-sm text-ink-dim sm:block">{subtitle}</p>
			{/if}
		</div>

		<UserMenu variant="light" />
	</div>
	{#if subtitle}
		<p class="m-0 mt-2 font-body text-sm text-ink-dim sm:hidden">{subtitle}</p>
	{/if}
</header>
