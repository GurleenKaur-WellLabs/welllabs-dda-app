<script lang="ts">
	import UserMenu from '$lib/shared/components/UserMenu.svelte';
	export let name = '';
</script>

<header class="sticky top-0 z-40 border-b border-hairline bg-void/10 px-6 py-4 backdrop-blur-md md:px-10">
	<div class="mx-auto flex max-w-6xl items-center justify-between gap-4">
		<a href="/home" class="flex items-center gap-3">
			<svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
				<circle cx="12" cy="12" r="10.5" stroke="#4FD1C5" stroke-width="1" opacity="0.5" />
				<circle cx="12" cy="12" r="6.5" stroke="#4FD1C5" stroke-width="1" opacity="0.8" />
				<circle cx="12" cy="12" r="2.5" fill="#4FD1C5" />
			</svg>
			<span class="font-display text-[15px] font-semibold tracking-wide text-ink">DDA</span>
			<span class="hidden font-mono text-[11px] text-ink md:inline">/ watershed control</span>
		</a>

		<div class="flex items-center gap-4">			
			<UserMenu />
		</div>
	</div>
</header>
