<script>
	import ModuleHeader from '$lib/shared/components/ModuleHeader.svelte';
</script>

<svelte:head>
	<title>Assess · DDA Product</title>
</svelte:head>

<div class="flex h-full min-h-screen flex-col bg-white font-body">
	<ModuleHeader title="Assess" />

	<main class="flex flex-1 flex-col items-center justify-center gap-3 p-6 text-center">
		<div
			class="flex h-16 w-16 items-center justify-center rounded-2xl"
			style:background-color="color-mix(in srgb, #d5b443 16%, transparent)"
		>
			<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#d5b443" stroke-width="1.5" class="h-8 w-8">
				<path d="M4 19h16" stroke-linecap="round" />
				<path d="M7 19v-5M12 19V8M17 19v-9" stroke-linecap="round" />
			</svg>
		</div>
		<h2 class="m-0 font-headline text-xl font-semibold text-brand-navy">Assess module — coming soon</h2>
		<p class="m-0 max-w-md text-sm text-brand-steel">
			This module will track outcomes and assess the impact of implemented designs over time.
			The API for this module is scaffolded at <code class="rounded bg-brand-pale px-1 py-0.5">/api/assess</code>.
		</p>
	</main>
</div>
