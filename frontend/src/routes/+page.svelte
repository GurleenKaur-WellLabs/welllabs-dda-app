<script>
	import { goto } from '$app/navigation';
	import { session } from '$lib/shared/session.svelte.js';

	$effect(() => {
		if (session.loaded && session.user) {
			goto('/home');
		}
	});
</script>

<svelte:head>
	<title>DDA Product — Watershed Toolkit</title>
</svelte:head>

<div class="flex min-h-screen flex-col bg-white font-body">
	<header class="flex items-center justify-between px-6 py-4">
		<span class="font-headline text-xl font-semibold text-brand-navy">DDA Product</span>
		{#if session.loaded && !session.user}
			<nav class="flex items-center gap-2">
				<a
					href="/login"
					class="rounded-lg border border-brand-navy/15 px-4 py-2 font-body text-sm font-medium text-brand-navy hover:bg-gray-50"
				>
					Sign in
				</a>
				<a
					href="/register"
					class="rounded-lg bg-brand-blue px-4 py-2 font-body text-sm font-medium text-white hover:bg-brand-deep"
				>
					Get started
				</a>
			</nav>
		{/if}
	</header>

	<main class="flex flex-1 flex-col items-center justify-center px-6 py-16">
		<div class="mx-auto max-w-2xl text-center">
			<h1 class="m-0 font-headline text-4xl leading-tight font-bold text-brand-navy sm:text-5xl">
				Diagnose. Design. Assess.
			</h1>
			<p class="m-0 mx-auto mt-5 max-w-lg text-lg leading-relaxed text-brand-steel">
				A watershed-first toolkit for diagnosing conditions in the field, designing
				interventions, and assessing outcomes — all in one place.
			</p>

			{#if session.loaded && !session.user}
				<div class="mt-8 flex items-center justify-center gap-3">
					<a
						href="/register"
						class="rounded-lg bg-brand-blue px-6 py-3 font-body text-base font-medium text-white shadow-sm hover:bg-brand-deep"
					>
						Create an account
					</a>
					<a
						href="/login"
						class="rounded-lg border border-brand-navy/15 px-6 py-3 font-body text-base font-medium text-brand-navy hover:bg-gray-50"
					>
						Sign in
					</a>
				</div>
			{/if}
		</div>

		<div class="mx-auto mt-16 grid max-w-4xl gap-6 sm:grid-cols-3">
			<div class="rounded-2xl border border-brand-navy/8 bg-white p-6 shadow-sm">
				<div
					class="mb-3 flex h-10 w-10 items-center justify-center rounded-lg"
					style="background: color-mix(in srgb, #1b75e0 14%, transparent);"
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#1b75e0" stroke-width="1.75" class="h-5 w-5">
						<circle cx="12" cy="12" r="7.5" />
						<path d="M12 4.5v15M4.5 12h15" />
						<circle cx="12" cy="12" r="1.75" fill="#1b75e0" stroke="none" />
					</svg>
				</div>
				<h3 class="m-0 font-headline text-base font-semibold text-brand-navy">Diagnose</h3>
				<p class="m-0 mt-2 text-sm leading-relaxed text-brand-steel">
					Map watersheds, draw observation zones, and capture geotagged field notes — synced
					offline with QField.
				</p>
			</div>

			<div class="rounded-2xl border border-brand-navy/8 bg-white p-6 shadow-sm">
				<div
					class="mb-3 flex h-10 w-10 items-center justify-center rounded-lg"
					style="background: color-mix(in srgb, #0d983b 14%, transparent);"
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#0d983b" stroke-width="1.75" class="h-5 w-5">
						<path d="M4 19.5V16l9-9 3.5 3.5-9 9H4z" stroke-linejoin="round" />
						<path d="M13 7l3.5 3.5" />
						<path d="M17.5 4.5 19.5 6.5" stroke-linecap="round" />
					</svg>
				</div>
				<h3 class="m-0 font-headline text-base font-semibold text-brand-navy">Design</h3>
				<p class="m-0 mt-2 text-sm leading-relaxed text-brand-steel">
					Plan and design interventions on top of diagnosed watersheds.
				</p>
			</div>

			<div class="rounded-2xl border border-brand-navy/8 bg-white p-6 shadow-sm">
				<div
					class="mb-3 flex h-10 w-10 items-center justify-center rounded-lg"
					style="background: color-mix(in srgb, #d5b443 14%, transparent);"
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="#d5b443" stroke-width="1.75" class="h-5 w-5">
						<path d="M4 19h16" stroke-linecap="round" />
						<path d="M7 19v-5M12 19V8M17 19v-9" stroke-linecap="round" />
					</svg>
				</div>
				<h3 class="m-0 font-headline text-base font-semibold text-brand-navy">Assess</h3>
				<p class="m-0 mt-2 text-sm leading-relaxed text-brand-steel">
					Track outcomes and assess impact of implemented designs over time.
				</p>
			</div>
		</div>
	</main>

	<footer class="border-t border-brand-navy/8 px-6 py-4 text-center text-xs text-brand-steel">
		DDA Product
	</footer>
</div>
